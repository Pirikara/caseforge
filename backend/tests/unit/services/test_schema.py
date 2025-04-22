import pytest
from app.services.schema import save_and_index_schema, list_projects, create_project
from app.models import Project, Schema
from sqlmodel import select
import os

# save_and_index_schemaのテスト
async def test_save_and_index_schema(session, monkeypatch, mock_chroma):
    # index_schemaをモック化
    def mock_index_schema(project_id, path):
        return True
    
    monkeypatch.setattr("app.services.schema.index_schema", mock_index_schema)
    
    # 一時ディレクトリを使用
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp")
    
    # テスト実行
    content = b'{"openapi": "3.0.0"}'
    result = await save_and_index_schema("test_project", content, "test.json", session)
    
    # 検証
    assert result["message"] == "Schema uploaded and indexed successfully."
    
    # ファイルが作成されたか確認
    assert os.path.exists("/tmp/test_project/test.json")
    
    # データベースにプロジェクトとスキーマが作成されたか確認
    project = session.exec(select(Project).where(Project.project_id == "test_project")).first()
    assert project is not None
    
    schema = session.exec(select(Schema).where(Schema.project_id == project.id)).first()
    assert schema is not None
    assert schema.filename == "test.json"
    
    # クリーンアップ
    if os.path.exists("/tmp/test_project/test.json"):
        os.remove("/tmp/test_project/test.json")
    if os.path.exists("/tmp/test_project"):
        os.rmdir("/tmp/test_project")

# list_projectsのテスト
async def test_list_projects(session, test_project):
    # テスト実行
    result = await list_projects(session)
    
    # 検証
    assert len(result) == 1
    assert result[0]["id"] == "test_project"
    assert result[0]["name"] == "Test Project"

# create_projectのテスト
async def test_create_project(session, monkeypatch):
    # 一時ディレクトリを使用
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp")
    
    # テスト実行
    result = await create_project("new_project", "New Project", "A test project", session)
    
    # 検証
    assert result["status"] == "created"
    assert result["project_id"] == "new_project"
    
    # データベースにプロジェクトが作成されたか確認
    project = session.exec(select(Project).where(Project.project_id == "new_project")).first()
    assert project is not None
    assert project.name == "New Project"
    assert project.description == "A test project"
    
    # ディレクトリが作成されたか確認
    assert os.path.exists("/tmp/new_project")
    
    # クリーンアップ
    if os.path.exists("/tmp/new_project"):
        os.rmdir("/tmp/new_project")