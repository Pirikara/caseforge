from typing import List, Dict, Tuple, Optional, Set
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
        
        path_param_deps = self._extract_path_parameter_dependencies()
        dependencies.extend(path_param_deps)
        
        resource_deps = self._extract_resource_operation_dependencies()
        dependencies.extend(resource_deps)
        
        schema_deps = self._extract_schema_reference_dependencies()
        dependencies.extend(schema_deps)
        
        # 新しい依存タイプ: body_reference
        body_deps = self._extract_body_reference_dependencies()
        dependencies.extend(body_deps)
        
        return dependencies
    
    def _extract_path_parameter_dependencies(self) -> List[Dict]:
        """パスパラメータの依存関係を抽出する"""
        dependencies = []
        
        paths_with_params = {path: methods for path, methods in self.paths.items() if "{" in path}
        
        for path, methods in paths_with_params.items():
            param_names = self._extract_path_params(path)
            
            for param_name in param_names:
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
        
        for path, methods in self.paths.items():
            for method_name, operation in methods.items():
                if method_name != "parameters":
                    if method_name.lower() == "post":
                        if self._response_contains_param(operation, param_name):
                            sources.append((path, method_name, operation))
                            
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
        
        resource_patterns = self._identify_resource_patterns()
        
        for resource, paths in resource_patterns.items():
            operations_order = ["post", "put", "get", "delete"]
            
            resource_operations = []
            for path in paths:
                for method in operations_order:
                    if method in self.paths.get(path, {}):
                        resource_operations.append((path, method))
            
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
        
        for path, methods in self.paths.items():
            for method_name, operation in methods.items():
                if method_name == "parameters":
                    continue
                
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
    
    def _extract_body_reference_dependencies(self) -> List[Dict]:
        """リクエストボディ内のIDフィールドによる依存関係を抽出する"""
        dependencies = []
        dependency_analyzer = DependencyAnalyzer(self.schema)
        
        for path, methods in self.paths.items():
            for method_name, operation in methods.items():
                if method_name == "parameters":
                    continue
                
                # リクエストボディを持つ操作のみ処理
                if "requestBody" not in operation:
                    continue
                
                request_body = operation["requestBody"]
                if "content" not in request_body:
                    continue
                
                for media_type, content in request_body["content"].items():
                    if "schema" not in content:
                        continue
                    
                    schema = content["schema"]
                    id_fields = dependency_analyzer.extract_id_fields(schema)
                    
                    for field_name, field_info in id_fields.items():
                        # IDフィールドから対応するリソースエンドポイントを推定
                        target_endpoints = dependency_analyzer.find_resource_endpoints(field_name)
                        
                        for target_path, target_method in target_endpoints:
                            dependencies.append({
                                "type": "body_reference",
                                "source": {
                                    "path": target_path,
                                    "method": target_method
                                },
                                "target": {
                                    "path": path,
                                    "method": method_name,
                                    "field": field_name
                                },
                                "strength": field_info.get("strength", "required"),
                                "confidence": field_info.get("confidence", 0.8)
                            })
        
        return dependencies


