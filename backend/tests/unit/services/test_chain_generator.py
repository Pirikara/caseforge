import pytest
from app.services.chain_generator import DependencyAwareRAG, ChainStore
from unittest.mock import MagicMock
import json

from app.models import TestCase

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
                        "description": "List of users"
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
                        "description": "User details"
                    }
                }
            }
        }
    }
}

SAMPLE_TEST_SUITE = {
    "name": "ユーザー作成と取得",
    "target_method": "POST",
    "target_path": "/users",
    "test_cases": [
        {
            "name": "正常系",
            "description": "正常なユーザー作成と取得",
            "error_type": None,
            "test_steps": [
                {
                    "sequence": 0,
                    "method": "POST",
                    "path": "/users",
                    "request_body": {"name": "Test User", "email": "test@example.com"},
                    "extract_rules": {"user_id": "$.id"},
                    "expected_status": 201
                },
                {
                    "sequence": 1,
                    "method": "GET",
                    "path": "/users/{user_id}",
                    "request_params": {"user_id": "{user_id}"}, # 抽出した値を使用
                    "expected_status": 200
                }
            ]
        },
        {
            "name": "必須フィールド欠落",
            "description": "emailフィールドがない場合",
            "error_type": "missing_field",
            "test_steps": [
                {
                    "sequence": 0,
                    "method": "POST",
                    "path": "/users",
                    "request_body": {"name": "Test User"},
                    "expected_status": 400
                }
            ]
        }
    ]
}

def test_build_dependency_graph(monkeypatch):
    """依存関係グラフ構築のテスト"""
    mock_analyzer = MagicMock()
    mock_analyzer.extract_dependencies.return_value = [
        {
            "type": "path_parameter",
            "source": {"path": "/users", "method": "post"},
            "target": {"path": "/users/{id}", "method": "get", "parameter": "id"}
        }
    ]
    monkeypatch.setattr("app.services.schema_analyzer.OpenAPIAnalyzer", lambda schema: mock_analyzer)
    
    rag = DependencyAwareRAG("test_service", SAMPLE_SCHEMA)
    graph = rag._build_dependency_graph()
    
    assert "POST /users" in graph
    assert "GET /users/{id}" in graph
    assert "GET /users/{id}" in graph["POST /users"]["dependents"]
    assert "POST /users" in graph["GET /users/{id}"]["dependencies"]

def test_identify_chain_candidates():
    """チェーン候補特定のテスト"""
    mock_graph = {
        "POST /users": {
            "path": "/users",
            "method": "post",
            "dependencies": [],
            "dependents": ["GET /users/{id}"]
        },
        "GET /users/{id}": {
            "path": "/users/{id}",
            "method": "get",
            "dependencies": ["POST /users"],
            "dependents": []
        }
    }
    
    rag = DependencyAwareRAG("test_service", SAMPLE_SCHEMA)
    rag._build_dependency_graph = lambda: mock_graph
    
    candidates = rag._identify_chain_candidates(mock_graph)
    
    assert len(candidates) > 0
    assert ["POST /users", "GET /users/{id}"] in candidates

