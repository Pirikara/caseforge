import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import json

client = TestClient(app)

def test_list_projects():
    # サービス関数をモック化
    with patch("app.services.schema.list_projects", new_callable=AsyncMock) as mock_list_projects:
        mock_list_projects.return_value = [
            {"id": "test1", "name": "Test Project 1"},
            {"id": "test2", "name": "Test Project 2"}
        ]
        
        # テスト実行
        response = client.get("/api/projects/")
        
        # 検証
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "test1"
        assert response.json()[1]["name"] == "Test Project 2"

def test_create_project():
    # os.makedirs をモック化して、ファイルシステムへの書き込みを回避
    with patch("os.makedirs") as mock_makedirs, \
         patch("os.path.exists") as mock_exists, \
         patch("app.services.schema.create_project", new_callable=AsyncMock) as mock_db_create_project:
        mock_exists.return_value = False
        mock_db_create_project.return_value = {"status": "created", "project_id": "new_project", "name": "New Project"}

        # テスト実行
        response = client.post(
            "/api/projects/",
            json={"project_id": "new_project", "name": "New Project"}
        )

        # 検証
        assert response.status_code == 200
        assert response.json()["status"] == "created"
        assert response.json()["project_id"] == "new_project"

        # os.makedirs が呼ばれたことを確認
        # app.services.schema.create_project が呼ばれたことを確認
        mock_db_create_project.assert_called_once_with(
            project_id="new_project",
            name="New Project",
            description=None # デフォルト値
        )

def test_upload_schema():
    # サービス関数をモック化
    with patch("app.api.projects.save_and_index_schema") as mock_save:
        mock_save.return_value = {"message": "Schema uploaded and indexed successfully."}
        
        # テスト実行
        files = {"file": ("test.json", '{"openapi": "3.0.0"}', "application/json")}
        response = client.post("/api/projects/test_project/schema", files=files)
        
        # 検証
        assert response.status_code == 200
        assert response.json()["message"] == "Schema uploaded and indexed successfully."

def test_generate_tests():
    # サービス関数をモック化
    with patch("app.api.projects.generate_chains_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-123")
        
        # テスト実行
        response = client.post("/api/projects/test_project/generate-tests")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["message"] == "Test chain generation (full_schema) started"
        assert response.json()["task_id"] == "task-123"

def test_get_chains():
    # サービス関数をモック化
    with patch("app.services.chain_generator.ChainStore") as mock_store:
        mock_store_instance = MagicMock()
        mock_store_instance.list_chains.return_value = [
            {"id": "chain-1", "name": "Chain 1"},
            {"id": "chain-2", "name": "Chain 2"}
        ]
        mock_store.return_value = mock_store_instance
        
        # テスト実行
        response = client.get("/api/projects/test_project/chains")
        
        # 検証
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "chain-1"
        assert response.json()[1]["name"] == "Chain 2"

def test_get_chain_detail():
    # サービス関数をモック化
    with patch("app.services.chain_generator.ChainStore") as mock_store:
        mock_store_instance = MagicMock()
        mock_store_instance.get_chain.return_value = {
            "id": "chain-1",
            "name": "Chain 1",
            "steps": [
                {"method": "POST", "path": "/users"},
                {"method": "GET", "path": "/users/{id}"}
            ]
        }
        mock_store.return_value = mock_store_instance
        
        # テスト実行
        response = client.get("/api/projects/test_project/chains/chain-1")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["id"] == "chain-1"
        assert len(response.json()["steps"]) == 2

def test_run_project_chains():
    # サービス関数をモック化
    with patch("app.services.chain_runner.run_chains") as mock_run:
        mock_run.return_value = {
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
        
        # テスト実行
        response = client.post("/api/projects/test_project/run")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["message"] == "Chain run complete"

def test_get_run_history():
    # サービス関数をモック化
    with patch("app.services.chain_runner.list_chain_runs") as mock_list:
        mock_list.return_value = [
            {"run_id": "run-1", "chain_id": "chain-1", "status": "completed"},
            {"run_id": "run-2", "chain_id": "chain-1", "status": "failed"}
        ]
        
        # テスト実行
        response = client.get("/api/projects/test_project/runs")
        
        # 検証
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["run_id"] == "run-1"
        assert response.json()[1]["status"] == "failed"

def test_get_run_detail():
    # サービス関数をモック化
    with patch("app.services.chain_runner.get_chain_run") as mock_get:
        mock_get.return_value = {
            "run_id": "run-1",
            "chain_id": "chain-1",
            "status": "completed",
            "steps": [
                {"sequence": 0, "method": "POST", "path": "/users", "status_code": 201, "passed": True},
                {"sequence": 1, "method": "GET", "path": "/users/{id}", "status_code": 200, "passed": True}
            ]
        }
        
        # テスト実行
        response = client.get("/api/projects/test_project/runs/run-1")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["run_id"] == "run-1"
        assert len(response.json()["steps"]) == 2