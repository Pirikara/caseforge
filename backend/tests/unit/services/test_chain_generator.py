import pytest
from app.services.chain_generator import DependencyAwareRAG, ChainStore
from unittest.mock import patch, MagicMock
import json
import os

from app.models import TestCase

# テスト用のシンプルなOpenAPIスキーma
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

# テスト用のサンプルテストスイート
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

def test_build_dependency_graph(mock_faiss, monkeypatch):
    """依存関係グラフ構築のテスト"""
    # OpenAPIAnalyzerのモック
    mock_analyzer = MagicMock()
    mock_analyzer.extract_dependencies.return_value = [
        {
            "type": "path_parameter",
            "source": {"path": "/users", "method": "post"},
            "target": {"path": "/users/{id}", "method": "get", "parameter": "id"}
        }
    ]
    monkeypatch.setattr("app.services.schema_analyzer.OpenAPIAnalyzer", lambda schema: mock_analyzer)
    
    # テスト実行
    rag = DependencyAwareRAG("test_project", SAMPLE_SCHEMA)
    graph = rag._build_dependency_graph()
    
    # 検証
    assert "POST /users" in graph
    assert "GET /users/{id}" in graph
    assert "GET /users/{id}" in graph["POST /users"]["dependents"]
    assert "POST /users" in graph["GET /users/{id}"]["dependencies"]

def test_identify_chain_candidates(mock_faiss, monkeypatch):
    """チェーン候補特定のテスト"""
    # 依存関係グラフのモック
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
    
    # テスト実行
    rag = DependencyAwareRAG("test_project", SAMPLE_SCHEMA)
    # _build_dependency_graphをモック
    rag._build_dependency_graph = lambda: mock_graph
    
    candidates = rag._identify_chain_candidates(mock_graph)
    
    # 検証
    assert len(candidates) > 0
    assert ["POST /users", "GET /users/{id}"] in candidates

