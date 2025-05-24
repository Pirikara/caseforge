from app.services.openapi.analyzer import OpenAPIAnalyzer, DependencyAnalyzer
from app.services.openapi.parser import parse_openapi_schema
import pytest
import json
import yaml # yaml モジュールをインポート

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

REALWORLD_SCHEMA = {
  "openapi": "3.0.1",
  "info": {
    "title": "RealWorld Conduit API",
    "description": "Conduit API documentation",
    "contact": {
      "name": "RealWorld",
      "url": "https://realworld-docs.netlify.app/"
    },
    "license": {
      "name": "MIT License",
      "url": "https://opensource.org/licenses/MIT"
    },
    "version": "1.0.0"
  },
  "tags": [
    {
      "name": "Articles"
    },
    {
      "name": "Comments"
    },
    {
      "name": "Favorites"
    },
    {
      "name": "Profile"
    },
    {
      "name": "Tags"
    },
    {
      "name": "User and Authentication"
    }
  ],
  "servers": [
    {
      "url": "https://api.realworld.io/api"
    }
  ],
  "paths": {
    "/users/login": {
      "post": {
        "tags": [
          "User and Authentication"
        ],
        "summary": "Existing user login",
        "description": "Login for existing user",
        "operationId": "Login",
        "requestBody": {
          "$ref": "#/components/requestBodies/LoginUserRequest"
        },
        "responses": {
          "200": {
            "$ref": "#/components/responses/UserResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "x-codegen-request-body-name": "body"
      }
    },
    "/users": {
      "post": {
        "tags": [
          "User and Authentication"
        ],
        "description": "Register a new user",
        "operationId": "CreateUser",
        "requestBody": {
          "$ref": "#/components/requestBodies/NewUserRequest"
        },
        "responses": {
          "201": {
            "$ref": "#/components/responses/UserResponse"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "x-codegen-request-body-name": "body"
      }
    },
    "/user": {
      "get": {
        "tags": [
          "User and Authentication"
        ],
        "summary": "Get current user",
        "description": "Gets the currently logged-in user",
        "operationId": "GetCurrentUser",
        "responses": {
          "200": {
            "$ref": "#/components/responses/UserResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      },
      "put": {
        "tags": [
          "User and Authentication"
        ],
        "summary": "Update current user",
        "description": "Updated user information for current user",
        "operationId": "UpdateCurrentUser",
        "requestBody": {
          "$ref": "#/components/requestBodies/UpdateUserRequest"
        },
        "responses": {
          "200": {
            "$ref": "#/components/responses/UserResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ],
        "x-codegen-request-body-name": "body"
      }
    },
    "/profiles/{username}": {
      "get": {
        "tags": [
          "Profile"
        ],
        "summary": "Get a profile",
        "description": "Get a profile of a user of the system. Auth is optional",
        "operationId": "GetProfileByUsername",
        "parameters": [
          {
            "name": "username",
            "in": "path",
            "description": "Username of the profile to get",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/ProfileResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        }
      }
    },
    "/profiles/{username}/follow": {
      "post": {
        "tags": [
          "Profile"
        ],
        "summary": "Follow a user",
        "description": "Follow a user by username",
        "operationId": "FollowUserByUsername",
        "parameters": [
          {
            "name": "username",
            "in": "path",
            "description": "Username of the profile you want to follow",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/ProfileResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      },
      "delete": {
        "tags": [
          "Profile"
        ],
        "summary": "Unfollow a user",
        "description": "Unfollow a user by username",
        "operationId": "UnfollowUserByUsername",
        "parameters": [
          {
            "name": "username",
            "in": "path",
            "description": "Username of the profile you want to unfollow",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/ProfileResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      }
    },
    "/articles/feed": {
      "get": {
        "tags": [
          "Articles"
        ],
        "summary": "Get recent articles from users you follow",
        "description": "Get most recent articles from users you follow. Use query parameters\n        to limit. Auth is required",
        "operationId": "GetArticlesFeed",
        "parameters": [
          {
            "$ref": "#/components/parameters/offsetParam"
          },
          {
            "$ref": "#/components/parameters/limitParam"
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/MultipleArticlesResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      }
    },
    "/articles": {
      "get": {
        "tags": [
          "Articles"
        ],
        "summary": "Get recent articles globally",
        "description": "Get most recent articles globally. Use query parameters to filter\n        results. Auth is optional",
        "operationId": "GetArticles",
        "parameters": [
          {
            "name": "tag",
            "in": "query",
            "description": "Filter by tag",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "author",
            "in": "query",
            "description": "Filter by author (username)",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "favorited",
            "in": "query",
            "description": "Filter by favorites of a user (username)",
            "schema": {
              "type": "string"
            }
          },
          {
            "$ref": "#/components/parameters/offsetParam"
          },
          {
            "$ref": "#/components/parameters/limitParam"
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/MultipleArticlesResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        }
      },
      "post": {
        "tags": [
          "Articles"
        ],
        "summary": "Create an article",
        "description": "Create an article. Auth is required",
        "operationId": "CreateArticle",
        "requestBody": {
          "$ref": "#/components/requestBodies/NewArticleRequest"
        },
        "responses": {
          "201": {
            "$ref": "#/components/responses/SingleArticleResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ],
        "x-codegen-request-body-name": "article"
      }
    },
    "/articles/{slug}": {
      "get": {
        "tags": [
          "Articles"
        ],
        "summary": "Get an article",
        "description": "Get an article. Auth not required",
        "operationId": "GetArticle",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article to get",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/SingleArticleResponse"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        }
      },
      "put": {
        "tags": [
          "Articles"
        ],
        "summary": "Update an article",
        "description": "Update an article. Auth is required",
        "operationId": "UpdateArticle",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article to update",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "$ref": "#/components/requestBodies/UpdateArticleRequest"
        },
        "responses": {
          "200": {
            "$ref": "#/components/responses/SingleArticleResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ],
        "x-codegen-request-body-name": "article"
      },
      "delete": {
        "tags": [
          "Articles"
        ],
        "summary": "Delete an article",
        "description": "Delete an article. Auth is required",
        "operationId": "DeleteArticle",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article to delete",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/EmptyOkResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      }
    },
    "/articles/{slug}/comments": {
      "get": {
        "tags": [
          "Comments"
        ],
        "summary": "Get comments for an article",
        "description": "Get the comments for an article. Auth is optional",
        "operationId": "GetArticleComments",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article that you want to get comments for",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/MultipleCommentsResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        }
      },
      "post": {
        "tags": [
          "Comments"
        ],
        "summary": "Create a comment for an article",
        "description": "Create a comment for an article. Auth is required",
        "operationId": "CreateArticleComment",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article that you want to create a comment for",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "$ref": "#/components/requestBodies/NewCommentRequest"
        },
        "responses": {
          "200": {
            "$ref": "#/components/responses/SingleCommentResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ],
        "x-codegen-request-body-name": "comment"
      }
    },
    "/articles/{slug}/comments/{id}": {
      "delete": {
        "tags": [
          "Comments"
        ],
        "summary": "Delete a comment for an article",
        "description": "Delete a comment for an article. Auth is required",
        "operationId": "DeleteArticleComment",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article that you want to delete a comment for",
            "required": True,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "id",
            "in": "path",
            "description": "ID of the comment you want to delete",
            "required": True,
            "schema": {
              "type": "integer"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/EmptyOkResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      }
    },
    "/articles/{slug}/favorite": {
      "post": {
        "tags": [
          "Favorites"
        ],
        "summary": "Favorite an article",
        "description": "Favorite an article. Auth is required",
        "operationId": "CreateArticleFavorite",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article that you want to favorite",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/SingleArticleResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      },
      "delete": {
        "tags": [
          "Favorites"
        ],
        "summary": "Unfavorite an article",
        "description": "Unfavorite an article. Auth is required",
        "operationId": "DeleteArticleFavorite",
        "parameters": [
          {
            "name": "slug",
            "in": "path",
            "description": "Slug of the article that you want to unfavorite",
            "required": True,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "$ref": "#/components/responses/SingleArticleResponse"
          },
          "401": {
            "$ref": "#/components/responses/Unauthorized"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        },
        "security": [
          {
            "Token": []
          }
        ]
      }
    },
    "/tags": {
      "get": {
        "tags": [
          "Tags"
        ],
        "summary": "Get tags",
        "description": "Get tags. Auth not required",
        "operationId": "GetTags",
        "responses": {
          "200": {
            "$ref": "#/components/responses/TagsResponse"
          },
          "422": {
            "$ref": "#/components/responses/GenericError"
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "LoginUser": {
        "required": [
          "email",
          "password"
        ],
        "type": "object",
        "properties": {
          "email": {
            "type": "string"
          },
          "password": {
            "type": "string",
            "format": "password"
          }
        }
      },
      "NewUser": {
        "required": [
          "email",
          "password",
          "username"
        ],
        "type": "object",
        "properties": {
          "username": {
            "type": "string"
          },
          "email": {
            "type": "string"
          },
          "password": {
            "type": "string",
            "format": "password"
          }
        }
      },
      "User": {
        "required": [
          "bio",
          "email",
          "image",
          "token",
          "username"
        ],
        "type": "object",
        "properties": {
          "email": {
            "type": "string"
          },
          "token": {
            "type": "string"
          },
          "username": {
            "type": "string"
          },
          "bio": {
            "type": "string"
          },
          "image": {
            "type": "string"
          }
        }
      },
      "UpdateUser": {
        "type": "object",
        "properties": {
          "email": {
            "type": "string"
          },
          "password": {
            "type": "string"
          },
          "username": {
            "type": "string"
          },
          "bio": {
            "type": "string"
          },
          "image": {
            "type": "string"
          }
        }
      },
      "Profile": {
        "required": [
          "bio",
          "following",
          "image",
          "username"
        ],
        "type": "object",
        "properties": {
          "username": {
            "type": "string"
          },
          "bio": {
            "type": "string"
          },
          "image": {
            "type": "string"
          },
          "following": {
            "type": "boolean"
          }
        }
      },
      "Article": {
        "required": [
          "author",
          "body",
          "createdAt",
          "description",
          "favorited",
          "favoritesCount",
          "slug",
          "tagList",
          "title",
          "updatedAt"
        ],
        "type": "object",
        "properties": {
          "slug": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "tagList": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "createdAt": {
            "type": "string",
            "format": "date-time"
          },
          "updatedAt": {
            "type": "string",
            "format": "date-time"
          },
          "favorited": {
            "type": "boolean"
          },
          "favoritesCount": {
            "type": "integer"
          },
          "author": {
            "$ref": "#/components/schemas/Profile"
          }
        }
      },
      "Comment": {
        "required": [
          "author",
          "body",
          "createdAt",
          "id",
          "updatedAt"
        ],
        "type": "object",
        "properties": {
          "id": {
            "type": "integer"
          },
          "createdAt": {
            "type": "string",
            "format": "date-time"
          },
          "updatedAt": {
            "type": "string",
            "format": "date-time"
          },
          "body": {
            "type": "string"
          },
          "author": {
            "$ref": "#/components/schemas/Profile"
          }
        }
      },
      "Tag": {
        "type": "string"
      }
    },
    "responses": {
      "UserResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "user"
              ],
              "type": "object",
              "properties": {
                "user": {
                  "$ref": "#/components/schemas/User"
                }
              }
            }
          }
        }
      },
      "ProfileResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "profile"
              ],
              "type": "object",
              "properties": {
                "profile": {
                  "$ref": "#/components/schemas/Profile"
                }
              }
            }
          }
        }
      },
      "MultipleArticlesResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "articles",
                "articlesCount"
              ],
              "type": "object",
              "properties": {
                "articles": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Article"
                  }
                },
                "articlesCount": {
                  "type": "integer"
                }
              }
            }
          }
        }
      },
      "SingleArticleResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "article"
              ],
              "type": "object",
              "properties": {
                "article": {
                  "$ref": "#/components/schemas/Article"
                }
              }
            }
          }
        }
      },
      "MultipleCommentsResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "comments"
              ],
              "type": "object",
              "properties": {
                "comments": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Comment"
                  }
                }
              }
            }
          }
        }
      },
      "SingleCommentResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "comment"
              ],
              "type": "object",
              "properties": {
                "comment": {
                  "$ref": "#/components/schemas/Comment"
                }
              }
            }
          }
        }
      },
      "TagsResponse": {
        "description": "Successful operation",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "tags"
              ],
              "type": "object",
              "properties": {
                "tags": {
                  "type": "array",
                  "items": {
                    "$ref": "#/components/schemas/Tag"
                  }
                }
              }
            }
          }
        }
      },
      "GenericError": {
        "description": "Unexpected error",
        "content": {
          "application/json": {
            "schema": {
              "$ref": "#/components/schemas/GenericErrorModel"
            }
          }
        }
      },
      "Unauthorized": {
        "description": "Unauthorized",
        "content": {
          "application/json": {
            "schema": {
              "$ref": "#/components/schemas/GenericErrorModel"
            }
          }
        }
      },
      "EmptyOkResponse": {
        "description": "Successful operation - There's no body content"
      }
    },
    "requestBodies": {
      "LoginUserRequest": {
        "description": "Multiple users",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "user"
              ],
              "type": "object",
              "properties": {
                "user": {
                  "$ref": "#/components/schemas/LoginUser"
                }
              }
            }
          }
        }
      },
      "NewUserRequest": {
        "description": "Multiple users",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "user"
              ],
              "type": "object",
              "properties": {
                "user": {
                  "$ref": "#/components/schemas/NewUser"
                }
              }
            }
          }
        }
      },
      "UpdateUserRequest": {
        "description": "Multiple users",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "user"
              ],
              "type": "object",
              "properties": {
                "user": {
                  "$ref": "#/components/schemas/UpdateUser"
                }
              }
            }
          }
        }
      },
      "NewArticleRequest": {
        "description": "Multiple articles",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "article"
              ],
              "type": "object",
              "properties": {
                "article": {
                  "$ref": "#/components/schemas/NewArticle"
                }
              }
            }
          }
        }
      },
      "UpdateArticleRequest": {
        "description": "Multiple articles",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "article"
              ],
              "type": "object",
              "properties": {
                "article": {
                  "$ref": "#/components/schemas/UpdateArticle"
                }
              }
            }
          }
        }
      },
      "NewCommentRequest": {
        "description": "Multiple comments",
        "content": {
          "application/json": {
            "schema": {
              "required": [
                "comment"
              ],
              "type": "object",
              "properties": {
                "comment": {
                  "$ref": "#/components/schemas/NewComment"
                }
              }
            }
          }
        }
      }
    },
    "parameters": {
      "offsetParam": {
        "name": "offset",
        "in": "query",
        "description": "The number of items to skip before starting to collect the result set.",
        "required": False,
        "schema": {
          "type": "integer",
          "format": "int32",
          "default": 0
        }
      },
      "limitParam": {
        "name": "limit",
        "in": "query",
        "description": "The number of items to return.",
        "required": False,
        "schema": {
          "type": "integer",
          "format": "int32",
          "default": 20
        }
      }
    },
    "securitySchemes": {
      "Token": {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header"
      }
    },
    "schemas": {
      "NewArticle": {
        "required": [
          "body",
          "description",
          "title"
        ],
        "type": "object",
        "properties": {
          "title": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "tagList": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        }
      },
      "UpdateArticle": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "body": {
            "type": "string"
          },
          "tagList": {
            "type": "array",
            "items": {
              "type": "string"
            }
          }
        }
      },
      "NewComment": {
        "required": [
          "body"
        ],
        "type": "object",
        "properties": {
          "body": {
            "type": "string"
          }
        }
      },
      "GenericErrorModel": {
        "required": [
          "errors"
        ],
        "type": "object",
        "properties": {
          "errors": {
            "required": [
              "body"
            ],
            "type": "object",
            "properties": {
              "body": {
                "type": "array",
                "items": {
                  "type": "string"
                }
              }
            }
          }
        }
      }
    }
  }
}

