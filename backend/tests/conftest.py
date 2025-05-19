import pytest
import os
from sqlmodel import SQLModel, create_engine, Session

os.environ["TESTING"] = "1"

TEST_BASE_DIR = "/tmp/test_caseforge"
os.environ["SCHEMA_DIR"] = f"{TEST_BASE_DIR}/schemas"
os.environ["TESTS_DIR"] = f"{TEST_BASE_DIR}/generated_tests"
os.environ["LOG_DIR"] = f"{TEST_BASE_DIR}/test_runs"

import app.config
app.config.settings.SCHEMA_DIR = f"{TEST_BASE_DIR}/schemas"
app.config.settings.TESTS_DIR = f"{TEST_BASE_DIR}/generated_tests"
app.config.settings.LOG_DIR = f"{TEST_BASE_DIR}/test_runs"

os.makedirs("/tmp/test_caseforge", exist_ok=True)
os.makedirs("/tmp/test_caseforge/schemas", exist_ok=True)
os.makedirs("/tmp/test_caseforge/schemas/test_service", exist_ok=True)
os.makedirs("/tmp/test_caseforge/generated_tests", exist_ok=True)
os.makedirs("/tmp/test_caseforge/test_runs", exist_ok=True)

with open("/tmp/test_caseforge/schemas/test_service/test-schema.yaml", "w") as f:
    f.write("""
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
      responses:
        '200':
          description: OK
    post:
      summary: Create user
      responses:
        '201':
          description: Created
  /users/{id}:
    get:
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: OK
""")

import stat
os.chmod("/tmp/test_caseforge", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

from app.models import Service, Schema
from app.models.base import DATABASE_URL
from sqlmodel import SQLModel, create_engine

TEST_DB_PATH = "/tmp/test_caseforge/test.db"
DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

import app.models.base
app.models.base.engine = engine

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """テスト用データベースを初期化"""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    import app.models.base
    app.models.base.DATABASE_URL = DATABASE_URL
    app.models.base.engine = engine
    
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        from sqlalchemy import text
        session.exec(text("DELETE FROM stepresult"))
        session.exec(text("DELETE FROM testcaseresult"))
        session.exec(text("DELETE FROM testrun"))
        session.exec(text("DELETE FROM teststep"))
        session.exec(text("DELETE FROM testcase"))
        session.exec(text("DELETE FROM testsuite"))
        session.exec(text("DELETE FROM service"))
        session.commit()

        service = Service(service_id="test_service", name="Test Service")
        session.add(service)
        session.commit()
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture(name="engine")
def engine_fixture():
    """テスト用のSQLiteエンジンを返す"""
    yield engine

@pytest.fixture(autouse=True)
def reset_database(session):
    """各テスト後にデータベースをリセット"""
    from app.models import StepResult, TestCaseResult, TestRun, TestStep, TestCase, TestSuite
    from sqlmodel import delete
    from app.models import StepResult, TestCaseResult, TestRun, TestStep, TestCase, TestSuite
    
    session.exec(delete(StepResult))
    session.exec(delete(TestCaseResult))
    session.exec(delete(TestRun))
    session.exec(delete(TestStep))
    session.exec(delete(TestCase))
    session.exec(delete(TestSuite))
    
    session.commit()
    yield
    session.rollback()

@pytest.fixture(name="session")
def session_fixture():
    """テスト用のインメモリSQLiteデータベースセッションを作成"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="test_service")
def test_service_fixture(session):
    """テスト用のサービスを取得"""
    service_id = "test_service"
    
    service_dir = f"{TEST_BASE_DIR}/schemas/{service_id}"
    os.makedirs(service_dir, exist_ok=True)
    
    with open(f"{service_dir}/test-schema.yaml", "w") as f:
        f.write("""
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
      responses:
        '200':
          description: OK
    post:
      summary: Create user
      responses:
        '201':
          description: Created
""")

    from sqlmodel import select
    service = session.exec(select(Service).where(Service.service_id == service_id)).first()
    
    if not service:
        service = Service(service_id=service_id, name="Test Service")
        session.add(service)
        session.commit()
        session.refresh(service)
    
    return service

@pytest.fixture(name="test_schema")
def test_schema_fixture(session, test_service):
    """テスト用のスキーマを作成"""
    schema = Schema(
        service_id=test_service.id,
        filename="test.yaml",
        file_path="/tmp/test.yaml",
        content_type="application/x-yaml"
    )
    session.add(schema)
    session.commit()
    session.refresh(schema)
    return schema

@pytest.fixture(name="mock_faiss")
def mock_faiss_fixture(monkeypatch):
    """FAISSのモック"""
    class MockFAISS:
        def __init__(self, *args, **kwargs):
            pass
            
        @classmethod
        def from_documents(cls, documents, embedding):
            return cls()
        
        def similarity_search(self, query, k=1):
            class MockDocument:
                page_content = "test content"
            return [MockDocument()]
    
    monkeypatch.setattr("langchain_community.vectorstores.FAISS", MockFAISS)
    return MockFAISS

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

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_dirs():
    """テスト終了時に一時ディレクトリをクリーンアップする"""
    yield
    import shutil
    try:
        shutil.rmtree("/tmp/test_caseforge", ignore_errors=True)
    except Exception as e:
        print(f"Failed to cleanup test directories: {e}")
