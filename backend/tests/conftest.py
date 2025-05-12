import pytest
import os
from sqlmodel import SQLModel, create_engine, Session

# テスト環境であることを示す環境変数を設定
os.environ["TESTING"] = "1"

# テスト用のディレクトリパスを設定
TEST_BASE_DIR = "/tmp/test_caseforge"
os.environ["SCHEMA_DIR"] = f"{TEST_BASE_DIR}/schemas"
os.environ["TESTS_DIR"] = f"{TEST_BASE_DIR}/generated_tests"
os.environ["LOG_DIR"] = f"{TEST_BASE_DIR}/test_runs"

# アプリケーション設定を上書き
import app.config
app.config.settings.SCHEMA_DIR = f"{TEST_BASE_DIR}/schemas"
app.config.settings.TESTS_DIR = f"{TEST_BASE_DIR}/generated_tests"
app.config.settings.LOG_DIR = f"{TEST_BASE_DIR}/test_runs"

# テスト用のベースディレクトリを作成
os.makedirs("/tmp/test_caseforge", exist_ok=True)

# テスト用ディレクトリを作成
os.makedirs("/tmp/test_caseforge/schemas", exist_ok=True)
os.makedirs("/tmp/test_caseforge/schemas/test_project", exist_ok=True)  # テスト用プロジェクトディレクトリ
os.makedirs("/tmp/test_caseforge/generated_tests", exist_ok=True)
os.makedirs("/tmp/test_caseforge/test_runs", exist_ok=True)

# テスト用のスキーマファイルを作成
with open("/tmp/test_caseforge/schemas/test_project/test-schema.yaml", "w") as f:
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

# データベースディレクトリの権限を確認
import stat
os.chmod("/tmp/test_caseforge", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

# モデルのインポートは環境変数設定後に行う
from app.models import Project, Schema, TestRun, TestCaseResult, TestSuite, TestStep
from app.models.base import DATABASE_URL
from sqlmodel import SQLModel

# テスト用のSQLiteデータベースファイルを使用
from sqlmodel import create_engine
TEST_DB_PATH = "/tmp/test_caseforge/test.db"
DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# app.models.base のエンジンを上書き
# 注意: app.models.base.py でも同じパスを使用するように修正済み
import app.models.base
app.models.base.engine = engine

# テスト開始前にデータベースを初期化
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """テスト用データベースを初期化"""
    # データベースファイルが存在する場合は削除
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    # app.models.base のエンジンを確実に上書き
    import app.models.base
    app.models.base.DATABASE_URL = DATABASE_URL
    app.models.base.engine = engine
    
    # テーブルを作成
    SQLModel.metadata.create_all(engine)
    
    # 固定のテストプロジェクトを作成（全テストで共有）
    with Session(engine) as session:
        # 既存のプロジェクトをクリア
        from sqlalchemy import text
        # 関連テーブルのデータをクリア
        session.exec(text("DELETE FROM stepresult"))
        session.exec(text("DELETE FROM testcaseresult"))
        session.exec(text("DELETE FROM testrun"))
        session.exec(text("DELETE FROM teststep"))
        session.exec(text("DELETE FROM testcase"))
        session.exec(text("DELETE FROM testsuite"))
        # project テーブルをクリア
        session.exec(text("DELETE FROM project"))
        session.commit()

        # 固定のプロジェクトを作成
        project = Project(project_id="test_project", name="Test Project")
        session.add(project)
        session.commit()
    
    yield
    
    # テスト終了後にデータベースファイルを削除
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture(name="engine")
def engine_fixture():
    """テスト用のSQLiteエンジンを返す"""
    # グローバルエンジンを使用
    yield engine

@pytest.fixture(autouse=True)
def reset_database(session):
    """各テスト後にデータベースをリセット"""
    # テスト開始前にテーブルをクリア（projectテーブルは除外）
    # 依存関係の深いテーブルから順に削除
    # ORMを使用してデータを削除
    from app.models import StepResult, TestCaseResult, TestRun, TestStep, TestCase, TestSuite
    
    # 依存関係の深いテーブルから順に削除
    # SQLModel の推奨する方法である session.exec(delete(...)) を使用
    from sqlmodel import delete
    from app.models import StepResult, TestCaseResult, TestRun, TestStep, TestCase, TestSuite
    
    session.exec(delete(StepResult))
    session.exec(delete(TestCaseResult))
    session.exec(delete(TestRun))
    session.exec(delete(TestStep))
    session.exec(delete(TestCase))
    session.exec(delete(TestSuite))
    
    session.commit() # ここでコミットが必要

    yield
    # テスト後にセッションをロールバック
    session.rollback()

@pytest.fixture(name="session")
def session_fixture():
    """テスト用のインメモリSQLiteデータベースセッションを作成"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    # インメモリデータベースはセッション終了時に自動的に破棄される

@pytest.fixture(name="test_project")
def test_project_fixture(session):
    """テスト用のプロジェクトを取得"""
    # 固定のプロジェクトIDを使用
    project_id = "test_project"
    
    # プロジェクトディレクトリを作成
    project_dir = f"{TEST_BASE_DIR}/schemas/{project_id}"
    os.makedirs(project_dir, exist_ok=True)
    
    # テスト用のスキーマファイルを作成
    with open(f"{project_dir}/test-schema.yaml", "w") as f:
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
    
    # 既存のプロジェクトを取得
    from sqlmodel import select
    project = session.exec(select(Project).where(Project.project_id == project_id)).first()
    
    # プロジェクトが存在しない場合は作成（通常はsetup_databaseで作成済み）
    if not project:
        project = Project(project_id=project_id, name="Test Project")
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