from .base import TimestampModel, get_session, engine
from .service import Service, Schema
from .test import TestSuite, TestCase, TestStep, TestRun, TestCaseResult, StepResult
from .endpoint import Endpoint

# モデルをインポートしてSQLModelに認識させる
__all__ = [
    "TimestampModel", "get_session", "engine",
    "Service", "Schema",
    "TestSuite", "TestCase", "TestStep",
    "TestRun", "TestCaseResult", "StepResult",
    "Endpoint"
]

# データベース初期化関数
def init_db():
    """データベーススキーマを初期化する"""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
