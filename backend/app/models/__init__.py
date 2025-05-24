from .base import TimestampModel, get_session, engine
from .service import Service, Schema
from .test import TestSuite, TestCase, TestStep, TestRun, TestCaseResult, StepResult
from .endpoint import Endpoint
from .schema_chunk import SchemaChunk
from sqlalchemy import text

__all__ = [
    "TimestampModel", "get_session", "engine",
    "Service", "Schema", "SchemaChunk",
    "TestSuite", "TestCase", "TestStep",
    "TestRun", "TestCaseResult", "StepResult",
    "Endpoint"
]

def init_db():
    """データベーススキーマを初期化する"""
    from sqlmodel import SQLModel

    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector;")
        SQLModel.metadata.create_all(bind=conn)
