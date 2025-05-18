from typing import List, Dict, Any
import yaml
import json
import copy
from langchain_core.documents import Document
from app.logging_config import logger

class OpenAPISchemaChunker:
    """
    OpenAPIスキーマを構造単位でチャンク化し、$refを解決するクラス
    """
    def __init__(self, path: str):
        """
        Args:
            path: OpenAPIスキーマファイルのパス
        """
        self.path = path
        self.schema: Dict[str, Any] = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """
        スキーマファイルを読み込み、YAMLまたはJSONとしてパースする
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                if str(self.path).endswith((".yaml", ".yml")):
                    return yaml.safe_load(f)
                elif self.path.endswith(".json"):
                    return json.load(f)
                else:
                    raise ValueError("Unsupported file format. Must be .yaml, .yml, or .json")
        except Exception as e:
            logger.error(f"Error loading or parsing schema file {self.path}: {e}")
            raise

    def _resolve_references(self, obj: Any) -> Any:
        """
        オブジェクト内の$refを再帰的に解決する
        """
        if isinstance(obj, dict):
            resolved_obj = {}
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str) and value.startswith("#/"):
                    ref_path = value.lstrip("#/").split("/")
                    ref_value = self.schema
                    try:
                        for part in ref_path:
                            ref_value = ref_value[part]
                        # $refを解決した値で置き換え、さらにその値内の$refも解決
                        resolved_obj.update(self._resolve_references(copy.deepcopy(ref_value)))
                    except (KeyError, TypeError) as e:
                        logger.warning(f"Could not resolve reference {value}: {e}")
                        # 解決できなかった場合は元の$refを残すか、エラーを示す
                        resolved_obj[key] = value # または resolved_obj[key] = {"$error": f"Unresolved reference: {value}"}
                else:
                    resolved_obj[key] = self._resolve_references(value)
            return resolved_obj
        elif isinstance(obj, list):
            return [self._resolve_references(item) for item in obj]
        else:
            return obj

    def get_documents(self) -> List[Document]:
        """
        スキーマをチャンク化し、Documentオブジェクトのリストを返す
        """
        documents: List[Document] = []
        if "paths" not in self.schema:
            logger.warning("No 'paths' found in schema.")
            return documents

        for path, methods in self.schema["paths"].items():
            if not isinstance(methods, dict):
                continue # Skip if not a dictionary (e.g., $ref at path level)

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue # Skip if not a dictionary (e.g., $ref at method level)

                # $refを解決したチャンク内容を構築
                chunk_content: Dict[str, Any] = {
                    "method": method.upper(),
                    "path": path,
                }

                # parameters, requestBody, responses を含める（$ref解決済み）
                if "parameters" in details:
                    chunk_content["parameters"] = self._resolve_references(details["parameters"])
                if "requestBody" in details:
                    chunk_content["requestBody"] = self._resolve_references(details["requestBody"])
                if "responses" in details:
                    # 主要なレスポンスのみを含める（例: 200, 201）
                    relevant_responses = {
                        status: resp for status, resp in details["responses"].items()
                        if status in ["200", "201", "204"] or status.startswith("2") # 2xx系を主要とみなす
                    }
                    chunk_content["responses"] = self._resolve_references(relevant_responses)

                # YAML形式の文字列としてpage_contentを作成
                page_content = yaml.dump(chunk_content, indent=2, sort_keys=False)

                # Documentオブジェクトを作成
                metadata = {
                    "source": f"{self.path}::paths::{path}::{method}",
                    "type": "path-method",
                    "path": path, # メタデータにもpathとmethodを追加しておくと便利かもしれない
                    "method": method.upper(),
                }
                documents.append(Document(page_content=page_content, metadata=metadata))
                logger.debug(f"Created document for {method.upper()} {path}")

        logger.info(f"Finished chunking schema. Created {len(documents)} documents.")
        return documents
