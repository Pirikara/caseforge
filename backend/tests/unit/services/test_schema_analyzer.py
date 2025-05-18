from app.services.schema_analyzer import OpenAPIAnalyzer

SAMPLE_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Test API",
        "version": "1.0.0"
    },
    "paths": {
        "/users": {
            "post": {
                "summary": "Create a user",
                "responses": {
                    "201": {
                        "description": "User created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "name": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "get": {
                "summary": "List users",
                "responses": {
                    "200": {
                        "description": "List of users",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/users/{id}": {
            "get": {
                "summary": "Get a user",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "User details",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/User"
                                }
                            }
                        }
                    }
                }
            },
            "put": {
                "summary": "Update a user",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "200": {
                        "description": "User updated",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/User"
                                }
                            }
                        }
                    }
                }
            },
            "delete": {
                "summary": "Delete a user",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    }
                ],
                "responses": {
                    "204": {
                        "description": "User deleted"
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                }
            },
            "UserInput": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                },
                "required": ["name", "email"]
            }
        }
    }
}

def test_extract_dependencies():
    """依存関係抽出機能のテスト"""
    analyzer = OpenAPIAnalyzer(SAMPLE_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    assert len(dependencies) > 0
    
    dependency_types = set(dep["type"] for dep in dependencies)
    assert "path_parameter" in dependency_types
    assert "resource_operation" in dependency_types
    
    schema_refs = [dep for dep in dependencies if dep["type"] == "schema_reference"]
    assert len(schema_refs) > 0, "スキーマ参照の依存関係が見つかりません"

def test_extract_path_parameter_dependencies():
    """パスパラメータの依存関係抽出のテスト"""
    analyzer = OpenAPIAnalyzer(SAMPLE_SCHEMA)
    dependencies = analyzer._extract_path_parameter_dependencies()
    
    assert len(dependencies) > 0
    
    post_to_get_dependency = False
    for dep in dependencies:
        if (dep["source"]["path"] == "/users" and 
            dep["source"]["method"] == "post" and 
            dep["target"]["path"] == "/users/{id}" and 
            dep["target"]["parameter"] == "id"):
            post_to_get_dependency = True
            break
    
    assert post_to_get_dependency, "POST /users → GET /users/{id} の依存関係が見つかりません"

def test_extract_resource_operation_dependencies():
    """リソース操作の依存関係抽出のテスト"""
    analyzer = OpenAPIAnalyzer(SAMPLE_SCHEMA)
    dependencies = analyzer._extract_resource_operation_dependencies()
    
    assert len(dependencies) > 0
    
    resource_paths = {}
    for dep in dependencies:
        source_path = dep["source"]["path"]
        source_method = dep["source"]["method"]
        target_path = dep["target"]["path"]
        target_method = dep["target"]["method"]
        
        if source_path not in resource_paths:
            resource_paths[source_path] = []
        resource_paths[source_path].append((source_method, target_method))
    
    if "/users" in resource_paths:
        methods = [method_pair[0] for method_pair in resource_paths["/users"]]
        assert "post" in methods, "POST メソッドが見つかりません"

def test_extract_schema_reference_dependencies():
    """スキーマ参照の依存関係抽出のテスト"""
    analyzer = OpenAPIAnalyzer(SAMPLE_SCHEMA)
    dependencies = analyzer._extract_schema_reference_dependencies()
    
    assert len(dependencies) > 0
    
    user_references = [dep for dep in dependencies if dep["source"]["schema"] == "User"]
    assert len(user_references) > 0, "User スキーマへの参照が見つかりません"
