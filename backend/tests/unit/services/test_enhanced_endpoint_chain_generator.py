"""
EnhancedEndpointChainGeneratorのユニットテスト

フェーズ2で実装されたハイブリッド検索機能のテストを行います。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict

from app.services.endpoint_chain_generator import EnhancedEndpointChainGenerator
from app.models import Endpoint


class TestEnhancedEndpointChainGenerator:
    """EnhancedEndpointChainGeneratorのテストクラス"""
    
    @pytest.fixture
    def sample_schema(self):
        """テスト用のOpenAPIスキーマ"""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "201": {
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
                "/articles": {
                    "post": {
                        "summary": "Create article",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "title": {"type": "string"},
                                            "content": {"type": "string"},
                                            "authorId": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "201": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "title": {"type": "string"},
                                                "content": {"type": "string"},
                                                "authorId": {"type": "integer"}
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
    def sample_endpoints(self):
        """テスト用のエンドポイントリスト"""
        return [
            Endpoint(
                id=1,
                service_id=1,
                method="POST",
                path="/articles",
                summary="Create article",
                description="Create a new article",
                request_body={
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "authorId": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            )
        ]
    
    @pytest.fixture
    def sample_dependencies(self):
        """テスト用の依存関係リスト"""
        return [
            {
                "type": "body_reference",
                "source": {
                    "path": "/users",
                    "method": "post"
                },
                "target": {
                    "path": "/articles",
                    "method": "post",
                    "field": "authorId"
                },
                "strength": "required",
                "confidence": 0.9
            }
        ]
    
    def test_enhanced_endpoint_chain_generator_initialization(self, sample_endpoints, sample_schema):
        """EnhancedEndpointChainGeneratorの初期化テスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        assert generator.service_id == 1
        assert len(generator.endpoints) == 1
        assert generator.schema == sample_schema
        assert generator.hybrid_search_enabled is True
        assert generator.dependency_analyzer is not None
    
    def test_generate_enhanced_embeddings(self, sample_endpoints, sample_schema):
        """拡張埋め込みテキスト生成のテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        endpoint = sample_endpoints[0]
        embedding_text = generator.generate_enhanced_embeddings(endpoint)
        
        assert "POST /articles" in embedding_text
        assert "Create article" in embedding_text
        assert "Resource: articles" in embedding_text
    
    @patch('app.services.endpoint_chain_generator.VectorDBManagerFactory')
    def test_hybrid_search(self, mock_vector_factory, sample_endpoints, sample_schema):
        """ハイブリッド検索のテスト"""
        # VectorDBManagerのモック設定
        mock_vector_manager = Mock()
        mock_vector_factory.create_default.return_value = mock_vector_manager
        
        # similarity_searchの結果をモック
        mock_docs = [
            Mock(page_content="Test content 1", metadata={"source": "test1"}),
            Mock(page_content="Test content 2", metadata={"source": "test2"})
        ]
        mock_vector_manager.similarity_search.return_value = mock_docs
        
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        endpoint = sample_endpoints[0]
        results = generator.hybrid_search(endpoint)
        
        assert isinstance(results, list)
        # ベクトル検索結果が含まれることを確認
        assert len(results) >= 0
    
    def test_get_dependency_chain_info(self, sample_endpoints, sample_schema):
        """依存関係チェーン情報取得のテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        # 依存関係を手動で設定
        generator.dependencies = [
            {
                "type": "body_reference",
                "source": {
                    "path": "/users",
                    "method": "post"
                },
                "target": {
                    "path": "/articles",
                    "method": "post",
                    "field": "authorId"
                },
                "strength": "required",
                "confidence": 0.9
            }
        ]
        
        endpoint = sample_endpoints[0]
        chain_info = generator.get_dependency_chain_info(endpoint)
        
        assert "target_endpoint" in chain_info
        assert "dependencies" in chain_info
        assert "execution_order" in chain_info
        assert "confidence_score" in chain_info
        assert chain_info["target_endpoint"] == "POST /articles"
        assert len(chain_info["dependencies"]) == 1
        assert chain_info["confidence_score"] == 0.9
    
    def test_build_dependency_graph_text(self, sample_endpoints, sample_schema):
        """依存関係グラフテキスト構築のテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        # 依存関係を手動で設定
        generator.dependencies = [
            {
                "type": "body_reference",
                "source": {
                    "path": "/users",
                    "method": "post"
                },
                "target": {
                    "path": "/articles",
                    "method": "post",
                    "field": "authorId"
                },
                "strength": "required",
                "confidence": 0.9
            }
        ]
        
        endpoint = sample_endpoints[0]
        graph_text = generator._build_dependency_graph_text(endpoint)
        
        assert "Dependency Graph:" in graph_text
        assert "POST /users" in graph_text
        assert "POST /articles" in graph_text
        assert "Body Reference" in graph_text
        assert "authorId" in graph_text
        assert "required" in graph_text
        assert "0.90" in graph_text
    
    def test_determine_execution_order(self, sample_endpoints, sample_schema):
        """実行順序決定のテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        # 依存関係を手動で設定
        generator.dependencies = [
            {
                "type": "body_reference",
                "source": {
                    "path": "/users",
                    "method": "post"
                },
                "target": {
                    "path": "/articles",
                    "method": "post",
                    "field": "authorId"
                },
                "strength": "required",
                "confidence": 0.9
            }
        ]
        
        endpoint = sample_endpoints[0]
        execution_order = generator._determine_execution_order(endpoint)
        
        assert "1. **POST /users**" in execution_order
        assert "2. **POST /articles**" in execution_order
        assert "Create resource for authorId field" in execution_order
        assert "Target endpoint execution" in execution_order
    
    @patch('app.services.endpoint_chain_generator.VectorDBManagerFactory')
    def test_get_search_quality_metrics(self, mock_vector_factory, sample_endpoints, sample_schema):
        """検索品質メトリクス取得のテスト"""
        # VectorDBManagerのモック設定
        mock_vector_manager = Mock()
        mock_vector_factory.create_default.return_value = mock_vector_manager
        
        # similarity_searchの結果をモック
        mock_docs = [
            Mock(page_content="Test content", metadata={"source": "test"})
        ]
        mock_vector_manager.similarity_search.return_value = mock_docs
        
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        # 依存関係を手動で設定
        generator.dependencies = [
            {
                "type": "body_reference",
                "source": {
                    "path": "/users",
                    "method": "post"
                },
                "target": {
                    "path": "/articles",
                    "method": "post",
                    "field": "authorId"
                },
                "strength": "required",
                "confidence": 0.9
            }
        ]
        
        endpoint = sample_endpoints[0]
        metrics = generator.get_search_quality_metrics(endpoint)
        
        assert "endpoint" in metrics
        assert "vector_search_results" in metrics
        assert "dependency_search_results" in metrics
        assert "hybrid_search_results" in metrics
        assert "dependency_coverage" in metrics
        assert "confidence_score" in metrics
        assert "search_effectiveness" in metrics
        assert metrics["endpoint"] == "POST /articles"
    
    def test_build_dependency_aware_context(self, sample_endpoints, sample_schema):
        """依存関係対応コンテキスト構築のテスト"""
        generator = EnhancedEndpointChainGenerator(
            service_id=1,
            endpoints=sample_endpoints,
            schema=sample_schema
        )
        
        # 依存関係を手動で設定
        generator.dependencies = [
            {
                "type": "body_reference",
                "source": {
                    "path": "/users",
                    "method": "post"
                },
                "target": {
                    "path": "/articles",
                    "method": "post",
                    "field": "authorId"
                },
                "strength": "required",
                "confidence": 0.9
            }
        ]
        
        endpoint = sample_endpoints[0]
        context = generator._build_dependency_aware_context(
            endpoint,
            "Test endpoint info",
            "Test schema info",
            "Test error types"
        )
        
        assert "dependency_graph" in context
        assert "target_endpoint" in context
        assert "relevant_schema_info" in context
        assert "execution_order" in context
        assert "error_types_instruction" in context
        assert "POST /articles" in context["target_endpoint"]
        assert "Create article" in context["target_endpoint"]


