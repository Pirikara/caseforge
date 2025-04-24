from .base import TimestampModel, get_session, engine
from .project import Project, Schema
from .test import TestCase, TestRun, TestResult
from .chain import TestChain, TestChainStep, ChainRun, StepResult

# モデルをインポートしてSQLModelに認識させる
__all__ = [
    "TimestampModel", "get_session", "engine",
    "Project", "Schema",
    "TestCase", "TestRun", "TestResult",
    "TestChain", "TestChainStep", "ChainRun", "StepResult"
]

# データベース初期化関数
def init_db():
    """データベーススキーマを初期化する"""
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)