from app.services.schema import save_and_index_schema, list_services, create_service
from app.models import Service, Schema
from sqlmodel import select
import os

async def test_save_and_index_schema(session, monkeypatch, test_service):
    def mock_index_schema(service_id: int, path: str):
        return True
    
    monkeypatch.setattr("app.services.schema.index_schema", mock_index_schema)
    
    # 一時ディレクトリを使用
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", "/tmp")
    
    # テスト実行
    content = b'{"openapi": "3.0.0"}'
    result = await save_and_index_schema(test_service.id, content, "test.json", session)
    
    # 検証
    assert result["message"] == "Schema uploaded, endpoints saved, and indexed successfully."
    
    # ファイルが作成されたか確認
    assert os.path.exists(f"/tmp/{test_service.id}/test.json")
    
    # データベースにサービスとスキーマが作成されたか確認
    service = session.exec(select(Service).where(Service.id == test_service.id)).first()
    assert service is not None
    
    schema = session.exec(select(Schema).where(Schema.service_id == service.id)).first()
    assert schema is not None
    assert schema.filename == "test.json"
    
    # クリーンアップ
    if os.path.exists(f"/tmp/{test_service.id}/test.json"):
        os.remove(f"/tmp/{test_service.id}/test.json")
    if os.path.exists(f"/tmp/{test_service.id}"):
        os.rmdir(f"/tmp/{test_service.id}")

async def test_list_services(session, test_service):
    # テスト実行
    result = await list_services(session)
    
    # 検証
    assert len(result) == 1
    assert result[0]["id"] == test_service.id
    assert result[0]["name"] == "Test Service"

async def test_create_service(session, monkeypatch):
    test_dir = "/tmp/test_caseforge_services"
    
    # os.makedirsとos.path.existsをモック化
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok=True: None)
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("app.config.settings.SCHEMA_DIR", test_dir)
    
    # テスト実行
    result = await create_service(name="New Service", description="A test service", session=session)
    
    # 検証
    assert result["status"] == "created"
    assert "id" in result
    
    # データベースにサービスが作成されたか確認
    service = session.exec(select(Service).where(Service.id == result["id"])).first()
    assert service is not None
    assert service.name == "New Service"
    assert service.description == "A test service"
