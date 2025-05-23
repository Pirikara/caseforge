from typing import List, Dict, Any, Optional, Tuple
import yaml
import json
import re
import copy
from app.logging_config import logger

def _resolve_references(schema: Dict, full_schema: Dict, resolved_refs: set = None) -> Dict:
    """
    $refを再帰的に解決する（循環参照対応版）
    
    Args:
        schema: 解決対象のスキーマ
        full_schema: OpenAPIスキーマ全体
        resolved_refs: 既に解決を試みた$refパスのセット (循環参照検出用)
        
    Returns:
        $refが解決されたスキーマ
    """
    if resolved_refs is None:
        resolved_refs = set()

    if not schema or not isinstance(schema, dict):
        return {} if schema is None else schema
    
    resolved = copy.deepcopy(schema)
    
    if "$ref" in resolved:
        ref_path = resolved["$ref"]
        
        if ref_path in resolved_refs:
            logger.warning(f"Circular reference detected: {ref_path}")
            return resolved
            
        resolved_refs.add(ref_path)
        
        if ref_path.startswith("#/"):
            parts = ref_path.lstrip("#/").split("/")
            ref_value = full_schema
            
            try:
                for part in parts:
                    if isinstance(ref_value, list) and re.match(r'^\d+$', part):
                         index = int(part)
                         if 0 <= index < len(ref_value):
                             ref_value = ref_value[index]
                         else:
                             logger.warning(f"Reference path index out of bounds: {ref_path}")
                             return resolved
                    elif isinstance(ref_value, dict) and part in ref_value:
                        ref_value = ref_value[part]
                    else:
                        logger.warning(f"Reference path not found: {ref_path}")
                        return resolved
            except (ValueError, IndexError, TypeError) as e:
                 logger.warning(f"Error resolving reference path {ref_path}: {e}")
                 return resolved
            
            del resolved["$ref"]
            
            if isinstance(ref_value, dict):
                ref_value = _resolve_references(ref_value, full_schema, resolved_refs)
                
            resolved.update(copy.deepcopy(ref_value))
            resolved = _resolve_references(resolved, full_schema, resolved_refs)
    
    if "properties" in resolved and isinstance(resolved["properties"], dict):
        for prop_name, prop_schema in resolved["properties"].items():
            if isinstance(prop_schema, dict):
                resolved["properties"][prop_name] = _resolve_references(prop_schema, full_schema, resolved_refs)
    
    if "items" in resolved and isinstance(resolved["items"], dict):
        resolved["items"] = _resolve_references(resolved["items"], full_schema, resolved_refs)
    
    for composite_key in ["allOf", "anyOf", "oneOf"]:
        if composite_key in resolved and isinstance(resolved[composite_key], list):
            for i, item_schema in enumerate(resolved[composite_key]):
                if isinstance(item_schema, dict):
                    resolved[composite_key][i] = _resolve_references(item_schema, full_schema, resolved_refs)
    
    if "additionalProperties" in resolved and isinstance(resolved["additionalProperties"], dict):
        resolved["additionalProperties"] = _resolve_references(resolved["additionalProperties"], full_schema, resolved_refs)
        
    if "parameters" in resolved and isinstance(resolved["parameters"], list):
         for i, param_schema in enumerate(resolved["parameters"]):
             if isinstance(param_schema, dict):
                 resolved["parameters"][i] = _resolve_references(param_schema, full_schema, resolved_refs)

    return resolved

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
        
        resolved_request_body = copy.deepcopy(request_body)
        content = resolved_request_body.get("content", {})
        
        if "application/json" in content:
            schema = content["application/json"].get("schema")
            if schema:
                resolved_request_body["content"]["application/json"]["schema"] = _resolve_references(schema, self.resolved_schema)
        
        for media_type, media_content in content.items():
             if media_type != "application/json" and "schema" in media_content:
                  resolved_request_body["content"][media_type]["schema"] = _resolve_references(media_content["schema"], self.resolved_schema)

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