# test.yaml の内容をここに埋め込む
REALWORLD_SCHEMA_CONTENT = """
openapi: 3.0.1
info:
  title: RealWorld Conduit API
  description: Conduit API documentation
  contact:
    name: RealWorld
    url: https://realworld-docs.netlify.app/
  license:
    name: MIT License
    url: https://opensource.org/licenses/MIT
  version: 1.0.0
tags:
  - name: Articles
  - name: Comments
  - name: Favorites
  - name: Profile
  - name: Tags
  - name: User and Authentication
servers:
  - url: https://api.realworld.io/api
paths:
  /users/login:
    post:
      tags:
        - User and Authentication
      summary: Existing user login
      description: Login for existing user
      operationId: Login
      requestBody:
        $ref: '#/components/requestBodies/LoginUserRequest'
      responses:
        '200':
          $ref: '#/components/responses/UserResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      x-codegen-request-body-name: body
  /users:
    post:
      tags:
        - User and Authentication
      description: Register a new user
      operationId: CreateUser
      requestBody:
        $ref: '#/components/requestBodies/NewUserRequest'
      responses:
        '201':
          $ref: '#/components/responses/UserResponse'
        '422':
          $ref: '#/components/responses/GenericError'
      x-codegen-request-body-name: body
  /user:
    get:
      tags:
        - User and Authentication
      summary: Get current user
      description: Gets the currently logged-in user
      operationId: GetCurrentUser
      responses:
        '200':
          $ref: '#/components/responses/UserResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
    put:
      tags:
        - User and Authentication
      summary: Update current user
      description: Updated user information for current user
      operationId: UpdateCurrentUser
      requestBody:
        $ref: '#/components/requestBodies/UpdateUserRequest'
      responses:
        '200':
          $ref: '#/components/responses/UserResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
      x-codegen-request-body-name: body
  /profiles/{username}:
    get:
      tags:
        - Profile
      summary: Get a profile
      description: Get a profile of a user of the system. Auth is optional
      operationId: GetProfileByUsername
      parameters:
        - name: username
          in: path
          description: Username of the profile to get
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/ProfileResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
  /profiles/{username}/follow:
    post:
      tags:
        - Profile
      summary: Follow a user
      description: Follow a user by username
      operationId: FollowUserByUsername
      parameters:
        - name: username
          in: path
          description: Username of the profile you want to follow
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/ProfileResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
    delete:
      tags:
        - Profile
      summary: Unfollow a user
      description: Unfollow a user by username
      operationId: UnfollowUserByUsername
      parameters:
        - name: username
          in: path
          description: Username of the profile you want to unfollow
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/ProfileResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
  /articles/feed:
    get:
      tags:
        - Articles
      summary: Get recent articles from users you follow
      description: Get most recent articles from users you follow. Use query parameters
        to limit. Auth is required
      operationId: GetArticlesFeed
      parameters:
        - $ref: '#/components/parameters/offsetParam'
        - $ref: '#/components/parameters/limitParam'
      responses:
        '200':
          $ref: '#/components/responses/MultipleArticlesResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
  /articles:
    get:
      tags:
        - Articles
      summary: Get recent articles globally
      description: Get most recent articles globally. Use query parameters to filter
        results. Auth is optional
      operationId: GetArticles
      parameters:
        - name: tag
          in: query
          description: Filter by tag
          schema:
            type: string
        - name: author
          in: query
          description: Filter by author (username)
          schema:
            type: string
        - name: favorited
          in: query
          description: Filter by favorites of a user (username)
          schema:
            type: string
        - $ref: '#/components/parameters/offsetParam'
        - $ref: '#/components/parameters/limitParam'
      responses:
        '200':
          $ref: '#/components/responses/MultipleArticlesResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
    post:
      tags:
        - Articles
      summary: Create an article
      description: Create an article. Auth is required
      operationId: CreateArticle
      requestBody:
        $ref: '#/components/requestBodies/NewArticleRequest'
      responses:
        '201':
          $ref: '#/components/responses/SingleArticleResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
      x-codegen-request-body-name: article
  /articles/{slug}:
    get:
      tags:
        - Articles
      summary: Get an article
      description: Get an article. Auth not required
      operationId: GetArticle
      parameters:
        - name: slug
          in: path
          description: Slug of the article to get
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/SingleArticleResponse'
        '422':
          $ref: '#/components/responses/GenericError'
    put:
      tags:
        - Articles
      summary: Update an article
      description: Update an article. Auth is required
      operationId: UpdateArticle
      parameters:
        - name: slug
          in: path
          description: Slug of the article to update
          required: true
          schema:
            type: string
      requestBody:
        $ref: '#/components/requestBodies/UpdateArticleRequest'
      responses:
        '200':
          $ref: '#/components/responses/SingleArticleResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
      x-codegen-request-body-name: article
    delete:
      tags:
        - Articles
      summary: Delete an article
      description: Delete an article. Auth is required
      operationId: DeleteArticle
      parameters:
        - name: slug
          in: path
          description: Slug of the article to delete
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/EmptyOkResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
  /articles/{slug}/comments:
    get:
      tags:
        - Comments
      summary: Get comments for an article
      description: Get the comments for an article. Auth is optional
      operationId: GetArticleComments
      parameters:
        - name: slug
          in: path
          description: Slug of the article that you want to get comments for
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/MultipleCommentsResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
    post:
      tags:
        - Comments
      summary: Create a comment for an article
      description: Create a comment for an article. Auth is required
      operationId: CreateArticleComment
      parameters:
        - name: slug
          in: path
          description: Slug of the article that you want to create a comment for
          required: true
          schema:
            type: string
      requestBody:
        $ref: '#/components/requestBodies/NewCommentRequest'
      responses:
        '200':
          $ref: '#/components/responses/SingleCommentResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
      x-codegen-request-body-name: comment
  /articles/{slug}/comments/{id}:
    delete:
      tags:
        - Comments
      summary: Delete a comment for an article
      description: Delete a comment for an article. Auth is required
      operationId: DeleteArticleComment
      parameters:
        - name: slug
          in: path
          description: Slug of the article that you want to delete a comment for
          required: true
          schema:
            type: string
        - name: id
          in: path
          description: ID of the comment you want to delete
          required: true
          schema:
            type: integer
      responses:
        '200':
          $ref: '#/components/responses/EmptyOkResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
  /articles/{slug}/favorite:
    post:
      tags:
        - Favorites
      summary: Favorite an article
      description: Favorite an article. Auth is required
      operationId: CreateArticleFavorite
      parameters:
        - name: slug
          in: path
          description: Slug of the article that you want to favorite
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/SingleArticleResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
    delete:
      tags:
        - Favorites
      summary: Unfavorite an article
      description: Unfavorite an article. Auth is required
      operationId: DeleteArticleFavorite
      parameters:
        - name: slug
          in: path
          description: Slug of the article that you want to unfavorite
          required: true
          schema:
            type: string
      responses:
        '200':
          $ref: '#/components/responses/SingleArticleResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '422':
          $ref: '#/components/responses/GenericError'
      security:
        - Token: [ ]
  /tags:
    get:
      tags:
        - Tags
      summary: Get tags
      description: Get tags. Auth not required
      operationId: GetTags
      responses:
        '200':
          $ref: '#/components/responses/TagsResponse'
        '422':
          $ref: '#/components/responses/GenericError'
components:
  schemas:
    LoginUser:
      required:
        - email
        - password
      type: object
      properties:
        email:
          type: string
        password:
          type: string
          format: password
    NewUser:
      required:
        - email
        - password
        - username
      type: object
      properties:
        username:
          type: string
        email:
          type: string
        password:
          type: string
          format: password
    User:
      required:
        - bio
        - email
        - image
        - token
        - username
      type: object
      properties:
        email:
          type: string
        token:
          type: string
        username:
          type: string
        bio:
          type: string
        image:
          type: string
    UpdateUser:
      type: object
      properties:
        email:
          type: string
        password:
          type: string
        username:
          type: string
        bio:
          type: string
        image:
          type: string
    Profile:
      required:
        - bio
        - following
        - image
        - username
      type: object
      properties:
        username:
          type: string
        bio:
          type: string
        image:
          type: string
        following:
          type: boolean
    Article:
      required:
        - author
        - body
        - createdAt
        - description
        - favorited
        - favoritesCount
        - slug
        - tagList
        - title
        - updatedAt
      type: object
      properties:
        slug:
          type: string
        title:
          type: string
        description:
          type: string
        body:
          type: string
        tagList:
          type: array
          items:
            type: string
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time
        favorited:
          type: boolean
        favoritesCount:
          type: integer
        author:
          $ref: '#/components/schemas/Profile'
    Comment:
      required:
        - author
        - body
        - createdAt
        - id
        - updatedAt
      type: object
      properties:
        id:
          type: integer
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time
        body:
          type: string
        author:
          $ref: '#/components/schemas/Profile'
    TagList:
      required:
        - tags
      type: object
      properties:
        tags:
          type: array
          items:
            type: string
    GenericErrorModel:
      required:
        - errors
      type: object
      properties:
        errors:
          type: object
          additionalProperties:
            type: array
            items:
              type: string
    ArticleInRequest:
      required:
        - body
        - description
        - title
      type: object
      properties:
        title:
          type: string
        description:
          type: string
        body:
          type: string
        tagList:
          type: array
          items:
            type: string
    CommentInRequest:
      required:
        - body
      type: object
      properties:
        body:
          type: string
  requestBodies:
    LoginUserRequest:
      content:
        application/json:
          schema:
            type: object
            required:
              - user
            properties:
              user:
                $ref: '#/components/schemas/LoginUser'
    NewUserRequest:
      content:
        application/json:
          schema:
            type: object
            required:
              - user
            properties:
              user:
                $ref: '#/components/schemas/NewUser'
    UpdateUserRequest:
      content:
        application/json:
          schema:
            type: object
            required:
              - user
            properties:
              user:
                $ref: '#/components/schemas/UpdateUser'
    NewArticleRequest:
      content:
        application/json:
          schema:
            type: object
            required:
              - article
            properties:
              article:
                $ref: '#/components/schemas/ArticleInRequest'
    UpdateArticleRequest:
      content:
        application/json:
          schema:
            type: object
            required:
              - article
            properties:
              article:
                $ref: '#/components/schemas/ArticleInRequest'
    NewCommentRequest:
      content:
        application/json:
          schema:
            type: object
            required:
              - comment
            properties:
              comment:
                $ref: '#/components/schemas/CommentInRequest'
  responses:
    UserResponse:
      description: A user
      content:
        application/json:
          schema:
            type: object
            required:
              - user
            properties:
              user:
                $ref: '#/components/schemas/User'
    ProfileResponse:
      description: A profile
      content:
        application/json:
          schema:
            type: object
            required:
              - profile
            properties:
              profile:
                $ref: '#/components/schemas/Profile'
    MultipleArticlesResponse:
      description: Multiple articles
      content:
        application/json:
          schema:
            type: object
            required:
              - articles
              - articlesCount
            properties:
              articles:
                type: array
                items:
                  $ref: '#/components/schemas/Article'
              articlesCount:
                type: integer
    SingleArticleResponse:
      description: A single article
      content:
        application/json:
          schema:
            type: object
            required:
              - article
            properties:
              article:
                $ref: '#/components/schemas/Article'
    MultipleCommentsResponse:
      description: Multiple comments
      content:
        application/json:
          schema:
            type: object
            required:
              - comments
            properties:
              comments:
                type: array
                items:
                  $ref: '#/components/schemas/Comment'
    SingleCommentResponse:
      description: A single comment
      content:
        application/json:
          schema:
            type: object
            required:
              - comment
            properties:
              comment:
                $ref: '#/components/schemas/Comment'
    TagsResponse:
      description: Tags
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/TagList'
    GenericError:
      description: Generic error model
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/GenericErrorModel'
    EmptyOkResponse:
      description: Empty response
  parameters:
    offsetParam:
      name: offset
      in: query
      description: The number of items to skip before starting to collect the result set.
      required: false
      schema:
        type: integer
        format: int32
        default: 0
    limitParam:
      name: limit
      in: query
      description: The number of items to return.
      required: false
      schema:
        type: integer
        format: int32
        default: 20
securitySchemes:
  Token:
    type: http
    scheme: bearer
    bearerFormat: JWT
"""

