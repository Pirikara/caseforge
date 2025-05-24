from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock, AsyncMock
import uuid
from datetime import datetime

client = TestClient(app)

def test_list_services():
    with patch("app.services.schema.list_services", new_callable=AsyncMock) as mock_list_services:
        mock_list_services.return_value = [
            {"id": "test1", "name": "Test Service 1"},
            {"id": "test2", "name": "Test Service 2"}
        ]
        
        response = client.get("/api/services/")
        
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "test1"
        assert response.json()[1]["name"] == "Test Service 2"

def test_create_service():
    with patch("os.makedirs") as mock_makedirs, \
         patch("os.path.exists") as mock_exists, \
         patch("app.services.schema.create_service", new_callable=AsyncMock) as mock_db_create_service:
        mock_exists.return_value = False
        mock_db_create_service.return_value = {"status": "created", "id": 1, "name": "New Service"}

        response = client.post(
            "/api/services/",
            json={"name": "New Service"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "created"
        assert "id" in response.json()
 
        mock_db_create_service.assert_called_once_with(
            name="New Service",
            description=None
        )

def test_upload_schema():
    with patch("app.api.services.save_and_index_schema") as mock_save:
        mock_save.return_value = {"message": "Schema uploaded and indexed successfully."}
        
        files = {"file": ("test.json", '{"openapi": "3.0.0"}', "application/json")}
        response = client.post("/api/services/1/schema", files=files)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Schema uploaded and indexed successfully."

def test_generate_tests():
    with patch("app.api.services.generate_test_suites_task") as mock_task, \
         patch("app.api.services.get_schema_files_or_400") as mock_get_schema_files:
        
        # get_schema_files_or_400 がダミーのファイルリストを返すようにモック
        # get_schema_files_or_400 がダミーのPathオブジェクトのリストを返すようにモック
        # Path オブジェクトのように振る舞うように exists() と name をモックする
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.name = "dummy_schema.json"
        # ダミーのスキーマファイル内容を返すように read_text をモック
        mock_path.read_text.return_value = '{"openapi": "3.0.0", "info": {"title": "Dummy API", "version": "1.0.0"}, "paths": {}}'
        # ダミーのスキーマファイル内容を返すように read_text をモック
        mock_path.read_text.return_value = '{"openapi": "3.0.0", "info": {"title": "Dummy API", "version": "1.0.0"}, "paths": {}}'
        mock_get_schema_files.return_value = [mock_path]
        
        mock_task.delay.return_value = MagicMock(id="task-123")
        
        response = client.post("/api/services/1/generate-tests")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Test suite generation (full_schema) started"
        assert response.json()["task_id"] == "task-123"

def test_list_test_suites():
    with patch("app.api.services.ChainStore") as mock_store:
        mock_store_instance = MagicMock()
        mock_store_instance.list_test_suites.return_value = [
            {"id": "suite-1", "name": "TestSuite 1", "test_cases_count": 2},
            {"id": "suite-2", "name": "TestSuite 2", "test_cases_count": 1}
        ]
        mock_store.return_value = mock_store_instance
        
        response = client.get("/api/services/1/test-suites")
        
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == "suite-1"
        assert response.json()[1]["name"] == "TestSuite 2"
        assert response.json()[0]["test_cases_count"] == 2

def test_get_test_suite_detail():
    with patch("app.api.services.ChainStore") as mock_store:
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
        
        response = client.get("/api/services/1/test-suites/suite-1")
        
        assert response.status_code == 200
        assert response.json()["id"] == "suite-1"
        assert len(response.json()["test_cases"]) == 1
        assert len(response.json()["test_cases"][0]["test_steps"]) == 2

def test_run_test_suites():
    with patch("app.services.chain_runner.run_test_suites") as mock_run:
        mock_run.return_value = {
            "status": "completed",
            "task_id": "mock-task-id"
        }
        
        response = client.post("/api/services/1/run-test-suites")
        
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert "task_id" in response.json()

def test_get_test_run_history():
    with patch("app.api.services.list_test_runs") as mock_list:
        mock_list.return_value = [
            {
                "id": 1,
                "run_id": "run-1",
                "service_id": 1,
                "suite_id": "suite-1",
                "suite_name": "Test Suite A",
                "status": "completed",
                "start_time": datetime.now(),
                "end_time": datetime.now(),
                "test_cases_count": 5,
                "passed_test_cases": 5,
                "success_rate": 100.0
            },
            {
                "id": 1,
                "run_id": "run-2",
                "service_id": 1,
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
        
        response = client.get("/api/services/1/runs")
        
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["run_id"] == "run-1"
        assert response.json()[1]["status"] == "failed"

def test_get_test_run_detail():
    with patch("app.api.services.get_test_run") as mock_get:
        mock_get.return_value = {
            "id": "run-1-id",
            "run_id": "run-1",
            "suite_id": "suite-1",
            "status": "completed",
            "start_time": "2023-01-01T10:00:00Z",
            "end_time": "2023-01-01T10:05:00Z",
            "test_case_results": [
                {
                    "id": "case-1-result-id",
                    "case_id": "case-1",
                    "status": "passed",
                    "error_message": None,
                    "step_results": [
                        {
                            "id": "step-1-result-id",
                            "sequence": 0,
                            "method": "POST",
                            "path": "/users",
                            "status_code": 201,
                            "passed": True,
                            "response_body": {"id": 123, "name": "Test User"},
                            "error_message": None,
                            "response_time": 100,
                            "extracted_values": {"user_id": 123}
                        },
                        {
                            "id": "step-2-result-id",
                            "sequence": 1,
                            "method": "GET",
                            "path": "/users/{id}",
                            "status_code": 200,
                            "passed": True,
                            "response_body": {"id": 123, "name": "Test User"},
                            "error_message": None,
                            "response_time": 50,
                            "extracted_values": {}
                        }
                    ]
                }
            ]
        }
        
        response = client.get("/api/services/1/runs/run-1")
        
        assert response.status_code == 200
        assert response.json()["run_id"] == "run-1"
        assert len(response.json()["test_case_results"]) == 1
        assert len(response.json()["test_case_results"][0]["step_results"]) == 2
