from typing import List, Dict, Tuple, Optional
import re
from app.logging_config import logger

class OpenAPIAnalyzer:
    """OpenAPIスキーマを解析して依存関係を抽出するクラス"""
    
    def __init__(self, schema: dict):
        """
        Args:
            schema: パース済みのOpenAPIスキーマ（dict形式）
        """
        self.schema = schema
        self.paths = schema.get("paths", {})
        self.components = schema.get("components", {})
        self.schemas = self.components.get("schemas", {})
        
    def extract_dependencies(self) -> List[Dict]:
        """
        スキーマから依存関係を抽出する
        
        Returns:
            依存関係のリスト
        """
        dependencies = []
        
        # 1. パスパラメータの依存関係を抽出
        path_param_deps = self._extract_path_parameter_dependencies()
        dependencies.extend(path_param_deps)
        
        # 2. リソース操作の依存関係を抽出（POST→PUT→GET→DELETEなど）
        resource_deps = self._extract_resource_operation_dependencies()
        dependencies.extend(resource_deps)
        
        # 3. スキーマ参照の依存関係を抽出
        schema_deps = self._extract_schema_reference_dependencies()
        dependencies.extend(schema_deps)
        
        return dependencies
    
    def _extract_path_parameter_dependencies(self) -> List[Dict]:
        """パスパラメータの依存関係を抽出する"""
        dependencies = []
        
        # パスパラメータを含むパスを特定
        paths_with_params = {path: methods for path, methods in self.paths.items() if "{" in path}
        
        for path, methods in paths_with_params.items():
            # パスからパラメータ名を抽出（例: /users/{id} → id）
            param_names = self._extract_path_params(path)
            
            for param_name in param_names:
                # パラメータを生成できる可能性のあるエンドポイントを探す
                source_endpoints = self._find_param_source_endpoints(param_name)
                
                for source_path, source_method, source_op in source_endpoints:
                    for method_name, operation in methods.items():
                        if method_name != "parameters":
                            dependencies.append({
                                "type": "path_parameter",
                                "source": {
                                    "path": source_path,
                                    "method": source_method,
                                    "parameter": param_name
                                },
                                "target": {
                                    "path": path,
                                    "method": method_name,
                                    "parameter": param_name
                                }
                            })
        
        return dependencies
    
    def _extract_path_params(self, path: str) -> List[str]:
        """パスからパラメータ名を抽出する"""
        return re.findall(r'{([^}]+)}', path)
    
    def _find_param_source_endpoints(self, param_name: str) -> List[Tuple[str, str, dict]]:
        """パラメータを生成できる可能性のあるエンドポイントを探す"""
        sources = []
        
        # 主にPOSTメソッドでIDを生成するエンドポイントを探す
        for path, methods in self.paths.items():
            for method_name, operation in methods.items():
                if method_name != "parameters":  # OpenAPIの予約語をスキップ
                    # POSTメソッドを優先的に探す（リソース作成の可能性が高い）
                    if method_name.lower() == "post":
                        # レスポンスにパラメータ名が含まれるか確認
                        if self._response_contains_param(operation, param_name):
                            sources.append((path, method_name, operation))
                            
        # POSTメソッドが見つからない場合は他のメソッドも探す
        if not sources:
            for path, methods in self.paths.items():
                for method_name, operation in methods.items():
                    if method_name != "parameters" and method_name.lower() != "post":
                        if self._response_contains_param(operation, param_name):
                            sources.append((path, method_name, operation))
        
        return sources
    
    def _response_contains_param(self, operation: dict, param_name: str) -> bool:
        """レスポンスにパラメータ名が含まれるか確認する"""
        responses = operation.get("responses", {})
        for status_code, response in responses.items():
            if status_code.startswith("2"):
                content = response.get("content", {})
                for media_type, media_content in content.items():
                    schema = media_content.get("schema", {})
                    if self._schema_contains_property(schema, param_name):
                        return True
        return False
    
    def _schema_contains_property(self, schema: dict, property_name: str) -> bool:
        """スキーマにプロパティが含まれるか確認する"""
        if "properties" in schema:
            return property_name in schema["properties"]
        
        if "$ref" in schema:
            ref_path = schema["$ref"]
            ref_schema = self._resolve_reference(ref_path)
            return self._schema_contains_property(ref_schema, property_name)
        
        return False
    
    def _resolve_reference(self, ref_path: str) -> dict:
        """$refパスを解決してスキーマを取得する"""
        if not ref_path.startswith("#/"):
            logger.warning(f"External reference not supported: {ref_path}")
            return {}
        
        parts = ref_path.lstrip("#/").split("/")
        current = self.schema
        
        for part in parts:
            if part in current:
                current = current[part]
            else:
                logger.warning(f"Reference path not found: {ref_path}")
                return {}
        
        return current
    
    def _extract_resource_operation_dependencies(self) -> List[Dict]:
        """リソース操作の依存関係を抽出する"""
        dependencies = []
        
        # リソースパスのパターンを特定（例: /users, /users/{id}）
        resource_patterns = self._identify_resource_patterns()
        
        for resource, paths in resource_patterns.items():
            # 操作の優先順位: POST → PUT → GET → DELETE
            operations_order = ["post", "put", "get", "delete"]
            
            # 各リソースの操作を順序付ける
            resource_operations = []
            for path in paths:
                for method in operations_order:
                    if method in self.paths.get(path, {}):
                        resource_operations.append((path, method))
            
            # 依存関係を作成
            for i in range(len(resource_operations) - 1):
                source_path, source_method = resource_operations[i]
                target_path, target_method = resource_operations[i + 1]
                
                dependencies.append({
                    "type": "resource_operation",
                    "source": {
                        "path": source_path,
                        "method": source_method
                    },
                    "target": {
                        "path": target_path,
                        "method": target_method
                    }
                })
        
        return dependencies
    
    def _identify_resource_patterns(self) -> Dict[str, List[str]]:
        """リソースパスのパターンを特定する"""
        resource_patterns = {}
        
        for path in self.paths.keys():
            # パスからリソース名を抽出（例: /users/{id} → users）
            parts = path.strip("/").split("/")
            if len(parts) > 0:
                resource = parts[0]
                if resource not in resource_patterns:
                    resource_patterns[resource] = []
                resource_patterns[resource].append(path)
        
        return resource_patterns
    
    def _extract_schema_reference_dependencies(self) -> List[Dict]:
        """スキーマ参照の依存関係を抽出する"""
        dependencies = []
        
        # スキーマ間の参照関係を分析
        for schema_name, schema in self.schemas.items():
            refs = self._find_references_in_schema(schema)
            
            for ref_name in refs:
                dependencies.append({
                    "type": "schema_reference",
                    "source": {
                        "schema": ref_name
                    },
                    "target": {
                        "schema": schema_name
                    }
                })
        
        # パスやレスポンスなどに含まれる$refも検出
        for path, methods in self.paths.items():
            for method_name, operation in methods.items():
                if method_name == "parameters":
                    continue
                
                # リクエストボディの$refを検出
                if "requestBody" in operation and "content" in operation["requestBody"]:
                    for media_type, content in operation["requestBody"]["content"].items():
                        if "schema" in content:
                            refs = self._find_references_in_schema(content["schema"])
                            for ref_name in refs:
                                dependencies.append({
                                    "type": "schema_reference",
                                    "source": {
                                        "schema": ref_name
                                    },
                                    "target": {
                                        "path": path,
                                        "method": method_name,
                                        "location": "requestBody"
                                    }
                                })
                
                # レスポンスの$refを検出
                if "responses" in operation:
                    for status, response in operation["responses"].items():
                        if "content" in response:
                            for media_type, content in response["content"].items():
                                if "schema" in content:
                                    refs = self._find_references_in_schema(content["schema"])
                                    for ref_name in refs:
                                        dependencies.append({
                                            "type": "schema_reference",
                                            "source": {
                                                "schema": ref_name
                                            },
                                            "target": {
                                                "path": path,
                                                "method": method_name,
                                                "location": f"response.{status}"
                                            }
                                        })
        
        return dependencies
    
    def _find_references_in_schema(self, schema: dict, visited: Optional[set] = None) -> List[str]:
        """スキーマ内の$refを再帰的に探索する"""
        if visited is None:
            visited = set()
            
        refs = []
        
        if isinstance(schema, dict):
            # 循環参照を防ぐ
            schema_id = id(schema)
            if schema_id in visited:
                return refs
            visited.add(schema_id)
            
            for key, value in schema.items():
                if key == "$ref" and isinstance(value, str) and value.startswith("#/components/schemas/"):
                    ref_name = value.split("/")[-1]
                    refs.append(ref_name)
                elif isinstance(value, (dict, list)):
                    refs.extend(self._find_references_in_schema(value, visited))
        elif isinstance(schema, list):
            for item in schema:
                if isinstance(item, (dict, list)):
                    refs.extend(self._find_references_in_schema(item, visited))
        
        return refs