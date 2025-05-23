from app.services.openapi.analyzer import OpenAPIAnalyzer, DependencyAnalyzer

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


# 新しい body_reference 依存関係のテスト用スキーマ
BODY_REFERENCE_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Blog API",
        "version": "1.0.0"
    },
    "paths": {
        "/users": {
            "post": {
                "summary": "Create a user",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/UserInput"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "User created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/User"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/articles": {
            "post": {
                "summary": "Create an article",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ArticleInput"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Article created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Article"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/articles/{id}": {
            "put": {
                "summary": "Update an article",
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
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ArticleInput"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Article updated",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Article"
                                }
                            }
                        }
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
            },
            "Article": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "authorId": {"type": "string"}
                }
            },
            "ArticleInput": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "authorId": {"type": "string"}
                },
                "required": ["title", "content", "authorId"]
            }
        }
    }
}


def test_extract_body_reference_dependencies():
    """リクエストボディ内のIDフィールドによる依存関係抽出のテスト"""
    analyzer = OpenAPIAnalyzer(BODY_REFERENCE_SCHEMA)
    dependencies = analyzer._extract_body_reference_dependencies()
    
    assert len(dependencies) > 0, "body_reference 依存関係が見つかりません"
    
    # authorId による依存関係をチェック
    author_dependency = None
    for dep in dependencies:
        if (dep["type"] == "body_reference" and
            dep["target"]["field"] == "authorId" and
            dep["target"]["path"] == "/articles" and
            dep["target"]["method"] == "post"):
            author_dependency = dep
            break
    
    assert author_dependency is not None, "authorId による依存関係が見つかりません"
    assert author_dependency["source"]["path"] == "/users"
    assert author_dependency["source"]["method"] == "post"
    assert author_dependency["strength"] == "required"
    assert author_dependency["confidence"] > 0.5


def test_extract_dependencies_with_body_reference():
    """body_reference を含む全依存関係抽出のテスト"""
    analyzer = OpenAPIAnalyzer(BODY_REFERENCE_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    dependency_types = set(dep["type"] for dep in dependencies)
    assert "body_reference" in dependency_types, "body_reference タイプが含まれていません"
    
    body_ref_deps = [dep for dep in dependencies if dep["type"] == "body_reference"]
    assert len(body_ref_deps) > 0, "body_reference 依存関係が見つかりません"


def test_dependency_analyzer_extract_id_fields():
    """DependencyAnalyzer の ID フィールド抽出テスト"""
    analyzer = DependencyAnalyzer(BODY_REFERENCE_SCHEMA)
    
    # ArticleInput スキーマから ID フィールドを抽出
    article_input_schema = BODY_REFERENCE_SCHEMA["components"]["schemas"]["ArticleInput"]
    id_fields = analyzer.extract_id_fields(article_input_schema)
    
    assert "authorId" in id_fields, "authorId フィールドが検出されませんでした"
    assert id_fields["authorId"]["strength"] == "required"
    assert id_fields["authorId"]["confidence"] > 0.5


def test_dependency_analyzer_find_resource_endpoints():
    """DependencyAnalyzer のリソースエンドポイント検索テスト"""
    analyzer = DependencyAnalyzer(BODY_REFERENCE_SCHEMA)
    
    # authorId から対応するエンドポイントを検索
    endpoints = analyzer.find_resource_endpoints("authorId")
    
    assert len(endpoints) > 0, "対応するエンドポイントが見つかりません"
    
    # /users エンドポイントが見つかることを確認
    user_endpoint = None
    for path, method in endpoints:
        if path == "/users" and method == "post":
            user_endpoint = (path, method)
            break
    
    assert user_endpoint is not None, "/users POST エンドポイントが見つかりません"


def test_dependency_analyzer_resource_name_normalization():
    """DependencyAnalyzer のリソース名正規化テスト"""
    analyzer = DependencyAnalyzer(BODY_REFERENCE_SCHEMA)
    
    # 様々なリソース名の正規化をテスト
    test_cases = [
        ("author", ["user", "users"]),  # マッピング定義済み
        ("category", ["category", "categories"]),  # マッピング定義済み
        ("product", ["product", "products"]),  # 基本的な複数形変換
        ("company", ["company", "companies"]),  # y -> ies 変換
    ]
    
    for resource_name, expected in test_cases:
        normalized = analyzer._normalize_resource_name(resource_name)
        for expected_name in expected:
            assert expected_name in normalized, f"{expected_name} が {resource_name} の正規化結果に含まれていません"


def test_dependency_analyzer_id_field_patterns():
    """DependencyAnalyzer の ID フィールドパターンマッチングテスト"""
    analyzer = DependencyAnalyzer(BODY_REFERENCE_SCHEMA)
    
    # 様々な ID フィールドパターンをテスト
    test_cases = [
        ("authorId", True),
        ("author_id", True),
        ("authorID", True),
        ("userId", True),
        ("user_id", True),
        ("categoryId", True),
        ("name", False),
        ("title", False),
        ("content", False),
    ]
    
    for field_name, expected in test_cases:
        result = analyzer._is_id_field(field_name)
        assert result == expected, f"{field_name} の ID フィールド判定が期待値と異なります"


def test_dependency_analyzer_confidence_calculation():
    """DependencyAnalyzer の信頼度計算テスト"""
    analyzer = DependencyAnalyzer(BODY_REFERENCE_SCHEMA)
    
    # 高信頼度のケース（既知のリソース名 + 適切な型）
    high_confidence_schema = {
        "type": "string",
        "format": "uuid",
        "description": "User identifier"
    }
    confidence = analyzer._calculate_confidence("authorId", high_confidence_schema)
    assert confidence > 0.8, f"高信頼度ケースの信頼度が低すぎます: {confidence}"
    
    # 低信頼度のケース（未知のリソース名 + 型情報なし）
    low_confidence_schema = {
        "description": "Some field"
    }
    confidence = analyzer._calculate_confidence("unknownId", low_confidence_schema)
    assert confidence < 0.8, f"低信頼度ケースの信頼度が高すぎます: {confidence}"