REALWORLD_SCHEMA = yaml.safe_load(REALWORLD_SCHEMA_CONTENT)

COMPOSITION_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Composition Test API",
        "version": "1.0.0"
    },
    "components": {
        "schemas": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                }
            },
            "Employee": {
                "allOf": [
                    {"$ref": "#/components/schemas/Person"},
                    {
                        "type": "object",
                        "properties": {
                            "employeeId": {"type": "string"}
                        }
                    }
                ]
            },
            "Student": {
                "anyOf": [
                    {"$ref": "#/components/schemas/Person"},
                    {
                        "type": "object",
                        "properties": {
                            "studentId": {"type": "string"}
                        }
                    }
                ]
            },
            "EitherPersonOrCar": {
                "oneOf": [
                    {"$ref": "#/components/schemas/Person"},
                    {
                        "type": "object",
                        "properties": {
                            "make": {"type": "string"},
                            "model": {"type": "string"}
                        }
                    }
                ]
            },
            "Department": {
                "type": "object",
                "properties": {
                    "manager": {"$ref": "#/components/schemas/Employee"},
                    "staff": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Employee"}
                    }
                }
            }
        }
    }
}

def test_resolve_refs_with_composition():
    """allOf, anyOf, oneOf 内の $ref 解決のテスト"""
    # parse_openapi_schema を使用して $ref を解決
    _, resolved_schema = parse_openapi_schema(schema_content=json.dumps(COMPOSITION_SCHEMA)) # 辞書をJSON文字列に変換して渡す
    analyzer = OpenAPIAnalyzer(resolved_schema)

    # allOf 内の $ref 解決を確認
    employee_schema = resolved_schema["components"]["schemas"]["Employee"]
    assert "allOf" in employee_schema
    assert len(employee_schema["allOf"]) == 2
    assert "$ref" not in employee_schema["allOf"][0]
    assert employee_schema["allOf"][0]["properties"]["name"]["type"] == "string"
    assert "$ref" not in employee_schema["allOf"][1]
    assert employee_schema["allOf"][1]["properties"]["employeeId"]["type"] == "string"

    # anyOf 内の $ref 解決を確認
    student_schema = resolved_schema["components"]["schemas"]["Student"]
    assert "anyOf" in student_schema
    assert len(student_schema["anyOf"]) == 2
    assert "$ref" not in student_schema["anyOf"][0]
    assert student_schema["anyOf"][0]["properties"]["name"]["type"] == "string"
    assert "$ref" not in student_schema["anyOf"][1]
    assert student_schema["anyOf"][1]["properties"]["studentId"]["type"] == "string"

    # oneOf 内の $ref 解決を確認
    either_schema = resolved_schema["components"]["schemas"]["EitherPersonOrCar"]
    assert "oneOf" in either_schema
    assert len(either_schema["oneOf"]) == 2
    assert "$ref" not in either_schema["oneOf"][0]
    assert either_schema["oneOf"][0]["properties"]["name"]["type"] == "string"
    assert "$ref" not in either_schema["oneOf"][1]
    assert either_schema["oneOf"][1]["properties"]["make"]["type"] == "string"

    # ネストされた allOf 内の $ref 解決を確認
    department_schema = resolved_schema["components"]["schemas"]["Department"]
    assert "$ref" not in department_schema["properties"]["manager"]
    assert "allOf" in department_schema["properties"]["manager"]
    assert "$ref" not in department_schema["properties"]["manager"]["allOf"][0]
    assert department_schema["properties"]["manager"]["allOf"][0]["properties"]["name"]["type"] == "string"
    assert "$ref" not in department_schema["properties"]["staff"]["items"]
    assert "allOf" in department_schema["properties"]["staff"]["items"]
    assert "$ref" not in department_schema["properties"]["staff"]["items"]["allOf"][0]
    assert department_schema["properties"]["staff"]["items"]["allOf"][0]["properties"]["name"]["type"] == "string"

