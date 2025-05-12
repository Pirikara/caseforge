from .base import TimestampModel, get_session, engine
from .project import Project, Schema
from .test_models import TestRun, TestCaseResult, StepResult, TestCase # TestCase を追加
from .chain import TestSuite, TestStep
from .endpoint import Endpoint

# モデルをインポートしてSQLModelに認識させる
__all__ = [
    "TimestampModel", "get_session", "engine",
    "Project", "Schema",
    "TestRun", "TestCaseResult", "TestCase", # TestCase を追加
    "TestSuite", "TestStep", "StepResult",
    "Endpoint"
]

# データベース初期化関数
def init_db():
    """データベーススキーマを初期化する"""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)