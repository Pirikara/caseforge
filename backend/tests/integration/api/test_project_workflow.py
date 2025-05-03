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

def test_chain_workflow(monkeypatch, mock_faiss, mock_llm, session):
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
    monkeypatch.setattr("app.api.projects.generate_chains_task.delay", lambda project_id: mock_task)
    
    # run_chains 関数をモック化
    mock_run_chains = AsyncMock()
    mock_run_chains.return_value = {
        "status": "completed",
        "message": "Executed 1 chains",
        "results": [
            {
                "name": "Chain 1",
                "status": "completed",
                "success": True,
                "steps": [
                    {"success": True, "status_code": 201},
                    {"success": True, "status_code": 200}
                ]
            }
        ]
    }
    monkeypatch.setattr("app.api.projects.run_chains", mock_run_chains)
    
    # ChainStore 関数をモック化
    mock_chain_store = MagicMock()
    mock_chain_store.list_chains.return_value = [
        {"id": "chain-1", "name": "Chain 1", "steps_count": 2}
    ]
    mock_chain_store.get_chain.return_value = {
        "id": "chain-1",
        "name": "Chain 1",
        "steps": [
            {"method": "POST", "path": "/users", "request": {"body": {"name": "Test User"}}},
            {"method": "GET", "path": "/users/{id}", "request": {}}
        ]
    }
    monkeypatch.setattr("app.services.chain_generator.ChainStore", lambda: mock_chain_store)
    
    # APIエンドポイントで直接使用されるChainStoreのメソッドもモック化
    monkeypatch.setattr("app.api.projects.ChainStore", lambda: mock_chain_store)
    
    # list_chain_runs 関数をモック化
    monkeypatch.setattr("app.api.projects.list_chain_runs", lambda project_id, limit=10: [
        {"run_id": "run-1", "chain_id": "chain-1", "status": "completed", "success_rate": 100}
    ])
    
    # get_chain_run 関数をモック化
    monkeypatch.setattr("app.api.projects.get_chain_run", lambda project_id, run_id: {
        "run_id": "run-1",
        "chain_id": "chain-1",
        "status": "completed",
        "steps": [
            {"sequence": 0, "method": "POST", "path": "/users", "status_code": 201, "passed": True},
            {"sequence": 1, "method": "GET", "path": "/users/{id}", "status_code": 200, "passed": True}
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
    
    # 3. チェーン生成
    response = client.post(f"/api/projects/{project_id}/generate-tests")
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert response.json()["message"] == "Test chain generation (full_schema) started"
    
    # 4. チェーン一覧取得
    response = client.get(f"/api/projects/{project_id}/chains")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "chain-1"
    
    # 5. チェーン詳細取得
    response = client.get(f"/api/projects/{project_id}/chains/chain-1")
    assert response.status_code == 200
    assert response.json()["id"] == "chain-1"
    assert len(response.json()["steps"]) == 2
    
    # 6. チェーン実行
    response = client.post(f"/api/projects/{project_id}/run")
    assert response.status_code == 200
    assert response.json()["message"] == "Chain run complete"
    
    # 7. 実行履歴取得
    response = client.get(f"/api/projects/{project_id}/runs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["run_id"] == "run-1"
    
    # 8. 実行詳細取得
    response = client.get(f"/api/projects/{project_id}/runs/run-1")
    assert response.status_code == 200
    assert response.json()["run_id"] == "run-1"
    assert len(response.json()["steps"]) == 2
    
    # クリーンアップ
    if os.path.exists(f"/tmp/test_integration/{project_id}"):
        shutil.rmtree(f"/tmp/test_integration/{project_id}")
    if os.path.exists("/tmp/test_integration"):
        shutil.rmtree("/tmp/test_integration")