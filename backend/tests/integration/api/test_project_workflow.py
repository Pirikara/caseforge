import pytest
from fastapi.testclient import TestClient
from app.main import app
import os
import json

client = TestClient(app)

def test_project_workflow(monkeypatch, mock_chroma, mock_llm):
    # 一時ディレクトリを使用
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp/test_integration")
    monkeypatch.setattr("app.config.settings.TESTS_DIR", "/tmp/test_integration")
    
    # テスト用ディレクトリを作成
    os.makedirs("/tmp/test_integration", exist_ok=True)
    
    # 1. プロジェクト作成
    response = client.post("/api/projects/?project_id=integration_test")
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    
    # 2. スキーマアップロード
    files = {"file": ("test.json", '{"openapi": "3.0.0"}', "application/json")}
    response = client.post("/api/projects/integration_test/schema", files=files)
    assert response.status_code == 200
    
    # 3. テスト生成
    response = client.post("/api/projects/integration_test/generate-tests")
    assert response.status_code == 200
    assert "task_id" in response.json()
    
    # 4. テスト一覧取得
    # モックを使用しているため、実際のファイルを作成
    os.makedirs("/tmp/test_integration/integration_test", exist_ok=True)
    with open("/tmp/test_integration/integration_test/tests.json", "w") as f:
        json.dump([
            {"id": "test1", "title": "Test Case 1", "request": {"method": "GET", "path": "/api/test"}, "expected": {"status": 200}}
        ], f)
    
    response = client.get("/api/projects/integration_test/tests")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "test1"
    
    # クリーンアップ
    if os.path.exists("/tmp/test_integration/integration_test/tests.json"):
        os.remove("/tmp/test_integration/integration_test/tests.json")
    if os.path.exists("/tmp/test_integration/integration_test"):
        os.rmdir("/tmp/test_integration/integration_test")
    if os.path.exists("/tmp/test_integration"):
        os.rmdir("/tmp/test_integration")