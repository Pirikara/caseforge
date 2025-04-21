import pytest
import os
from sqlmodel import SQLModel, create_engine, Session
from app.models import Project, Schema, TestCase, TestRun, TestResult
from app.config import settings

# テスト用のデータベースURL
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(name="engine")
def engine_fixture():
    """テスト用のSQLiteエンジンを作成"""
    engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    
    # SQLiteファイルを削除
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(name="session")
def session_fixture(engine):
    """テスト用のデータベースセッションを作成"""
    with Session(engine) as session:
        yield session

@pytest.fixture(name="test_project")
def test_project_fixture(session):
    """テスト用のプロジェクトを作成"""
    project = Project(project_id="test_project", name="Test Project")
    session.add(project)
    session.commit()
    session.refresh(project)
    return project

@pytest.fixture(name="test_schema")
def test_schema_fixture(session, test_project):
    """テスト用のスキーマを作成"""
    schema = Schema(
        project_id=test_project.id,
        filename="test.yaml",
        file_path="/tmp/test.yaml",
        content_type="application/x-yaml"
    )
    session.add(schema)
    session.commit()
    session.refresh(schema)
    return schema

@pytest.fixture(name="mock_chroma")
def mock_chroma_fixture(monkeypatch):
    """ChromaDBのモック"""
    class MockChroma:
        def __init__(self, *args, **kwargs):
            pass
            
        def as_retriever(self, *args, **kwargs):
            return self
            
        def invoke(self, *args, **kwargs):
            return [MockDocument()]
            
        def add_documents(self, *args, **kwargs):
            pass
            
        def persist(self):
            pass
    
    class MockDocument:
        def __init__(self):
            self.page_content = "test content"
    
    monkeypatch.setattr("langchain_community.vectorstores.Chroma", MockChroma)
    return MockChroma

@pytest.fixture(name="mock_llm")
def mock_llm_fixture(monkeypatch):
    """LLMのモック"""
    class MockLLM:
        def __init__(self, *args, **kwargs):
            pass
            
        def invoke(self, *args, **kwargs):
            class MockResponse:
                content = '[{"id": "test1", "title": "Test Case 1", "request": {"method": "GET", "path": "/api/test"}, "expected": {"status": 200}}]'
            return MockResponse()
    
    monkeypatch.setattr("langchain_openai.ChatOpenAI", MockLLM)
    return MockLLM