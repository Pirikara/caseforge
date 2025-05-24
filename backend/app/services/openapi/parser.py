from typing import List, Dict, Any, Optional, Tuple
import yaml
import json
import re
import copy
from app.logging_config import logger
from app.exceptions import OpenAPIParseException

def _resolve_references(schema: Any, full_schema: Dict, resolved_refs: set = None) -> Any:
    """
    $refを再帰的に解決する（循環参照対応版）
    辞書やリスト構造を汎用的に探索し、$refを解決する。

    Args:
        schema: 解決対象のスキーマの一部（辞書、リスト、またはその他の型）
        full_schema: OpenAPIスキーマ全体
        resolved_refs: 現在の解決パス内で既に解決を試みた$refパスのセット (循環参照検出用)

    Returns:
        $refが解決されたスキーマの一部
    """
    # resolved_refsが提供されていない場合は新しいセットを作成
    if resolved_refs is None:
        resolved_refs = set()

    # スキーマが辞書の場合
    if isinstance(schema, dict):
        # $ref キーが存在する場合、その参照を解決して返す
        if "$ref" in schema:
            ref_path = schema["$ref"]

            # 現在の解決パス内で既に解決を試みている場合は循環参照
            if ref_path in resolved_refs:
                logger.error(f"Circular reference detected: {ref_path}")
                raise OpenAPIParseException(
                    f"循環参照が検出されました: {ref_path}。OpenAPIスキーマに循環参照は許可されていません。",
                    details={
                        "circular_reference_path": ref_path,
                        "resolution_path": list(resolved_refs)
                    }
                )

            if ref_path.startswith("#/"):
                parts = ref_path.lstrip("#/").split("/")
                ref_value = full_schema

                try:
                    for part in parts:
                        # パスがリストのインデックスの場合
                        if isinstance(ref_value, list) and re.match(r'^\d+$', part):
                            index = int(part)
                            if 0 <= index < len(ref_value):
                                ref_value = ref_value[index]
                            else:
                                logger.warning(f"Reference path index out of bounds: {ref_path}")
                                return schema # パスが見つからない場合は元の$refを返す
                        # パスが辞書のキーの場合
                        elif isinstance(ref_value, dict) and part in ref_value:
                            ref_value = ref_value[part]
                        else:
                            logger.warning(f"Reference path not found: {ref_path}")
                            return schema # パスが見つからない場合は元の$refを返す
                except (ValueError, IndexError, TypeError) as e:
                    logger.warning(f"Error resolving reference path {ref_path}: {e}")
                    return schema # エラー発生時は元の$refを返す

                # 現在の解決パス内で既に解決を試みている場合のみ循環参照として扱う
                # 事前チェックは削除し、実際の解決パス内での循環参照のみを検出する

                # 現在の解決パスに追加
                resolved_refs.add(ref_path)

                # 解決した値自体に$refが含まれていないか再帰的にチェック
                # 現在の解決パスを引き継いで循環参照を検出
                resolved_value = _resolve_references(ref_value, full_schema, resolved_refs)
                
                # 解決パスから削除（バックトラック）
                resolved_refs.discard(ref_path)
                
                return resolved_value
            else:
                 # 外部参照はここでは解決しない
                 logger.warning(f"External reference not supported: {ref_path}")
                 return schema

        # $ref キーが存在しない場合、辞書の値について再帰的に解決
        resolved = copy.deepcopy(schema)
        for key, value in resolved.items():
            resolved[key] = _resolve_references(value, full_schema, resolved_refs)
        return resolved

    # スキーマがリストの場合
    elif isinstance(schema, list):
        resolved_list = []
        for item in schema:
            resolved_list.append(_resolve_references(item, full_schema, resolved_refs))
        return resolved_list

    # その他の型の場合はそのまま返す
    else:
        return schema

