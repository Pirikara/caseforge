"""
ハイブリッド検索機能の統合テスト

フェーズ2で実装されたハイブリッド検索機能の統合テストを行います。
実際のOpenAPIスキーマと依存関係解析を使用してテストします。
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict

from app.services.endpoint_chain_generator import EnhancedEndpointChainGenerator
from app.services.openapi.analyzer import OpenAPIAnalyzer
from app.models import Endpoint


class TestHybridSearchIntegration:
    """ハイブリッド検索機能の統合テスト"""
    
    @pytest.fixture
    def comprehensive_schema(self):
        """包括的なテスト用OpenAPIスキーマ"""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Blog API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "description": "Create a new user account",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["name", "email"],
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string", "format": "email"}
                                        }
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
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "email": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/categories": {
                    "post": {
                        "summary": "Create category",
                        "description": "Create a new article category",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["name"],
                                        "properties": {
                                            "name": {"type": "string"},
                                            "description": {"type": "string"}
                                        }
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
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                                "description": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/articles": {
                    "post": {
                        "summary": "Create article",
                        "description": "Create a new blog article",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["title", "content", "authorId"],
                                        "properties": {
                                            "title": {"type": "string"},
                                            "content": {"type": "string"},
                                            "authorId": {"type": "integer", "description": "ID of the article author"},
                                            "categoryId": {"type": "integer", "description": "ID of the article category"}
                                        }
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
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "title": {"type": "string"},
                                                "content": {"type": "string"},
                                                "authorId": {"type": "integer"},
                                                "categoryId": {"type": "integer"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "/articles/{id}": {
                    "put": {
                        "summary": "Update article",
                        "description": "Update an existing article",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"}
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "content": {"type": "string"},
                                            "authorId": {"type": "integer"},
                                            "categoryId": {"type": "integer"}
                                        }
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
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "title": {"type": "string"},
                                                "content": {"type": "string"},
                                                "authorId": {"type": "integer"},
                                                "categoryId": {"type": "integer"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    @pytest.fixture
    def article_endpoints(self):
        """記事関連のエンドポイント"""
        return [
            Endpoint(
                id=1,
                service_id=1,
                method="POST",
                path="/articles",
                summary="Create article",
                description="Create a new blog article",
                request_body={
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["title", "content", "authorId"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "authorId": {"type": "integer"},
                                    "categoryId": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            ),
            Endpoint(
                id=2,
                service_id=1,
                method="PUT",
                path="/articles/{id}",
                summary="Update article",
                description="Update an existing article",
                request_body={
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "authorId": {"type": "integer"},
                                    "categoryId": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            )
        ]
    
    def test_dependency_detection_integration(self, comprehensive_schema, article_endpoints):
        """依存関係検出の統合テスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=article_endpoints,
            schema=comprehensive_schema
        )
        
        # 依存関係が正しく検出されることを確認
        assert len(generator.dependencies) > 0
        
        # body_reference依存関係が検出されることを確認
        body_ref_deps = [dep for dep in generator.dependencies if dep.get("type") == "body_reference"]
        assert len(body_ref_deps) > 0
        
        # authorId依存関係が検出されることを確認
        author_deps = [dep for dep in body_ref_deps 
                      if dep.get("target", {}).get("field") == "authorId"]
        assert len(author_deps) > 0
        
        # categoryId依存関係が検出されることを確認
        category_deps = [dep for dep in body_ref_deps 
                        if dep.get("target", {}).get("field") == "categoryId"]
        assert len(category_deps) > 0
    
    @patch('app.services.endpoint_chain_generator.VectorDBManagerFactory')
    def test_hybrid_search_with_dependencies(self, mock_vector_factory, comprehensive_schema, article_endpoints):
        """依存関係を含むハイブリッド検索のテスト"""
        # VectorDBManagerのモック設定
        mock_vector_manager = Mock()
        mock_vector_factory.create_default.return_value = mock_vector_manager
        
        # similarity_searchの結果をモック
        mock_docs = [
            Mock(page_content="User creation endpoint", metadata={"source": "users"}),
            Mock(page_content="Category creation endpoint", metadata={"source": "categories"}),
            Mock(page_content="Article management endpoint", metadata={"source": "articles"})
        ]
        mock_vector_manager.similarity_search.return_value = mock_docs
        
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=article_endpoints,
            schema=comprehensive_schema
        )
        
        # POST /articlesエンドポイントでハイブリッド検索を実行
        post_article_endpoint = article_endpoints[0]
        results = generator.hybrid_search(post_article_endpoint)
        
        # 結果の検証
        assert isinstance(results, list)
        assert len(results) > 0
        
        # ベクトル検索結果と依存関係ベース検索結果が統合されていることを確認
        search_types = {result.get("search_type") for result in results}
        assert "semantic" in search_types  # ベクトル検索結果
        
        # 依存関係が検出された場合は構造的検索結果も含まれる
        if generator.dependencies:
            assert "structural" in search_types
    
    def test_dependency_chain_info_comprehensive(self, comprehensive_schema, article_endpoints):
        """包括的な依存関係チェーン情報のテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=article_endpoints,
            schema=comprehensive_schema
        )
        
        # POST /articlesエンドポイントの依存関係チェーン情報を取得
        post_article_endpoint = article_endpoints[0]
        chain_info = generator.get_dependency_chain_info(post_article_endpoint)
        
        # 基本的な構造の確認
        assert "target_endpoint" in chain_info
        assert "dependencies" in chain_info
        assert "execution_order" in chain_info
        assert "confidence_score" in chain_info
        assert "warnings" in chain_info
        
        # ターゲットエンドポイントの確認
        assert chain_info["target_endpoint"] == "POST /articles"
        
        # 依存関係が検出されている場合の詳細確認
        if chain_info["dependencies"]:
            # authorId依存関係の確認
            author_deps = [dep for dep in chain_info["dependencies"] 
                          if dep.get("target", {}).get("field") == "authorId"]
            if author_deps:
                author_dep = author_deps[0]
                assert author_dep["type"] == "body_reference"
                assert author_dep["source"]["path"] == "/users"
                assert author_dep["source"]["method"] == "post"
                assert author_dep["strength"] == "required"
                assert author_dep["confidence"] > 0.5
            
            # 実行順序の確認
            execution_order = chain_info["execution_order"]
            assert len(execution_order) >= 2  # 最低でもセットアップ + ターゲット
            
            # 最後のステップがターゲットエンドポイントであることを確認
            last_step = execution_order[-1]
            assert last_step["endpoint"] == "POST /articles"
            assert last_step["purpose"] == "Target endpoint execution"
            assert last_step["required"] is True
    
    def test_enhanced_embeddings_with_dependencies(self, comprehensive_schema, article_endpoints):
        """依存関係を含む拡張埋め込みのテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=article_endpoints,
            schema=comprehensive_schema
        )
        
        post_article_endpoint = article_endpoints[0]
        embedding_text = generator.generate_enhanced_embeddings(post_article_endpoint)
        
        # 基本的なエンドポイント情報が含まれることを確認
        assert "POST /articles" in embedding_text
        assert "Create article" in embedding_text
        
        # IDフィールド情報が含まれることを確認
        assert "ID Field: authorId" in embedding_text or "authorId" in embedding_text
        
        # リソース情報が含まれることを確認
        assert "Resource: articles" in embedding_text
        
        # 依存関係情報が含まれることを確認（依存関係が検出された場合）
        if generator.dependencies:
            dependency_related_content = any([
                "Dependency:" in embedding_text,
                "Depends on:" in embedding_text,
                "Required Field:" in embedding_text
            ])
            assert dependency_related_content
    
    @patch('app.services.endpoint_chain_generator.VectorDBManagerFactory')
    def test_search_quality_metrics_comprehensive(self, mock_vector_factory, comprehensive_schema, article_endpoints):
        """包括的な検索品質メトリクスのテスト"""
        # VectorDBManagerのモック設定
        mock_vector_manager = Mock()
        mock_vector_factory.create_default.return_value = mock_vector_manager
        
        # similarity_searchの結果をモック
        mock_docs = [
            Mock(page_content="User endpoint", metadata={"source": "users"}),
            Mock(page_content="Category endpoint", metadata={"source": "categories"})
        ]
        mock_vector_manager.similarity_search.return_value = mock_docs
        
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=article_endpoints,
            schema=comprehensive_schema
        )
        
        post_article_endpoint = article_endpoints[0]
        metrics = generator.get_search_quality_metrics(post_article_endpoint)
        
        # メトリクスの基本構造確認
        expected_keys = [
            "endpoint", "vector_search_results", "dependency_search_results",
            "hybrid_search_results", "dependency_coverage", "confidence_score",
            "search_effectiveness"
        ]
        for key in expected_keys:
            assert key in metrics
        
        # エンドポイント情報の確認
        assert metrics["endpoint"] == "POST /articles"
        
        # 検索結果数の確認
        assert metrics["vector_search_results"] >= 0
        assert metrics["dependency_search_results"] >= 0
        assert metrics["hybrid_search_results"] >= 0
        
        # 依存関係が検出された場合のメトリクス確認
        if generator.dependencies:
            assert metrics["dependency_coverage"] >= 0.0
            assert metrics["dependency_coverage"] <= 1.0
            assert metrics["confidence_score"] >= 0.0
            assert metrics["confidence_score"] <= 1.0
        
        # 検索効果の評価
        assert metrics["search_effectiveness"] in ["improved", "equivalent", "degraded", "error"]
    
    def test_dependency_aware_context_building(self, comprehensive_schema, article_endpoints):
        """依存関係対応コンテキスト構築の統合テスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=article_endpoints,
            schema=comprehensive_schema
        )
        
        post_article_endpoint = article_endpoints[0]
        
        # 依存関係対応コンテキストの構築
        context = generator._build_dependency_aware_context(
            post_article_endpoint,
            "Test endpoint info",
            "Test schema info",
            "Test error types"
        )
        
        # コンテキストの基本構造確認
        expected_keys = [
            "dependency_graph", "target_endpoint", "relevant_schema_info",
            "execution_order", "error_types_instruction"
        ]
        for key in expected_keys:
            assert key in context
        
        # 依存関係グラフの確認
        dependency_graph = context["dependency_graph"]
        if generator.dependencies:
            assert "Dependency Graph:" in dependency_graph
            assert "POST /users" in dependency_graph or "POST /categories" in dependency_graph
        else:
            assert "No dependencies detected" in dependency_graph
        
        # ターゲットエンドポイント情報の確認
        target_endpoint = context["target_endpoint"]
        assert "POST /articles" in target_endpoint
        assert "Create article" in target_endpoint
        
        # 実行順序の確認
        execution_order = context["execution_order"]
        assert "POST /articles" in execution_order
        if generator.dependencies:
            # 依存関係がある場合は複数のステップが含まれる
            assert "1." in execution_order
            assert "Target endpoint execution" in execution_order


class TestHybridSearchPerformance:
    """ハイブリッド検索のパフォーマンステスト"""
    
    @patch('app.services.endpoint_chain_generator.VectorDBManagerFactory')
    def test_hybrid_search_performance(self, mock_vector_factory):
        """ハイブリッド検索のパフォーマンステスト"""
        # 大量のモックデータを設定
        mock_vector_manager = Mock()
        mock_vector_factory.create_default.return_value = mock_vector_manager
        
        # 大量のベクトル検索結果をモック
        mock_docs = [
            Mock(page_content=f"Content {i}", metadata={"source": f"source_{i}"})
            for i in range(100)
        ]
        mock_vector_manager.similarity_search.return_value = mock_docs[:5]  # 最大5件に制限
        
        # 大量のエンドポイントを含むスキーマ
        large_schema = {
            "paths": {
                f"/resource_{i}": {
                    "post": {
                        "summary": f"Create resource {i}",
                        "responses": {"201": {"content": {"application/json": {"schema": {"properties": {"id": {"type": "integer"}}}}}}}
                    }
                } for i in range(50)
            }
        }
        
        endpoints = [
            Endpoint(
                id=1,
                service_id=1,
                method="POST",
                path="/articles",
                summary="Create article",
                request_body={
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "authorId": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            )
        ]
        
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=endpoints,
            schema=large_schema
        )
        
        import time
        start_time = time.time()
        
        # ハイブリッド検索の実行
        results = generator.hybrid_search(endpoints[0])
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # パフォーマンス要件の確認（2秒以内）
        assert execution_time < 2.0, f"Hybrid search took too long: {execution_time:.2f} seconds"
        
        # 結果の制限が適用されていることを確認
        assert len(results) <= generator.max_results
        
        # 結果の品質確認
        assert isinstance(results, list)
        for result in results:
            assert "source" in result
            assert "score" in result
            assert "content" in result
            assert "search_type" in result
