from sqlmodel import Field, SQLModel, create_engine, Session
from datetime import datetime, UTC
import os
from app.config import settings

# データベース接続設定
# テスト環境の場合はSQLiteを使用
if os.environ.get("TESTING") == "1":
    # テスト用にファイルベースのデータベースを使用
    TEST_DB_PATH = "/tmp/test_caseforge/test.db"
    DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
else:
    DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

# ベースモデル
class TimestampModel(SQLModel):
    """タイムスタンプを持つ全モデルの基底クラス"""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))