from typing import List, Dict, Any
import yaml
import json
import copy
from langchain_core.documents import Document
from app.logging_config import logger
from app.services.openapi.parser import parse_openapi_schema, _resolve_references

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
        self.schema, self.resolved_schema = parse_openapi_schema(file_path=path)

    def get_documents(self) -> List[Document]:
        """
        スキーマをチャンク化し、Documentオブジェクトのリストを返す
        """
        documents: List[Document] = []
        # Use resolved_schema for chunking
        if "paths" not in self.resolved_schema:
            logger.warning("No 'paths' found in resolved schema.")
            return documents

        for path, methods in self.resolved_schema.get("paths", {}).items():
            if not isinstance(methods, dict):
                continue

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue

                chunk_content: Dict[str, Any] = {
                    "method": method.upper(),
                    "path": path,
                }

                # Extract relevant parts from the resolved schema
                if "parameters" in details:
                    chunk_content["parameters"] = copy.deepcopy(details["parameters"])
                if "requestBody" in details:
                    chunk_content["requestBody"] = copy.deepcopy(details["requestBody"])
                if "responses" in details:
                    relevant_responses = {
                        status: copy.deepcopy(resp) for status, resp in details["responses"].items()
                        if status in ["200", "201", "204"] or status.startswith("2")
                    }
                    chunk_content["responses"] = relevant_responses

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
