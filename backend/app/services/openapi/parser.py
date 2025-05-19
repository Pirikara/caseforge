from typing import List, Dict, Any
import yaml
import json
import re
import copy
from app.logging_config import logger

class EndpointParser:
    """OpenAPIスキーマからエンドポイント情報を抽出するクラス"""
    
    def __init__(self, schema_content: str):
        """
        Args:
            schema_content: OpenAPIスキーマの内容（YAML or JSON）
        """
        try:
            self.schema = yaml.safe_load(schema_content)
            logger.info("Schema loaded as YAML")
        except Exception as e:
            logger.info(f"Failed to load as YAML: {e}, trying JSON")
            try:
                self.schema = json.loads(schema_content)
                logger.info("Schema loaded as JSON")
            except Exception as e:
                logger.error(f"Failed to parse schema content: {e}")
                raise ValueError(f"Invalid schema format: {e}")
        
        # スキーマの基本構造を検証
        if not isinstance(self.schema, dict):
            logger.error(f"Schema is not a dictionary: {type(self.schema)}")
            raise ValueError("Schema must be a dictionary")
        
        # OpenAPIスキーマの必須フィールドを確認
        if "openapi" not in self.schema:
            logger.warning("Schema does not contain 'openapi' field")
        
        if "paths" not in self.schema:
            logger.warning("Schema does not contain 'paths' field")
            self.schema["paths"] = {}
    
    def parse_endpoints(self, service_id: int) -> List[Dict[str, Any]]:
        """
        スキーマからエンドポイント情報を抽出する
        
        Args:
            service_id: サービスID
            
        Returns:
            エンドポイント情報のリスト
        """
        endpoints = []
        
        logger.info(f"Parsing endpoints for service_id: {service_id}")
        
        paths = self.schema.get("paths", {})
        logger.info(f"Found {len(paths)} paths in schema")
        
        if not paths:
            logger.warning("No paths found in schema")
            return []
        
        for path, methods in paths.items():
            logger.debug(f"Processing path: {path}")
            
            if not isinstance(methods, dict):
                logger.warning(f"Path '{path}' does not contain methods dictionary: {type(methods)}")
                continue
            
            for method_name, operation in methods.items():
                if method_name.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}:
                    logger.debug(f"Skipping non-HTTP method: {method_name}")
                    continue  # HTTPメソッド以外はスキップ
                
                logger.debug(f"Processing method: {method_name} for path: {path}")
                
                try:
                    # リクエストボディ、ヘッダー、クエリパラメータ、レスポンスを抽出
                    request_body = self._extract_request_body(operation)
                    request_headers = self._extract_parameters(operation, "header")
                    request_query_params = self._extract_parameters(operation, "query")
                    responses = operation.get("responses")
                    
                    # レスポンススキーマ内の$refを解決
                    resolved_responses = {}
                    if responses:
                        for status_code, response_obj in responses.items():
                            resolved_response_obj = copy.deepcopy(response_obj)
                            if isinstance(resolved_response_obj, dict) and "content" in resolved_response_obj:
                                for media_type, media_type_obj in resolved_response_obj["content"].items():
                                    if isinstance(media_type_obj, dict) and "schema" in media_type_obj:
                                        # resolved_refs セットを渡して再帰呼び出し
                                        resolved_response_obj["content"][media_type]["schema"] = self._resolve_references(media_type_obj["schema"])
                            resolved_responses[status_code] = resolved_response_obj

                    # デバッグログを追加
                    logger.info(f"パース結果 - {path} {method_name.upper()}")
                    logger.info(f"  - request_body: {request_body is not None}")
                    logger.info(f"  - request_headers: {request_headers}")
                    logger.info(f"  - request_query_params: {request_query_params}")
                    logger.info(f"  - responses: {resolved_responses is not None}")
                    
                    endpoint_data = {
                        "service_id": service_id,
                        "path": path,
                        "method": method_name.upper(),
                        "summary": operation.get("summary"),
                        "description": operation.get("description"),
                        "request_body": request_body,
                        "request_headers": request_headers,
                        "request_query_params": request_query_params,
                        "responses": resolved_responses # 解決済みのレスポンスを使用
                    }
                    
                    endpoints.append(endpoint_data)
                    logger.debug(f"Added endpoint: {path} {method_name.upper()}")
                except Exception as e:
                    logger.error(f"Error processing endpoint {path} {method_name}: {e}", exc_info=True)
                    # エラーが発生しても処理を続行
                    continue
        
        logger.info(f"Parsed {len(endpoints)} endpoints from schema")
        return endpoints
    
    def _extract_request_body(self, operation: Dict) -> Dict:
        """リクエストボディを抽出する"""
        if "requestBody" not in operation:
            return None
        
        request_body = operation["requestBody"]
        content = request_body.get("content", {})
        
        # application/json を優先
        if "application/json" in content:
            schema = content["application/json"].get("schema")
            if schema:
                return self._resolve_references(schema)
        
        # 他のContent-Typeがあれば最初のものを使用
        for content_type, content_schema in content.items():
            schema = content_schema.get("schema")
            if schema:
                return self._resolve_references(schema)
        
        return None
    
    def _extract_parameters(self, operation: Dict, param_in: str) -> Dict:
        """指定したinタイプのパラメータを抽出する"""
        result = {}
        
        if "parameters" not in operation:
            return result
        
        for param in operation["parameters"]:
            if param.get("in") == param_in:
                name = param.get("name")
                if name:
                    param_schema = param.get("schema", {})
                    resolved_schema = self._resolve_references(param_schema)
                    result[name] = {
                        "required": param.get("required", False),
                        "schema": resolved_schema
                    }
        
        return result
    
    def _resolve_references(self, schema: Dict, resolved_refs: set = None) -> Dict:
        """
        $refを再帰的に解決する（循環参照対応版）
        
        Args:
            schema: 解決対象のスキーマ
            resolved_refs: 既に解決を試みた$refパスのセット (循環参照検出用)
            
        Returns:
            $refが解決されたスキーマ
        """
        if resolved_refs is None:
            resolved_refs = set()

        if not schema or not isinstance(schema, dict):
            return {} if schema is None else schema
        
        # 深いコピーを作成して元のスキーマを変更しないようにする
        resolved = copy.deepcopy(schema)
        
        # $refがあれば解決を試みる
        if "$ref" in resolved:
            ref_path = resolved["$ref"]
            logger.debug(f"Resolving reference: {ref_path}")
            
            # 循環参照の検出
            if ref_path in resolved_refs:
                logger.warning(f"Circular reference detected: {ref_path}")
                # 循環参照の場合は解決をスキップし、現在の$refを残すか、エラーを示す値を返すなど検討
                # ここでは$refを残したまま返す
                return resolved
                
            # 解決を試みる前にパスを記録
            resolved_refs.add(ref_path)
            
            if ref_path.startswith("#/"):
                parts = ref_path.lstrip("#/").split("/")
                ref_value = self.schema
                
                try:
                    for part in parts:
                        # 配列のインデックス参照に対応 (例: #/paths/~1items/get/parameters/0)
                        if isinstance(ref_value, list) and re.match(r'^\d+$', part):
                             index = int(part)
                             if 0 <= index < len(ref_value):
                                 ref_value = ref_value[index]
                             else:
                                 logger.warning(f"Reference path index out of bounds: {ref_path}")
                                 return resolved # 参照が見つからない場合は解決をスキップ
                        elif isinstance(ref_value, dict) and part in ref_value:
                            ref_value = ref_value[part]
                        else:
                            logger.warning(f"Reference path not found: {ref_path}")
                            return resolved # 参照が見つからない場合は解決をスキップ
                except (ValueError, IndexError, TypeError) as e:
                     logger.warning(f"Error resolving reference path {ref_path}: {e}")
                     return resolved # パス解決中のエラーもスキップ
                
                # $refを解決した値で置き換え
                del resolved["$ref"]
                
                # 解決した値自体にさらに$refがある可能性があるので、まずref_valueを再帰的に解決
                if isinstance(ref_value, dict):
                    # 解決済みのパスセットを渡して再帰呼び出し
                    ref_value = self._resolve_references(ref_value, resolved_refs)
                    
                resolved.update(copy.deepcopy(ref_value))
                
                # 解決した結果（resolved）にさらにネストされた$refがある可能性があるので再帰的に解決
                # この行は既存のネストされた$ref解決ロジックと連携する
                # 解決済みのパスセットを渡して再帰呼び出し
                resolved = self._resolve_references(resolved, resolved_refs)
        
        # ネストされたプロパティ内の$refも解決
        if "properties" in resolved and isinstance(resolved["properties"], dict):
            for prop_name, prop_schema in resolved["properties"].items():
                if isinstance(prop_schema, dict):
                    # 解決済みのパスセットを渡して再帰呼び出し
                    resolved["properties"][prop_name] = self._resolve_references(prop_schema, resolved_refs)
        
        # 配列内の$refも解決（items内の$ref）
        if "items" in resolved and isinstance(resolved["items"], dict):
            # 解決済みのパスセットを渡して再帰呼び出し
            resolved["items"] = self._resolve_references(resolved["items"], resolved_refs)
        
        # allOf, anyOf, oneOfなどの複合型も解決
        for composite_key in ["allOf", "anyOf", "oneOf"]:
            if composite_key in resolved and isinstance(resolved[composite_key], list):
                for i, item_schema in enumerate(resolved[composite_key]):
                    if isinstance(item_schema, dict):
                        # 解決済みのパスセットを渡して再帰呼び出し
                        resolved[composite_key][i] = self._resolve_references(item_schema, resolved_refs)
        
        # additionalPropertiesも解決
        if "additionalProperties" in resolved and isinstance(resolved["additionalProperties"], dict):
            # 解決済みのパスセットを渡して再帰呼び出し
            resolved["additionalProperties"] = self._resolve_references(resolved["additionalProperties"], resolved_refs)
            
        # 配列のインデックス参照に対応するためのparameters内の$ref解決
        if "parameters" in resolved and isinstance(resolved["parameters"], list):
             for i, param_schema in enumerate(resolved["parameters"]):
                 if isinstance(param_schema, dict):
                     # 解決済みのパスセットを渡して再帰呼び出し
                     resolved["parameters"][i] = self._resolve_references(param_schema, resolved_refs)

        return resolved
