"""
リクエストボディ内のIDフィールドによる依存関係解析の統合テスト
"""

import pytest
from app.services.openapi.analyzer import OpenAPIAnalyzer


# 実際のブログAPIスキーマ例
BLOG_API_SCHEMA = {
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
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CreateUserRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "User created successfully",
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
        "/categories": {
            "post": {
                "summary": "Create a category",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CreateCategoryRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Category created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Category"
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
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CreateArticleRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Article created successfully",
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
                            "type": "string",
                            "format": "uuid"
                        }
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/UpdateArticleRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Article updated successfully",
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
        "/comments": {
            "post": {
                "summary": "Create a comment",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CreateCommentRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Comment created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Comment"
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
                    "id": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "name": {
                        "type": "string"
                    },
                    "email": {
                        "type": "string",
                        "format": "email"
                    }
                }
            },
            "CreateUserRequest": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "email": {
                        "type": "string",
                        "format": "email"
                    }
                },
                "required": ["name", "email"]
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "name": {
                        "type": "string"
                    },
                    "description": {
                        "type": "string"
                    }
                }
            },
            "CreateCategoryRequest": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "description": {
                        "type": "string"
                    }
                },
                "required": ["name"]
            },
            "Article": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "title": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string"
                    },
                    "authorId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "User identifier who created this article"
                    },
                    "categoryId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Category identifier for this article"
                    }
                }
            },
            "CreateArticleRequest": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string"
                    },
                    "authorId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "User identifier who created this article"
                    },
                    "categoryId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Category identifier for this article"
                    }
                },
                "required": ["title", "content", "authorId"]
            },
            "UpdateArticleRequest": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string"
                    },
                    "content": {
                        "type": "string"
                    },
                    "categoryId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Category identifier for this article"
                    }
                }
            },
            "Comment": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "content": {
                        "type": "string"
                    },
                    "authorId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "User identifier who created this comment"
                    },
                    "articleId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Article identifier this comment belongs to"
                    }
                }
            },
            "CreateCommentRequest": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string"
                    },
                    "authorId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "User identifier who created this comment"
                    },
                    "articleId": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Article identifier this comment belongs to"
                    }
                },
                "required": ["content", "authorId", "articleId"]
            }
        }
    }
}


