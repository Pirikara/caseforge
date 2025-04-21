from sqlmodel import Field, SQLModel, create_engine, Session
from typing import Optional, List
from datetime import datetime
from app.config import settings

# データベース接続設定
DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session

# ベースモデル
class TimestampModel(SQLModel):
    """タイムスタンプを持つ全モデルの基底クラス"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)