def test_generate_test_suite_for_candidate(monkeypatch):
    """テストスイート生成のテスト"""
    class MockResponse:
        content = json.dumps(SAMPLE_TEST_SUITE)
    
    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value = MockResponse()
    monkeypatch.setattr("langchain_openai.ChatOpenAI", lambda **kwargs: mock_llm_instance)
    
    rag = DependencyAwareRAG("test_service", SAMPLE_SCHEMA)
    test_suite = rag._generate_chain_for_candidate(["POST /users", "GET /users/{id}"])
    
    assert test_suite is not None
    assert test_suite["name"] == SAMPLE_TEST_SUITE["name"]
    assert test_suite["target_method"] == SAMPLE_TEST_SUITE["target_method"]
    assert test_suite["target_path"] == SAMPLE_TEST_SUITE["target_path"]
    assert len(test_suite["test_cases"]) == len(SAMPLE_TEST_SUITE["test_cases"])
    assert test_suite["test_cases"][0]["name"] == SAMPLE_TEST_SUITE["test_cases"][0]["name"]
    assert len(test_suite["test_cases"][0]["test_steps"]) == len(SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"])
    assert test_suite["test_cases"][1]["error_type"] == SAMPLE_TEST_SUITE["test_cases"][1]["error_type"]

def test_generate_test_suites(mock_llm, monkeypatch):
    """テストスイート生成のテスト"""
    mock_graph = {
        "POST /users": {
            "path": "/users",
            "method": "post",
            "dependencies": [],
            "dependents": ["GET /users/{id}"]
        },
        "GET /users/{id}": {
            "path": "/users/{id}",
            "method": "get",
            "dependencies": ["POST /users"],
            "dependents": []
        }
    }
    
    mock_candidates = [["POST /users", "GET /users/{id}"]]
    
    mock_test_suite = SAMPLE_TEST_SUITE
    
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._build_dependency_graph", lambda self: mock_graph)
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._identify_chain_candidates", lambda self, graph: mock_candidates)
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._generate_chain_for_candidate", lambda self, candidate: mock_test_suite)
    
    rag = DependencyAwareRAG("test_service", SAMPLE_SCHEMA)
    test_suites = rag.generate_request_chains()
    
    assert len(test_suites) == 1
    assert test_suites[0]["name"] == SAMPLE_TEST_SUITE["name"]
    assert len(test_suites[0]["test_cases"]) == len(SAMPLE_TEST_SUITE["test_cases"])
    assert len(test_suites[0]["test_cases"][0]["test_steps"]) == len(SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"])

def test_chain_store_save_test_suites(session, test_service, monkeypatch):
    """テストスイート保存のテスト"""
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
    
    mock_open = MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)
    
    chain_store = ChainStore()
    chain_store.save_suites(session, test_service.id, [SAMPLE_TEST_SUITE])
    
    from app.models import TestSuite, TestStep
    from sqlmodel import select

    test_suites = session.exec(select(TestSuite).where(TestSuite.service_id == test_service.id)).all()
    assert len(test_suites) == 1
    assert test_suites[0].name == SAMPLE_TEST_SUITE["name"]
    assert test_suites[0].target_method == SAMPLE_TEST_SUITE["target_method"]
    assert test_suites[0].target_path == SAMPLE_TEST_SUITE["target_path"]

    test_cases = session.exec(select(TestCase).where(TestCase.suite_id == test_suites[0].id)).all()
    assert len(test_cases) == len(SAMPLE_TEST_SUITE["test_cases"])
    assert test_cases[0].name == SAMPLE_TEST_SUITE["test_cases"][0]["name"]
    assert test_cases[1].error_type == SAMPLE_TEST_SUITE["test_cases"][1]["error_type"]

    test_steps_case1 = session.exec(select(TestStep).where(TestStep.case_id == test_cases[0].id)).all()
    assert len(test_steps_case1) == len(SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"])
    assert test_steps_case1[0].method == SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"][0]["method"]

    test_steps_case2 = session.exec(select(TestStep).where(TestStep.case_id == test_cases[1].id)).all()
    assert len(test_steps_case2) == len(SAMPLE_TEST_SUITE["test_cases"][1]["test_steps"])
    assert test_steps_case2[0].method == SAMPLE_TEST_SUITE["test_cases"][1]["test_steps"][0]["method"]

    from app.models import TestSuite
    from sqlmodel import select
    
    from app.models import TestSuite
    from sqlmodel import select

    saved_test_suites = session.exec(select(TestSuite).where(TestSuite.service_id == test_service.id)).all()
    for suite in saved_test_suites:
        session.delete(suite)
    session.commit()

def test_chain_store_list_test_suites(session, test_service):
    """テストスイート一覧取得のテスト"""
    from app.models import TestSuite
    
    test_suite = TestSuite(
        id="test-suite-1",
        service_id=test_service.id,
        name="Test TestSuite",
        target_method="GET",
        target_path="/items"
    )
    session.add(test_suite)
    session.flush()

    test_case = TestCase(
        id="test-case-1",
        suite_id=test_suite.id,
        name="Normal Case"
    )
    session.add(test_case)
    session.commit()
    
    chain_store = ChainStore()
    test_suites = chain_store.list_test_suites(session, test_service.id)
    print("test_suites : ", test_suites)
    
    filtered_suites = [suite for suite in test_suites if suite["service_id"] == test_service.id]
    print(filtered_suites)

    assert len(filtered_suites) == 1
    assert filtered_suites[0]["id"] == "test-suite-1"
    assert filtered_suites[0]["service_id"] == test_service.id
    assert filtered_suites[0]["name"] == "Test TestSuite"
    assert filtered_suites[0]["target_method"] == "GET"
    assert filtered_suites[0]["target_path"] == "/items"
    assert filtered_suites[0]["test_cases_count"] == 1

def test_chain_store_get_test_suite(session, test_service):
    """特定のテストスイート取得のテスト"""
    from app.models import TestSuite, TestStep

    test_suite = TestSuite(
        id="test-suite-1",
        service_id=test_service.id,
        name="POST /users TestSuite",
        target_method="POST",
        target_path="/users"
    )
    session.add(test_suite)
    session.flush()

    test_case = TestCase(
        id="test-case-1",
        suite_id=test_suite.id,
        name="Normal Case",
        description="Normal user creation",
        error_type=None
    )
    session.add(test_case)
    session.flush()

    step1 = TestStep(
        id="test-step-1",
        case_id=test_case.id,
        sequence=0,
        method="POST",
        path="/users",
        request_body={"name": "Test User"},
        expected_status=201
    )
    step2 = TestStep(
        id="test-step-2",
        case_id=test_case.id,
        sequence=1,
        method="GET",
        path="/users/{id}",
        extract_rules={"user_id": "$.id"},
        expected_status=200
    )
    session.add(step1)
    session.add(step2)
    session.commit()
    
    chain_store = ChainStore()
    test_suite_data = chain_store.get_test_suite(session, test_service.id, "test-suite-1")

    assert test_suite_data is not None
    assert test_suite_data["id"] == "test-suite-1"
    assert test_suite_data["name"] == "POST /users TestSuite"
    assert test_suite_data["target_method"] == "POST"
    assert test_suite_data["target_path"] == "/users"
    assert len(test_suite_data["test_cases"]) == 1
    assert test_suite_data["test_cases"][0]["id"] == "test-case-1"
    assert test_suite_data["test_cases"][0]["name"] == "Normal Case"
    assert len(test_suite_data["test_cases"][0]["test_steps"]) == 2
    assert test_suite_data["test_cases"][0]["test_steps"][0]["method"] == "POST"
    assert test_suite_data["test_cases"][0]["test_steps"][1]["method"] == "GET"

def test_dependency_aware_rag_error_handling(monkeypatch):
    """DependencyAwareRAGのエラーハンドリングテスト"""
    mock_analyzer = MagicMock()
    mock_analyzer.extract_dependencies.side_effect = Exception("Dependency extraction error")
    monkeypatch.setattr("app.services.schema_analyzer.OpenAPIAnalyzer", lambda schema: mock_analyzer)
    
    rag = DependencyAwareRAG("test_service", SAMPLE_SCHEMA)
    
    assert hasattr(rag, "analyzer")

def test_dependency_aware_rag_generate_chain_for_candidate_error(monkeypatch):
    """_generate_chain_for_candidateのエラーハンドリングテスト"""
    def mock_build_context_error(self, candidate):
        raise Exception("Context building error")
    
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._build_context_for_candidate", mock_build_context_error)
    
    rag = DependencyAwareRAG("test_service", SAMPLE_SCHEMA)
    result = rag._generate_chain_for_candidate(["POST /users"])
    
    import os
    os.environ["TESTING"] = "1"
    
    assert result is not None
    assert "name" in result

def test_chain_store_list_test_suites_error(session, test_service, monkeypatch):
    """ChainStore.list_test_suitesのエラーハンドリングテスト"""
    def mock_select_error(*args, **kwargs):
        raise Exception("Database query error")
    
    monkeypatch.setattr("app.services.chain_generator.select", mock_select_error)
    
    chain_store = ChainStore()
    result = chain_store.list_test_suites(session, test_service.id)
    
    assert result == []

def test_chain_store_get_test_suite_error(session, test_service, monkeypatch):
    """ChainStore.get_test_suiteのエラーハンドリングテスト"""
    def mock_select_error(*args, **kwargs):
        raise Exception("Database query error")
    
    monkeypatch.setattr("app.services.chain_generator.select", mock_select_error)
    
    chain_store = ChainStore()
    result = chain_store.get_test_suite(session, test_service.id, "test-suite-1")
    
    assert result is None

def test_dependency_aware_rag_with_error_types(monkeypatch):
    """エラータイプを指定したDependencyAwareRAGのテスト"""
    mock_analyzer = MagicMock()
    mock_analyzer.extract_dependencies.return_value = []
    monkeypatch.setattr("app.services.schema_analyzer.OpenAPIAnalyzer", lambda schema: mock_analyzer)
    
    error_types = ["missing_field", "invalid_value"]
    rag = DependencyAwareRAG(1, SAMPLE_SCHEMA, error_types) # Assuming 1 is a valid service ID for testing
    
    assert rag.error_types == error_types
    
    def mock_generate_chain(self, candidate):
        assert self.error_types == error_types
        return SAMPLE_TEST_SUITE
    
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._generate_chain_for_candidate", mock_generate_chain)
    
    rag._build_dependency_graph = lambda: {"POST /users": {"dependencies": [], "dependents": []}}
    rag._identify_chain_candidates = lambda graph: [["POST /users"]]
    
    test_suites = rag.generate_request_chains()
    
    assert len(test_suites) == 1
    assert test_suites[0] == SAMPLE_TEST_SUITE

def test_circular_import_prevention():
    """循環インポートが発生しないことを確認するテスト"""
    import app.services.chain_generator
    import app.workers.tasks
    
    assert hasattr(app.services.chain_generator, "DependencyAwareRAG")
    assert hasattr(app.services.chain_generator, "ChainStore")
    assert hasattr(app.workers.tasks, "generate_test_suites_task")