def test_complex_dependency_analysis():
    """複雑な依存関係の解析テスト"""
    analyzer = OpenAPIAnalyzer(BLOG_API_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    # body_reference 依存関係が検出されることを確認
    body_ref_deps = [dep for dep in dependencies if dep["type"] == "body_reference"]
    assert len(body_ref_deps) > 0, "body_reference 依存関係が検出されませんでした"
    
    # 期待される依存関係をチェック
    expected_dependencies = [
        # POST /articles は POST /users に依存（authorId）
        {
            "source_path": "/users",
            "source_method": "post",
            "target_path": "/articles",
            "target_method": "post",
            "field": "authorId"
        },
        # POST /articles は POST /categories に依存（categoryId）
        {
            "source_path": "/categories",
            "source_method": "post",
            "target_path": "/articles",
            "target_method": "post",
            "field": "categoryId"
        },
        # POST /comments は POST /users に依存（authorId）
        {
            "source_path": "/users",
            "source_method": "post",
            "target_path": "/comments",
            "target_method": "post",
            "field": "authorId"
        },
        # POST /comments は POST /articles に依存（articleId）
        {
            "source_path": "/articles",
            "source_method": "post",
            "target_path": "/comments",
            "target_method": "post",
            "field": "articleId"
        }
    ]
    
    for expected in expected_dependencies:
        found = False
        for dep in body_ref_deps:
            if (dep["source"]["path"] == expected["source_path"] and
                dep["source"]["method"] == expected["source_method"] and
                dep["target"]["path"] == expected["target_path"] and
                dep["target"]["method"] == expected["target_method"] and
                dep["target"]["field"] == expected["field"]):
                found = True
                break
        
        assert found, f"期待される依存関係が見つかりません: {expected}"


def test_dependency_strength_analysis():
    """依存関係の強度解析テスト"""
    analyzer = OpenAPIAnalyzer(BLOG_API_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    body_ref_deps = [dep for dep in dependencies if dep["type"] == "body_reference"]
    
    # authorId は必須フィールドなので required
    author_deps = [dep for dep in body_ref_deps if dep["target"]["field"] == "authorId"]
    for dep in author_deps:
        if dep["target"]["path"] == "/articles" and dep["target"]["method"] == "post":
            assert dep["strength"] == "required", "authorId の依存関係強度が正しくありません"
    
    # categoryId は POST /articles では任意フィールド（required に含まれていない）
    category_deps = [dep for dep in body_ref_deps if dep["target"]["field"] == "categoryId"]
    for dep in category_deps:
        if dep["target"]["path"] == "/articles" and dep["target"]["method"] == "put":
            assert dep["strength"] == "optional", "categoryId の依存関係強度が正しくありません"


def test_confidence_scoring():
    """信頼度スコアリングテスト"""
    analyzer = OpenAPIAnalyzer(BLOG_API_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    body_ref_deps = [dep for dep in dependencies if dep["type"] == "body_reference"]
    
    # 高信頼度の依存関係（既知のリソース名 + UUID形式 + 説明文）
    high_confidence_deps = [
        dep for dep in body_ref_deps 
        if dep["target"]["field"] in ["authorId", "categoryId", "articleId"]
    ]
    
    for dep in high_confidence_deps:
        assert dep["confidence"] > 0.8, f"高信頼度依存関係の信頼度が低すぎます: {dep['confidence']}"


def test_all_dependency_types_integration():
    """全依存関係タイプの統合テスト"""
    analyzer = OpenAPIAnalyzer(BLOG_API_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    dependency_types = set(dep["type"] for dep in dependencies)
    
    # 全ての依存関係タイプが含まれることを確認
    expected_types = ["path_parameter", "resource_operation", "schema_reference", "body_reference"]
    for expected_type in expected_types:
        assert expected_type in dependency_types, f"{expected_type} 依存関係が見つかりません"
    
    # 各タイプの依存関係が適切に検出されることを確認
    path_param_deps = [dep for dep in dependencies if dep["type"] == "path_parameter"]
    resource_op_deps = [dep for dep in dependencies if dep["type"] == "resource_operation"]
    schema_ref_deps = [dep for dep in dependencies if dep["type"] == "schema_reference"]
    body_ref_deps = [dep for dep in dependencies if dep["type"] == "body_reference"]
    
    assert len(path_param_deps) > 0, "パスパラメータ依存関係が検出されませんでした"
    assert len(resource_op_deps) > 0, "リソース操作依存関係が検出されませんでした"
    assert len(schema_ref_deps) > 0, "スキーマ参照依存関係が検出されませんでした"
    assert len(body_ref_deps) > 0, "ボディ参照依存関係が検出されませんでした"


def test_dependency_chain_detection():
    """依存関係チェーンの検出テスト"""
    analyzer = OpenAPIAnalyzer(BLOG_API_SCHEMA)
    dependencies = analyzer.extract_dependencies()
    
    # 依存関係チェーンの例:
    # POST /users → POST /articles → POST /comments
    # POST /categories → POST /articles
    
    body_ref_deps = [dep for dep in dependencies if dep["type"] == "body_reference"]
    
    # POST /users → POST /articles の依存関係
    users_to_articles = any(
        dep["source"]["path"] == "/users" and
        dep["source"]["method"] == "post" and
        dep["target"]["path"] == "/articles" and
        dep["target"]["method"] == "post"
        for dep in body_ref_deps
    )
    
    # POST /articles → POST /comments の依存関係
    articles_to_comments = any(
        dep["source"]["path"] == "/articles" and
        dep["source"]["method"] == "post" and
        dep["target"]["path"] == "/comments" and
        dep["target"]["method"] == "post"
        for dep in body_ref_deps
    )
    
    assert users_to_articles, "POST /users → POST /articles の依存関係が検出されませんでした"
    assert articles_to_comments, "POST /articles → POST /comments の依存関係が検出されませんでした"