def parse_openapi_schema(schema_content: Optional[str] = None, file_path: Optional[str] = None) -> Tuple[Dict, Dict]:
    """
    OpenAPIスキーマの内容またはファイルパスを受け取り、パース済みのスキーマと$ref解決済みのスキーマを返す

    Args:
        schema_content: OpenAPIスキーマの内容（YAML or JSON）
        file_path: OpenAPIスキーマファイルのパス

    Returns:
        パース済みのスキーマ（dict）、$ref解決済みのスキーマ（dict）のタプル
    """
    if schema_content is None and file_path is None:
        raise ValueError("Either schema_content or file_path must be provided")

    schema = None
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                schema_content = f.read()
        except Exception as e:
            logger.error(f"Error loading schema file {file_path}: {e}")
            raise

    if schema_content:
        try:
            schema = yaml.safe_load(schema_content)
        except Exception as e:
            try:
                schema = json.loads(schema_content)
            except Exception as e:
                logger.error(f"Failed to parse schema content: {e}")
                raise ValueError(f"Invalid schema format: {e}")

    if not isinstance(schema, dict):
        raise ValueError("Parsed schema must be a dictionary")

    if "openapi" not in schema:
        logger.warning("Schema does not contain 'openapi' field")

    if "paths" not in schema:
        logger.warning("Schema does not contain 'paths' field")
        schema["paths"] = {}

    resolved_schema = _resolve_references(copy.deepcopy(schema), schema)

    return schema, resolved_schema

class EndpointParser:
    """OpenAPIスキーマからエンドポイント情報を抽出するクラス"""
    
    def __init__(self, schema_content: str):
        """
        Args:
            schema_content: OpenAPIスキーマの内容（YAML or JSON）
        """
        self.schema, self.resolved_schema = parse_openapi_schema(schema_content=schema_content)
    
    def parse_endpoints(self, service_id: int) -> List[Dict[str, Any]]:
        """
        スキーマからエンドポイント情報を抽出する
        
        Args:
            service_id: サービスID
            
        Returns:
            エンドポイント情報のリスト
        """
        endpoints = []
        
        
        paths = self.resolved_schema.get("paths", {})
        
        if not paths:
            logger.warning("No paths found in resolved schema")
            return []
        
        for path, methods in paths.items():
            
            if not isinstance(methods, dict):
                logger.warning(f"Path '{path}' does not contain methods dictionary: {type(methods)}")
                continue
            
            for method_name, operation in methods.items():
                if method_name.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}:
                    continue
                
                
                try:
                    request_body = operation.get("requestBody")
                    request_headers = self._extract_parameters(operation, "header")
                    request_query_params = self._extract_parameters(operation, "query")
                    responses = operation.get("responses")
                    
                    resolved_responses = responses
                    
                    endpoint_data = {
                        "service_id": service_id,
                        "path": path,
                        "method": method_name.upper(),
                        "summary": operation.get("summary"),
                        "description": operation.get("description"),
                        "request_body": self._resolve_request_body_schema(request_body),
                        "request_headers": request_headers,
                        "request_query_params": request_query_params,
                        "responses": self._resolve_response_schemas(resolved_responses)
                    }
                    
                    endpoints.append(endpoint_data)
                except Exception as e:
                    logger.error(f"Error processing endpoint {path} {method_name}: {e}", exc_info=True)
                    continue
        
        return endpoints
    
    def _resolve_request_body_schema(self, request_body: Optional[Dict]) -> Optional[Dict]:
        """リクエストボディのスキーマを解決する"""
        if not request_body:
            return None
        
        # リクエストボディ全体を_resolve_referencesに渡して解決
        resolved_request_body = _resolve_references(copy.deepcopy(request_body), self.resolved_schema)

        return resolved_request_body

    def _resolve_response_schemas(self, responses: Optional[Dict]) -> Optional[Dict]:
        """レスポンスのスキーマを解決する"""
        if not responses:
            return None
        
        resolved_responses = copy.deepcopy(responses)
        
        for status_code, response in resolved_responses.items():
            if "content" in response:
                for media_type, content in response["content"].items():
                    if "schema" in content:
                        resolved_responses[status_code]["content"][media_type]["schema"] = _resolve_references(content["schema"], self.resolved_schema)
        
        return resolved_responses

    def _extract_request_body(self, operation: Dict) -> Dict:
        """リクエストボディを抽出する (スキーマ解決は_resolve_request_body_schemaで行う)"""
        if "requestBody" not in operation:
            return None
        return operation["requestBody"]

    def _extract_parameters(self, operation: Dict, param_in: str) -> Dict:
        """指定したinタイプのパラメータを抽出する (スキーマ解決は不要、resolved_schemaから取得済み)"""
        result = {}
        
        if "parameters" not in operation:
            return result
        
        for param in operation["parameters"]:
            if param.get("in") == param_in:
                name = param.get("name")
                if name:
                    param_schema = param.get("schema", {})
                    result[name] = {
                        "required": param.get("required", False),
                        "schema": param_schema
                    }
        
        return result
