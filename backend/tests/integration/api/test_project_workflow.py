from fastapi.testclient import TestClient
from app.main import app
import os
import shutil
from unittest.mock import MagicMock, AsyncMock

client = TestClient(app)

def test_workflow(monkeypatch):
    import uuid
    service_id = f"integration_test_{uuid.uuid4().hex[:8]}"
    
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp/test_integration")
    monkeypatch.setattr("app.config.settings.TESTS_DIR", "/tmp/test_integration")
    monkeypatch.setattr("app.config.settings.LOG_DIR", "/tmp/test_integration/logs")
    
    os.makedirs("/tmp/test_integration", exist_ok=True)
    os.makedirs("/tmp/test_integration/logs", exist_ok=True)
    
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok=True: None)
    mock_open = MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)
    
    create_service_called = [False]
    
    def mock_path_exists(path):
        path_str = str(path)
        if path_str == f"/tmp/test_integration/{service_id}" and not create_service_called[0]:
            create_service_called[0] = True
            return False
        return True
    monkeypatch.setattr("pathlib.Path.exists", mock_path_exists)
    monkeypatch.setattr("pathlib.Path.glob", lambda path, pattern: [MagicMock(name="test.json")])    
    monkeypatch.setattr("app.services.schema.index_schema", lambda service_id, path: None)
    
    mock_task = MagicMock()
    mock_task.id = "mock-task-id"
    monkeypatch.setattr("app.api.services.generate_test_suites_task.delay", lambda service_id, error_types: mock_task)
    
    mock_run_test_suites = AsyncMock()
    mock_run_test_suites.return_value = {
        "message": "Test suite run complete",
        "task_id": "mock-run-task-id",
        "status": "triggered"
    }
    monkeypatch.setattr("app.api.services.run_test_suites", mock_run_test_suites)
    
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
    monkeypatch.setattr("app.services.chain_generator.ChainStore", lambda: mock_test_suite_store)
    
    monkeypatch.setattr("app.api.services.ChainStore", lambda: mock_test_suite_store)
    
    monkeypatch.setattr("app.api.services.list_test_runs", lambda service_id, limit=10: [
        {"id": 1, "run_id": "run-1-id", "service_id": service_id, "suite_id": "suite-1", "suite_name": "TestSuite 1", "status": "completed", "start_time": "2023-01-01T10:00:00Z", "end_time": "2023-01-01T10:05:00Z", "test_cases_count": 2, "passed_test_cases": 2, "success_rate": 100} # TestRunSummary スキーマに合わせる
    ])
    
    monkeypatch.setattr("app.api.services.get_test_run", lambda service_id, run_id: {
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
    
    response = client.post(
        "/api/services/",
        json={"service_id": service_id, "name": f"Integration Test {service_id}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    
    service_int_id = response.json()["id"]
    
    files = {"file": ("test.json", '{"openapi": "3.0.0"}', "application/json")}
    response = client.post(f"/api/services/{service_int_id}/schema", files=files)
    assert response.status_code == 200
    
    response = client.post(f"/api/services/{service_int_id}/generate-tests")
    print(response.json())
    print(response.status_code)
    assert response.status_code == 200
    assert "task_id" in response.json()
    assert response.json()["message"] == "Test suite generation (full_schema) started"
    
    response = client.get(f"/api/services/{service_int_id}/test-suites")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "suite-1"
    
    response = client.get(f"/api/services/{service_int_id}/test-suites/suite-1")
    assert response.status_code == 200
    assert response.json()["id"] == "suite-1"
    assert len(response.json()["test_cases"]) == 1
    assert len(response.json()["test_cases"][0]["test_steps"]) == 2
    
    response = client.post(f"/api/services/{service_int_id}/run-test-suites")
    assert response.status_code == 200
    assert response.json()["message"] == "Test suite run complete"
    
    response = client.get(f"/api/services/{service_int_id}/runs")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["run_id"] == "run-1-id"
    
    response = client.get(f"/api/services/{service_int_id}/runs/run-1")
    assert response.status_code == 200
    assert response.json()["run_id"] == "run-1"
    assert len(response.json()["test_case_results"]) == 1
    assert len(response.json()["test_case_results"][0]["step_results"]) == 2
    
    if os.path.exists(f"/tmp/test_integration/{service_id}"):
        shutil.rmtree(f"/tmp/test_integration/{service_id}")
    if os.path.exists("/tmp/test_integration"):
        shutil.rmtree("/tmp/test_integration")