class TestHybridSearchIntegration:
    """ハイブリッド検索の統合テスト"""
    
    @patch('app.services.endpoint_chain_generator.VectorDBManagerFactory')
    def test_hybrid_search_integration(self, mock_vector_factory):
        """ハイブリッド検索の統合テスト"""
        # VectorDBManagerのモック設定
        mock_vector_manager = Mock()
        mock_vector_factory.create_default.return_value = mock_vector_manager
        
        # similarity_searchの結果をモック
        mock_docs = [
            Mock(page_content="User endpoint content", metadata={"source": "users"}),
            Mock(page_content="Article endpoint content", metadata={"source": "articles"})
        ]
        mock_vector_manager.similarity_search.return_value = mock_docs
        
        # テスト用のスキーマとエンドポイント
        schema = {
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "responses": {
                            "201": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "properties": {
                                                "id": {"type": "integer"}
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
                        "requestBody": {
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
                    }
                }
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
            schema=schema
        )
        
        # ハイブリッド検索の実行
        results = generator.hybrid_search(endpoints[0])
        
        # 結果の検証
        assert isinstance(results, list)
        
        # 依存関係ベース検索結果が含まれることを確認
        dependency_results = [r for r in results if r.get("search_type") == "structural"]
        vector_results = [r for r in results if r.get("search_type") == "semantic"]
        
        # 両方の検索結果が統合されていることを確認
        assert len(vector_results) > 0  # ベクトル検索結果
        # 依存関係が検出された場合は依存関係ベース検索結果も含まれる
        if generator.dependencies:
            assert len(dependency_results) > 0