CIRCULAR_REFERENCE_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Circular Reference Test API",
        "version": "1.0.0"
    },
    "components": {
        "schemas": {
            "Node": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "next": {"$ref": "#/components/schemas/Node"}
                }
            },
            "LinkedList": {
                "type": "object",
                "properties": {
                    "head": {"$ref": "#/components/schemas/Node"}
                }
            },
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "spouse": {"$ref": "#/components/schemas/Spouse"}
                }
            },
            "Spouse": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "partner": {"$ref": "#/components/schemas/Person"}
                }
            }
        }
    }
}

def test_resolve_refs_with_circular_reference():
    """循環参照のテスト - 循環参照が検出された場合はエラーが投げられることを確認"""
    import pytest
    from app.exceptions import OpenAPIParseException
    
    # 循環参照を含むスキーマの解析時にOpenAPIParseExceptionが投げられることを確認
    with pytest.raises(OpenAPIParseException) as exc_info:
        parse_openapi_schema(schema_content=json.dumps(CIRCULAR_REFERENCE_SCHEMA))
    
    # エラーメッセージに循環参照の情報が含まれていることを確認
    assert "循環参照が検出されました" in str(exc_info.value)
    assert "Node" in str(exc_info.value)
    
    # エラーの詳細情報を確認
    assert exc_info.value.details is not None
    assert "circular_reference_path" in exc_info.value.details
    assert "resolution_path" in exc_info.value.details
