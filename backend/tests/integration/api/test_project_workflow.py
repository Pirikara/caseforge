import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import init_db
from app.config import settings
import os
import json
import shutil
from unittest.mock import patch, MagicMock, AsyncMock

client = TestClient(app)

def test_workflow(monkeypatch, mock_faiss, mock_llm, session):
    # ユニークなプロジェクト名を生成
    import uuid
    project_id = f"integration_test_{uuid.uuid4().hex[:8]}"
    
    # 一時ディレクトリを使用
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp/test_integration")
    monkeypatch.setattr("app.config.settings.TESTS_DIR", "/tmp/test_integration")
    monkeypatch.setattr("app.config.settings.LOG_DIR", "/tmp/test_integration/logs")
    
    # テスト用ディレクトリを作成
    os.makedirs("/tmp/test_integration", exist_ok=True)
    os.makedirs("/tmp/test_integration/logs", exist_ok=True)
    
    # ファイルシステム操作をモック化
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok=True: None)
    mock_open = MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)
    
    # Path.exists をモック化（プロジェクト作成時はFalse、それ以外はTrue）
    create_project_called = [False]  # リスト内に変数を格納して参照渡しにする
    
    def mock_path_exists(path):
        path_str = str(path)
        # プロジェクト作成時のチェックの場合
        if path_str == f"/tmp/test_integration/{project_id}" and not create_project_called[0]:
            create_project_called[0] = True  # 一度だけFalseを返す
            return False
        return True
    monkeypatch.setattr("pathlib.Path.exists", mock_path_exists)
    
    # Path.glob をモック化
    monkeypatch.setattr("pathlib.Path.glob", lambda path, pattern: [MagicMock(name="test.json")])
    
    # init_db()の呼び出しを削除（conftest.pyで既に初期化されている）
    
    # index_schema 関数をモック化
    monkeypatch.setattr("app.services.schema.index_schema", lambda project_id, path: None)
    
    # generate_chains_task 関数をモック化
    mock_task = MagicMock()
    mock_task.id = "mock-task-id"
    monkeypatch.setattr("app.api.projects.generate_test_suites_task.delay", lambda project_id, error_types: mock_task) # generate_chains_task を generate_test_suites_task に変更, error_types 引数を追加
    
    # run_chains 関数をモック化
    mock_run_test_suites = AsyncMock()
    mock_run_test_suites.return_value = {
        "message": "Test suite run complete",
        "task_id": "mock-run-task-id",
        "status": "triggered"
    }
    monkeypatch.setattr("app.api.projects.run_test_suites", mock_run_test_suites)
    
    # TestSuiteStore 関数をモック化
    mock_test_suite_store = MagicMock()
    mock_test_suite_store.list_test_suites.return_value = [
        {"id": "suite-1", "name": "TestSuite 1", "test_cases_count": 2}
    ]
    mock_test_suite_store.get_test_suite.return_value = {
        "id": "suite-1",
        "name": "TestSuite 1",
        "test_cases": [
            {
                "id": "case-1",
                "name": "TestCase 1",
                "test_steps": [
                    {"method": "POST", "path": "/users", "request": {"body": {"name": "Test User"}}},
                    {"method": "GET", "path": "/users/{id}", "request": {}}
                ]
            }
        ]
    }
    monkeypatch.setattr("app.services.chain_generator.ChainStore", lambda: mock_test_suite_store) # ChainStore のモックを TestSuiteStore に変更
    
    # APIエンドポイントで直接使用されるChainStoreのメソッドもモック化
    monkeypatch.setattr("app.api.projects.ChainStore", lambda: mock_test_suite_store) # ChainStore のモックを TestSuiteStore に変更
    
    # list_test_runs 関数をモック化
    monkeypatch.setattr("app.api.projects.list_test_runs", lambda project_id, limit=10: [
        {"id": "run-1-id", "run_id": "run-1", "suite_id": "suite-1", "suite_name": "TestSuite 1", "status": "completed", "start_time": "2023-01-01T10:00:00Z", "end_time": "2023-01-01T10:05:00Z", "test_cases_count": 2, "passed_test_cases": 2, "success_rate": 100} # TestRunSummary スキーマに合わせる
    ])
    
    # get_test_run 関数をモック化
    monkeypatch.setattr("app.api.projects.get_test_run", lambda project_id, run_id: {
        "run_id": "run-1",
        "suite_id": "suite-1",
        "status": "completed",
        "test_case_results": [
            {
                "case_id": "case-1",
                "status": "passed",
                "step_results": [
                    {"sequence": 0, "method": "POST", "path": "/users", "status_code": 201, "passed": True},
                    {"sequence": 1, "method": "GET", "path": "/users/{id}", "status_code": 200, "passed": True}
                ]
            }
        ]
    })
    
    # project_id は既に定義済み
    
    # 1. プロジェクト作成
    response = client.post(
        "/api/projects/",
        json={"project_id": project_id, "name": f"Integration Test {project_id}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    
    # 2. スキーマアップロード
    files = {"file": ("test.json", '{"openapi": "3.0.0"}', "application/json")}
    response = client.post(f"/api/projects/{project_id}/schema", files=files)
    assert response.status_code == 200
    
    # 3. テストスイート生成
    response = client.post(f"/api/projects/{project_id}/generate-tests")
    print(response.json())
    print(response.status_code)
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert response.json()["message"] == "Test suite generation (full_schema) started"
    
    # 4. テストスイート一覧取得
    response = client.get(f"/api/projects/{project_id}/test-suites")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "suite-1"
    
    # 5. テストスイート詳細取得
    response = client.get(f"/api/projects/{project_id}/test-suites/suite-1")
    assert response.status_code == 200
    assert response.json()["id"] == "suite-1"
    assert len(response.json()["test_cases"]) == 1
    assert len(response.json()["test_cases"][0]["test_steps"]) == 2
    
    # 6. テストスイート実行
    response = client.post(f"/api/projects/{project_id}/run-test-suites")
    assert response.status_code == 200
    assert response.json()["message"] == "Test suite run complete"
    
    # 7. 実行履歴取得
    response = client.get(f"/api/projects/{project_id}/runs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["run_id"] == "run-1"
    
    # 8. 実行詳細取得
    response = client.get(f"/api/projects/{project_id}/runs/run-1")
    assert response.status_code == 200
    assert response.json()["run_id"] == "run-1"
    assert len(response.json()["test_case_results"]) == 1
    assert len(response.json()["test_case_results"][0]["step_results"]) == 2
    
    # クリーンアップ
    if os.path.exists(f"/tmp/test_integration/{project_id}"):
        shutil.rmtree(f"/tmp/test_integration/{project_id}")
    if os.path.exists("/tmp/test_integration"):
        shutil.rmtree("/tmp/test_integration")