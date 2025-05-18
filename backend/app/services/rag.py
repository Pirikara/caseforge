from typing import List, Dict, Any
import os
import yaml
import json
import copy
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from app.config import settings
from app.logging_config import logger
from app.exceptions import TimeoutException
from app.utils.timeout import timeout, async_timeout, run_with_timeout
from app.utils.retry import run_with_retry, RetryStrategy
from app.utils.path_manager import path_manager

# 既存のEmbeddingFunctionForCaseforgeクラスは削除し、代わりに新しい埋め込みモデルを使用します。
# 互換性のために、EmbeddingFunctionForCaseforgeクラスを残しますが、内部では新しい実装を使用します。
class EmbeddingFunctionForCaseforge(Embeddings):
    """
    DBで使用するための埋め込み関数（互換性のために残す）
    内部では新しい埋め込みモデルを使用します。
    """
    def __init__(self):
        """
        簡易的な埋め込み関数を初期化
        """
        try:
            logger.info("Using simplified embedding function from new implementation")
            from app.services.vector_db.embeddings import EmbeddingModelFactory
            self.model = EmbeddingModelFactory.create(model_type="simplified")
            logger.info("Successfully initialized simplified embedding function")
        except Exception as e:
            logger.error(f"Error initializing simplified embedding function: {e}", exc_info=True)
            raise

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        DBのEmbeddingFunction用の呼び出しメソッド

        Args:
            input: 埋め込むテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        return self.embed_documents(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        """
        複数のドキュメントを埋め込む

        Args:
            input: 埋め込むテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        try:
            return self.model.embed_documents(input)
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}", exc_info=True)
            return [[0.0] * 384 for _ in range(len(input))]

    def embed_query(self, input: str) -> List[float]:
        """
        クエリを埋め込む

        Args:
            input: 埋め込むクエリテキスト

        Returns:
            埋め込みベクトル
        """
        try:
            return self.model.embed_query(input)
        except Exception as e:
            logger.error(f"Error creating query embedding: {e}", exc_info=True)
            return [0.0] * 384

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
                continue

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue

                chunk_content: Dict[str, Any] = {
                    "method": method.upper(),
                    "path": path,
                }

                if "parameters" in details:
                    chunk_content["parameters"] = self._resolve_references(details["parameters"])
                if "requestBody" in details:
                    chunk_content["requestBody"] = self._resolve_references(details["requestBody"])
                if "responses" in details:
                    relevant_responses = {
                        status: resp for status, resp in details["responses"].items()
                        if status in ["200", "201", "204"] or status.startswith("2")
                    }
                    chunk_content["responses"] = self._resolve_references(relevant_responses)

                page_content = yaml.dump(chunk_content, indent=2, sort_keys=False)

                metadata = {
                    "source": f"{self.path}::paths::{path}::{method}",
                    "type": "path-method",
                    "path": path,
                    "method": method.upper(),
                }
                documents.append(Document(page_content=page_content, metadata=metadata))
                logger.debug(f"Created document for {method.upper()} {path}")

        logger.info(f"Finished chunking schema. Created {len(documents)} documents.")
        return documents


def index_schema(project_id: str, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    """
    try:
        logger.info(f"Indexing schema for project {project_id}: {path}")

        # 1. スキーマファイルのロードとチャンク化
        logger.info("Step 1: Loading, parsing, and chunking OpenAPI schema file")
        chunker = OpenAPISchemaChunker(path)
        docs = chunker.get_documents()
        logger.info(f"Successfully chunked schema file into {len(docs)} documents")

        if not docs:
            logger.warning(f"No documents generated for schema {path}. Skipping indexing.")
            return

        # 2. ベクトルDBマネージャーの初期化
        logger.info("Step 2: Initializing vector database manager")
        from app.services.vector_db.manager import VectorDBManagerFactory
        
        # プロジェクト固有のベクトルDBマネージャーを作成
        vector_db_manager = VectorDBManagerFactory.create_default(project_id)
        
        # 3. ドキュメントをベクトルDBに追加
        logger.info("Step 3: Adding documents to vector database")
        try:
            # ドキュメントを追加（タイムアウトとリトライ機構は内部で処理）
            vector_db_manager.add_documents(docs)
            logger.info(f"Successfully added {len(docs)} documents to vector database")
            
            # 4. 互換性のために/tmpにもシンボリックリンクを作成（FAISSの場合）
            if isinstance(vector_db_manager.vectordb, FAISS) and vector_db_manager.persist_directory:
                save_dir = vector_db_manager.persist_directory
                tmp_dir = path_manager.get_faiss_dir(project_id, temp=True)
                
                path_manager.ensure_dir(os.path.dirname(str(tmp_dir)))
                
                if path_manager.exists(tmp_dir):
                    if os.path.islink(str(tmp_dir)):
                        os.unlink(str(tmp_dir))
                    else:
                        import shutil
                        shutil.rmtree(str(tmp_dir))
                
                os.symlink(save_dir, str(tmp_dir))
                logger.info(f"Created symbolic link from {tmp_dir} to {save_dir}")
            
            logger.info(f"Successfully indexed schema for project {project_id}")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}", exc_info=True)
            logger.warning("Continuing without vector database indexing")

    except Exception as e:
        logger.error(f"Error in vector database processing: {e}", exc_info=True)
        logger.warning("Attempting to continue without vector database indexing")
