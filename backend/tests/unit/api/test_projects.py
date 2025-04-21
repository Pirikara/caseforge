import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_list_projects():
    # サービス関数をモック化
    with patch("app.api.projects.list_projects") as mock_list_projects:
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
    # サービス関数をモック化
    with patch("app.api.projects.create_project") as mock_create_project:
        mock_create_project.return_value = {"status": "created", "project_id": "new_project"}
        
        # テスト実行
        response = client.post("/api/projects/?project_id=new_project")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["status"] == "created"
        assert response.json()["project_id"] == "new_project"

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
    with patch("app.api.projects.trigger_test_generation") as mock_trigger:
        mock_trigger.return_value = "task-123"
        
        # テスト実行
        response = client.post("/api/projects/test_project/generate-tests")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["message"] == "Test generation started"
        assert response.json()["task_id"] == "task-123"