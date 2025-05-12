import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import json
import uuid
from datetime import datetime

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
    with patch("app.api.projects.generate_test_suites_task") as mock_task: # generate_chains_task を generate_test_suites_task に変更
        mock_task.delay.return_value = MagicMock(id="task-123")
        
        # テスト実行
        response = client.post("/api/projects/test_project/generate-tests")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["message"] == "Test suite generation (full_schema) started"
        assert response.json()["task_id"] == "task-123"

def test_list_test_suites():
    # サービス関数をモック化
    with patch("app.api.projects.ChainStore") as mock_store: # ChainStore のモックを app.api.projects に変更
        mock_store_instance = MagicMock()
        mock_store_instance.list_test_suites.return_value = [
            {"id": "suite-1", "name": "TestSuite 1", "test_cases_count": 2},
            {"id": "suite-2", "name": "TestSuite 2", "test_cases_count": 1}
        ]
        mock_store.return_value = mock_store_instance
        
        # テスト実行
        response = client.get("/api/projects/test_project/test-suites")
        
        # 検証
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "suite-1"
        assert response.json()[1]["name"] == "TestSuite 2"
        assert response.json()[0]["test_cases_count"] == 2

def test_get_test_suite_detail():
    # サービス関数をモック化
    with patch("app.api.projects.ChainStore") as mock_store: # ChainStore のモックを app.api.projects に変更
        mock_store_instance = MagicMock()
        mock_store_instance.get_test_suite.return_value = {
            "id": "suite-1",
            "name": "TestSuite 1",
            "test_cases": [
                {
                    "id": "case-1",
                    "name": "TestCase 1",
                    "test_steps": [
                        {"method": "POST", "path": "/users"},
                        {"method": "GET", "path": "/users/{id}"}
                    ]
                }
            ]
        }
        mock_store.return_value = mock_store_instance
        
        # テスト実行
        response = client.get("/api/projects/test_project/test-suites/suite-1")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["id"] == "suite-1"
        assert len(response.json()["test_cases"]) == 1
        assert len(response.json()["test_cases"][0]["test_steps"]) == 2

def test_run_test_suites():
    # サービス関数をモック化
    with patch("app.services.chain_runner.run_test_suites") as mock_run:
        mock_run.return_value = {
            "status": "completed",
            "task_id": "mock-task-id" # task_id は残しておく
        }
        
        # テスト実行
        response = client.post("/api/projects/test_project/run-test-suites")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert "task_id" in response.json()

def test_get_test_run_history():
    # サービス関数をモック化
    with patch("app.api.projects.list_test_runs") as mock_list:
        mock_list.return_value = [
            {
                "id": str(uuid.uuid4()),
                "run_id": "run-1",
                "suite_id": "suite-1",
                "suite_name": "Test Suite A",
                "status": "completed",
                "start_time": datetime.now(),
                "end_time": datetime.now(),
                "test_cases_count": 5,
                "passed_test_cases": 5,
                "success_rate": 100.0  # float!
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": "run-2",
                "suite_id": "suite-1",
                "suite_name": "Test Suite A",
                "status": "failed",
                "start_time": datetime.now(),
                "end_time": datetime.now(),
                "test_cases_count": 5,
                "passed_test_cases": 3,
                "success_rate": 60.0
            }
        ]
        
        # テスト実行
        response = client.get("/api/projects/test_project/runs")
        
        # 検証
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["run_id"] == "run-1"
        assert response.json()[1]["status"] == "failed"

def test_get_test_run_detail():
    # サービス関数をモック化
    with patch("app.api.projects.get_test_run") as mock_get: # patch の対象を app.api.projects に変更
        mock_get.return_value = {
            "id": "run-1-id", # TestRun の id を追加
            "run_id": "run-1",
            "suite_id": "suite-1",
            "status": "completed",
            "start_time": "2023-01-01T10:00:00Z", # start_time を追加 (datetime形式)
            "end_time": "2023-01-01T10:05:00Z", # end_time を追加 (datetime形式)
            "test_case_results": [
                {
                    "id": "case-1-result-id", # TestCaseResult の id を追加
                    "case_id": "case-1",
                    "status": "passed",
                    "error_message": None, # error_message を追加
                    "step_results": [
                        {
                            "id": "step-1-result-id", # StepResult の id を追加
                            "sequence": 0,
                            "method": "POST",
                            "path": "/users",
                            "status_code": 201,
                            "passed": True,
                            "response_body": {"id": 123, "name": "Test User"}, # response_body を追加
                            "error_message": None, # error_message を追加
                            "response_time": 100, # response_time を追加
                            "extracted_values": {"user_id": 123} # extracted_values を追加
                        },
                        {
                            "id": "step-2-result-id", # StepResult の id を追加
                            "sequence": 1,
                            "method": "GET",
                            "path": "/users/{id}",
                            "status_code": 200,
                            "passed": True,
                            "response_body": {"id": 123, "name": "Test User"}, # response_body を追加
                            "error_message": None, # error_message を追加
                            "response_time": 50, # response_time を追加
                            "extracted_values": {} # extracted_values を追加
                        }
                    ]
                }
            ]
        }
        
        # テスト実行
        response = client.get("/api/projects/test_project/runs/run-1")
        
        # 検証
        assert response.status_code == 200
        assert response.json()["run_id"] == "run-1"
        assert len(response.json()["test_case_results"]) == 1
        assert len(response.json()["test_case_results"][0]["step_results"]) == 2