class DependencyAnalyzer:
    """依存関係解析エンジン"""
    
    def __init__(self, schema: dict):
        self.schema = schema
        self.paths = schema.get("paths", {})
        self.components = schema.get("components", {})
        self.schemas = self.components.get("schemas", {})
        
        # IDフィールドのパターン
        self.id_patterns = [
            r'(.+)[Ii]d$',      # authorId, userId, categoryId
            r'(.+)_id$',        # author_id, user_id, category_id
            r'(.+)[Ii][Dd]$',   # authorID, userID, categoryID
        ]
        
        # リソース名の正規化マッピング
        self.resource_mappings = {
            'author': ['user', 'users'],
            'user': ['user', 'users'],
            'category': ['category', 'categories'],
            'article': ['article', 'articles'],
            'post': ['post', 'posts'],
            'comment': ['comment', 'comments'],
        }
    
    def extract_id_fields(self, schema: dict, visited: Optional[Set] = None) -> Dict[str, Dict]:
        """スキーマからIDフィールドを抽出する"""
        if visited is None:
            visited = set()
        
        id_fields = {}
        
        if isinstance(schema, dict):
            schema_id = id(schema)
            if schema_id in visited:
                return id_fields
            visited.add(schema_id)
            
            # $refの解決
            if "$ref" in schema:
                ref_schema = self._resolve_reference(schema["$ref"])
                return self.extract_id_fields(ref_schema, visited)
            
            # propertiesの処理
            if "properties" in schema:
                for field_name, field_schema in schema["properties"].items():
                    if self._is_id_field(field_name):
                        strength = self._determine_field_strength(field_name, schema)
                        confidence = self._calculate_confidence(field_name, field_schema)
                        
                        id_fields[field_name] = {
                            "strength": strength,
                            "confidence": confidence,
                            "schema": field_schema
                        }
                    
                    # ネストしたオブジェクトの処理
                    if isinstance(field_schema, dict):
                        nested_fields = self.extract_id_fields(field_schema, visited)
                        for nested_field, nested_info in nested_fields.items():
                            full_field_name = f"{field_name}.{nested_field}"
                            id_fields[full_field_name] = nested_info
            
            # allOf, oneOf, anyOfの処理
            for key in ["allOf", "oneOf", "anyOf"]:
                if key in schema:
                    for sub_schema in schema[key]:
                        nested_fields = self.extract_id_fields(sub_schema, visited)
                        id_fields.update(nested_fields)
        
        return id_fields
    
    def _is_id_field(self, field_name: str) -> bool:
        """フィールド名がIDフィールドかどうか判定する"""
        for pattern in self.id_patterns:
            if re.match(pattern, field_name):
                return True
        return False
    
    def _determine_field_strength(self, field_name: str, schema: dict) -> str:
        """フィールドの依存関係の強度を判定する"""
        required_fields = schema.get("required", [])
        
        if field_name in required_fields:
            return "required"
        else:
            return "optional"
    
    def _calculate_confidence(self, field_name: str, field_schema: dict) -> float:
        """依存関係の信頼度を計算する"""
        confidence = 0.5  # ベース信頼度
        
        # フィールド名のパターンマッチング精度
        for pattern in self.id_patterns:
            match = re.match(pattern, field_name)
            if match:
                resource_name = match.group(1).lower()
                if resource_name in self.resource_mappings:
                    confidence += 0.3
                else:
                    confidence += 0.2
                break
        
        # スキーマ情報による信頼度調整
        if isinstance(field_schema, dict):
            # 型情報
            if field_schema.get("type") in ["integer", "string"]:
                confidence += 0.1
            
            # フォーマット情報
            if field_schema.get("format") in ["uuid", "int64"]:
                confidence += 0.1
            
            # 説明文による判定
            description = field_schema.get("description", "").lower()
            if any(keyword in description for keyword in ["id", "identifier", "reference"]):
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def find_resource_endpoints(self, field_name: str) -> List[Tuple[str, str]]:
        """IDフィールドから対応するリソースエンドポイントを探す"""
        endpoints = []
        
        # フィールド名からリソース名を抽出
        resource_name = self._extract_resource_name(field_name)
        if not resource_name:
            return endpoints
        
        # リソース名の正規化
        possible_resources = self._normalize_resource_name(resource_name)
        
        # 対応するエンドポイントを検索
        for path, methods in self.paths.items():
            path_parts = path.strip("/").split("/")
            if len(path_parts) == 0:
                continue
            
            base_resource = path_parts[0].lower()
            
            # リソース名がマッチするかチェック
            if base_resource in possible_resources:
                # POST操作を優先的に探す（リソース作成操作）
                if "post" in methods:
                    endpoints.append((path, "post"))
                # POST操作がない場合は他の操作も考慮
                elif "get" in methods:
                    endpoints.append((path, "get"))
        
        return endpoints
    
    def _extract_resource_name(self, field_name: str) -> Optional[str]:
        """フィールド名からリソース名を抽出する"""
        for pattern in self.id_patterns:
            match = re.match(pattern, field_name)
            if match:
                return match.group(1).lower()
        return None
    
    def _normalize_resource_name(self, resource_name: str) -> List[str]:
        """リソース名を正規化して可能な名前のリストを返す"""
        if resource_name in self.resource_mappings:
            return self.resource_mappings[resource_name]
        
        # 基本的な単数形/複数形の変換
        possible_names = [resource_name]
        
        # 複数形の推定
        if resource_name.endswith('y'):
            possible_names.append(resource_name[:-1] + 'ies')
        elif resource_name.endswith(('s', 'sh', 'ch', 'x', 'z')):
            possible_names.append(resource_name + 'es')
        else:
            possible_names.append(resource_name + 's')
        
        # 単数形の推定（既に複数形の場合）
        if resource_name.endswith('ies'):
            possible_names.append(resource_name[:-3] + 'y')
        elif resource_name.endswith('es'):
            possible_names.append(resource_name[:-2])
        elif resource_name.endswith('s') and len(resource_name) > 1:
            possible_names.append(resource_name[:-1])
        
        return list(set(possible_names))
    
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
    
    def check_circular_dependencies(self, dependencies: List[Dict]) -> List[Dict]:
        """循環参照をチェックし、警告を出力する"""
        # 依存関係グラフの構築
        graph = {}
        for dep in dependencies:
            source_key = f"{dep['source']['path']}:{dep['source']['method']}"
            target_key = f"{dep['target']['path']}:{dep['target']['method']}"
            
            if source_key not in graph:
                graph[source_key] = []
            graph[source_key].append(target_key)
        
        # DFSによる循環検出
        visited = set()
        rec_stack = set()
        circular_deps = []
        
        def dfs(node, path):
            if node in rec_stack:
                # 循環を検出
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_deps.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        # 循環参照が見つかった場合の警告
        for cycle in circular_deps:
            logger.warning(f"Circular dependency detected: {' -> '.join(cycle)}")
        
        return dependencies