def test_generate_test_suite_for_candidate(mock_faiss, mock_llm, monkeypatch):
    """テストスイート生成のテスト"""
    # LLMのレスポンスをモック
    class MockResponse:
        content = json.dumps(SAMPLE_TEST_SUITE)
    
    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke.return_value = MockResponse()
    monkeypatch.setattr("langchain_openai.ChatOpenAI", lambda **kwargs: mock_llm_instance)
    
    # テスト実行
    rag = DependencyAwareRAG("test_project", SAMPLE_SCHEMA)
    test_suite = rag._generate_chain_for_candidate(["POST /users", "GET /users/{id}"]) # メソッド名はそのまま
    
    # 検証
    assert test_suite is not None
    assert test_suite["name"] == SAMPLE_TEST_SUITE["name"]
    assert test_suite["target_method"] == SAMPLE_TEST_SUITE["target_method"]
    assert test_suite["target_path"] == SAMPLE_TEST_SUITE["target_path"]
    assert len(test_suite["test_cases"]) == len(SAMPLE_TEST_SUITE["test_cases"])
    assert test_suite["test_cases"][0]["name"] == SAMPLE_TEST_SUITE["test_cases"][0]["name"]
    assert len(test_suite["test_cases"][0]["test_steps"]) == len(SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"])
    assert test_suite["test_cases"][1]["error_type"] == SAMPLE_TEST_SUITE["test_cases"][1]["error_type"]

def test_generate_test_suites(mock_faiss, mock_llm, monkeypatch):
    """テストスイート生成のテスト"""
    # _build_dependency_graphをモック
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
    
    # _identify_chain_candidatesをモック
    mock_candidates = [["POST /users", "GET /users/{id}"]]
    
    # _generate_chain_for_candidateをモック
    mock_test_suite = SAMPLE_TEST_SUITE # SAMPLE_CHAIN を SAMPLE_TEST_SUITE に変更
    
    # モック関数を設定
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._build_dependency_graph", lambda self: mock_graph)
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._identify_chain_candidates", lambda self, graph: mock_candidates)
    monkeypatch.setattr("app.services.chain_generator.DependencyAwareRAG._generate_chain_for_candidate", lambda self, candidate: mock_test_suite) # _generate_chain_for_candidate はそのまま
    
    # テスト実行
    rag = DependencyAwareRAG("test_project", SAMPLE_SCHEMA)
    test_suites = rag.generate_request_chains() # メソッド名はそのまま
    
    # 検証
    assert len(test_suites) == 1
    assert test_suites[0]["name"] == SAMPLE_TEST_SUITE["name"]
    assert len(test_suites[0]["test_cases"]) == len(SAMPLE_TEST_SUITE["test_cases"])
    assert len(test_suites[0]["test_cases"][0]["test_steps"]) == len(SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"])

def test_chain_store_save_test_suites(session, test_project, monkeypatch):
    """テストスイート保存のテスト"""
    # ディレクトリ作成をモック
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
    
    # ファイル書き込みをモック
    mock_open = MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)
    
    # テスト実行
    chain_store = ChainStore()
    chain_store.save_chains(session, test_project.project_id, [SAMPLE_TEST_SUITE]) # session を渡すように変更
    
    # 検証
    # TestSuiteが作成されたことを確認
    from app.models import TestSuite, TestStep
    from sqlmodel import select
    
    test_suites = session.exec(select(TestSuite).where(TestSuite.project_id == test_project.id)).all()
    assert len(test_suites) == 1
    assert test_suites[0].name == SAMPLE_TEST_SUITE["name"]
    assert test_suites[0].target_method == SAMPLE_TEST_SUITE["target_method"]
    assert test_suites[0].target_path == SAMPLE_TEST_SUITE["target_path"]

    # TestCaseが作成されたことを確認
    test_cases = session.exec(select(TestCase).where(TestCase.suite_id == test_suites[0].id)).all()
    assert len(test_cases) == len(SAMPLE_TEST_SUITE["test_cases"])
    assert test_cases[0].name == SAMPLE_TEST_SUITE["test_cases"][0]["name"]
    assert test_cases[1].error_type == SAMPLE_TEST_SUITE["test_cases"][1]["error_type"]

    # TestStepが作成されたことを確認
    test_steps_case1 = session.exec(select(TestStep).where(TestStep.case_id == test_cases[0].id)).all()
    assert len(test_steps_case1) == len(SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"])
    assert test_steps_case1[0].method == SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"][0]["method"]

    test_steps_case2 = session.exec(select(TestStep).where(TestStep.case_id == test_cases[1].id)).all()
    assert len(test_steps_case2) == len(SAMPLE_TEST_SUITE["test_cases"][1]["test_steps"])
    assert test_steps_case2[0].method == SAMPLE_TEST_SUITE["test_cases"][1]["test_steps"][0]["method"]

    # テスト後に保存されたテストスイートをデータベースから取得して削除
    from app.models import TestSuite
    from sqlmodel import select
    
    # テスト後に保存されたテストスイートをデータベースから取得して全て削除
    from app.models import TestSuite
    from sqlmodel import select
    
    saved_test_suites = session.exec(select(TestSuite).where(TestSuite.project_id == test_project.id)).all()
    for suite in saved_test_suites:
        session.delete(suite)
    session.commit()

def test_chain_store_list_test_suites(session, test_project, monkeypatch):
    """テストスイート一覧取得のテスト"""
    # テスト用のテストスイートを作成
    from app.models import TestSuite # インポートするモデルを変更
    
    test_suite = TestSuite(
        id="test-suite-1", # id に変更
        project_id=test_project.id, # project_id を test_project.project_id に変更
        name="Test TestSuite", # 名前の変更
        target_method="GET", # target_method を追加
        target_path="/items" # target_path を追加
    )
    session.add(test_suite)
    session.flush() # id を生成するために flush

    # テストケースを追加
    test_case = TestCase(
        id="test-case-1",
        suite_id=test_suite.id,
        name="Normal Case"
    )
    session.add(test_case)
    session.commit()
    
    # テスト実行
    chain_store = ChainStore() # ChainStore の名前はそのまま
    test_suites = chain_store.list_test_suites(session, test_project.project_id) # session を渡すように変更
    print("test_suites : ", test_suites) # デバッグ用に出力
    
    # 検証
    # "Test TestSuite" という名前のテストスイートをフィルタリング
    filtered_suites = [suite for suite in test_suites if suite["project_id"] == test_project.id] # project_id でフィルタリング
    print(filtered_suites) # デバッグ用に出力

    assert len(filtered_suites) == 1
    assert filtered_suites[0]["id"] == "test-suite-1" # id を確認
    assert filtered_suites[0]["name"] == "Test TestSuite"
    assert filtered_suites[0]["target_method"] == "GET"
    assert filtered_suites[0]["target_path"] == "/items"
    assert filtered_suites[0]["test_cases_count"] == 1 # test_cases_count を確認

def test_chain_store_get_test_suite(session, test_project, monkeypatch):
    """特定のテストスイート取得のテスト"""
    # テスト用のテストスイート、テストケース、テストステップを作成
    from app.models import TestSuite, TestStep # インポートするモデルを変更

    test_suite = TestSuite(
        id="test-suite-1", # id に変更
        project_id=test_project.id, # project_id を test_project.project_id に変更
        name="POST /users TestSuite", # 名前の変更
        target_method="POST", # target_method を追加
        target_path="/users" # target_path を追加
    )
    session.add(test_suite)
    session.flush() # id を生成するために flush

    test_case = TestCase(
        id="test-case-1", # id を追加
        suite_id=test_suite.id, # suite_id に変更
        name="Normal Case", # 名前の変更
        description="Normal user creation", # description を追加
        error_type=None # error_type を追加
    )
    session.add(test_case)
    session.flush() # id を生成するために flush

    step1 = TestStep(
        id="test-step-1", # id を追加
        case_id=test_case.id, # case_id に変更
        sequence=0,
        method="POST",
        path="/users",
        request_body={"name": "Test User"}, # request_body を追加
        expected_status=201 # expected_status を追加
    )
    step2 = TestStep(
        id="test-step-2", # id を追加
        case_id=test_case.id, # case_id に変更
        sequence=1,
        method="GET",
        path="/users/{id}",
        extract_rules={"user_id": "$.id"}, # extract_rules を追加
        expected_status=200 # expected_status を追加
    )
    session.add(step1)
    session.add(step2)
    session.commit()
    
    # テスト実行
    chain_store = ChainStore() # ChainStore の名前はそのまま
    test_suite_data = chain_store.get_test_suite(session, test_project.project_id, "test-suite-1") # session を追加
    
    # 検証
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