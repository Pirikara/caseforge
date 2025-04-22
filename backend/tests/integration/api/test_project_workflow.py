import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import init_db
import os
import json
import shutil

client = TestClient(app)

def test_project_workflow(monkeypatch, mock_chroma, mock_llm):
    # 一時ディレクトリを使用
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp/test_integration")
    monkeypatch.setattr("app.config.settings.TESTS_DIR", "/tmp/test_integration")
    
    # テスト用ディレクトリを作成
    os.makedirs("/tmp/test_integration", exist_ok=True)
    
    # データベースのテーブルを作成
    init_db()
    
    # index_schema 関数をモック化
    monkeypatch.setattr("app.services.schema.index_schema", lambda project_id, path: None)
    
    # trigger_test_generation 関数をモック化
    monkeypatch.setattr("app.api.projects.trigger_test_generation", lambda project_id: "mock-task-id")
    
    # ユニークなプロジェクト名を生成
    import uuid
    project_id = f"integration_test_{uuid.uuid4().hex[:8]}"
    
    # 1. プロジェクト作成
    response = client.post(f"/api/projects/?project_id={project_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    
    # 2. スキーマアップロード
    files = {"file": ("test.json", '{"openapi": "3.0.0"}', "application/json")}
    response = client.post(f"/api/projects/{project_id}/schema", files=files)
    assert response.status_code == 200
    
    # 3. テスト生成
    response = client.post(f"/api/projects/{project_id}/generate-tests")
    assert response.status_code == 200
    assert "task_id" in response.json()
    
    # 4. テスト一覧取得
    # モックを使用しているため、実際のファイルを作成
    os.makedirs(f"/tmp/test_integration/{project_id}", exist_ok=True)
    with open(f"/tmp/test_integration/{project_id}/tests.json", "w") as f:
        json.dump([
            {"id": "test1", "title": "Test Case 1", "request": {"method": "GET", "path": "/api/test"}, "expected": {"status": 200}}
        ], f)
    
    response = client.get(f"/api/projects/{project_id}/tests")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == "test1"
    
    # クリーンアップ
    if os.path.exists(f"/tmp/test_integration/{project_id}"):
        shutil.rmtree(f"/tmp/test_integration/{project_id}")
    if os.path.exists("/tmp/test_integration"):
        shutil.rmtree("/tmp/test_integration")