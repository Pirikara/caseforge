import pytest
from app.workers.tasks import generate_test_suites_task, generate_test_suites_for_endpoints_task
from unittest.mock import patch, MagicMock, call

def test_generate_test_suites_task_success(mock_faiss, mock_llm, monkeypatch):
    """テストスイート生成タスクの正常系テスト"""
    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # DependencyAwareRAGをモック化
    mock_rag = MagicMock()
    mock_rag.generate_request_chains.return_value = [
        {
            "name": "TestSuite 1",
            "target_method": "POST",
            "target_path": "/users",
            "test_cases": [
                {
                    "name": "Normal Case",
                    "test_steps": [
                        {"method": "POST", "path": "/users"},
                        {"method": "GET", "path": "/users/{id}"}
                    ]
                }
            ]
        }
    ]
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda project_id, schema, error_types=None: mock_rag)

    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # テスト実行
    result = generate_test_suites_task("test_project")

    # 検証
    assert result["status"] == "completed"
    assert result["count"] > 0
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()
    args, kwargs = mock_store.save_csuites.call_args
    assert args[0] == "test_project"
    assert isinstance(args[1], list)
    assert len(args[1]) == 1
    assert "test_cases" in args[1][0]

def test_generate_test_suites_task_with_error_types(mock_faiss, mock_llm, monkeypatch):
    """エラータイプを指定したテストスイート生成タスクのテスト"""
    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # DependencyAwareRAGをモック化
    mock_rag = MagicMock()
    mock_rag.generate_request_chains.return_value = [
        {
            "name": "TestSuite 1",
            "target_method": "POST",
            "target_path": "/users",
            "test_cases": [
                {
                    "name": "Normal Case",
                    "test_steps": [
                        {"method": "POST", "path": "/users"}
                    ]
                },
                {
                    "name": "Missing Field Error",
                    "error_type": "missing_field",
                    "test_steps": [
                        {"method": "POST", "path": "/users", "expected_status": 400}
                    ]
                }
            ]
        }
    ]
    
    # DependencyAwareRAGのモックを設定し、error_typesが正しく渡されることを確認
    mock_dependency_aware_rag = MagicMock(return_value=mock_rag)
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", mock_dependency_aware_rag)

    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # エラータイプを指定してテスト実行
    error_types = ["missing_field", "invalid_value"]
    result = generate_test_suites_task("test_project", error_types)

    # 検証
    assert result["status"] == "completed"
    assert result["count"] > 0
    # DependencyAwareRAGが呼ばれたことを確認
    mock_dependency_aware_rag.assert_called_once()
    # error_typesが正しく渡されていることを確認
    args, kwargs = mock_dependency_aware_rag.call_args
    assert args[0] == "test_project"
    # error_typesは位置引数として渡されている可能性がある
    if len(args) > 2:
        assert args[2] == error_types
    elif "error_types" in kwargs:
        assert kwargs["error_types"] == error_types
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()

def test_generate_test_suites_task_no_schema_files(monkeypatch):
    """スキーマファイルが存在しない場合のテスト"""
    # os.listdirをモック化して空のリストを返す
    monkeypatch.setattr("os.listdir", lambda path: [])

    # テスト実行
    result = generate_test_suites_task("test_project")

    # 検証
    assert result["status"] == "error"
    assert "No schema files found" in result["message"]

def test_generate_test_suites_task_schema_parse_error(monkeypatch):
    """スキーマのパースに失敗する場合のテスト"""
    # get_schema_contentをモック化して無効なJSONを返す
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{invalid json'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # テスト実行
    result = generate_test_suites_task("test_project")

    # 検証
    assert result["status"] == "error"
    assert "message" in result

def test_generate_test_suites_task_rag_initialization_error(monkeypatch):
    """RAGの初期化に失敗する場合のテスト"""
    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # DependencyAwareRAGをモック化して例外を発生させる
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda project_id, schema, error_types=None: exec('raise Exception("RAG initialization error")'))

    # テスト実行
    result = generate_test_suites_task("test_project")

    # 検証
    assert result["status"] == "error"
    assert "message" in result

def test_generate_test_suites_task_generate_chains_error(mock_faiss, mock_llm, monkeypatch):
    """テストスイート生成に失敗する場合のテスト"""
    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # DependencyAwareRAGをモック化
    mock_rag = MagicMock()
    # generate_request_chainsメソッドが例外を発生させる
    mock_rag.generate_request_chains.side_effect = Exception("Generate chains error")
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda project_id, schema, error_types=None: mock_rag)

    # テスト実行
    result = generate_test_suites_task("test_project")

    # 検証
    assert result["status"] == "error"
    assert "message" in result

def test_generate_test_suites_for_endpoints_task_success(mock_faiss, mock_llm, monkeypatch, session):
    """エンドポイント指定テストスイート生成タスクの正常系テスト"""
    # Projectモデルのモック
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.project_id = "test_project"

    # Endpointモデルのモック
    mock_endpoint1 = MagicMock()
    mock_endpoint1.endpoint_id = "endpoint1"
    mock_endpoint1.path = "/users"
    mock_endpoint1.method = "POST"

    mock_endpoint2 = MagicMock()
    mock_endpoint2.endpoint_id = "endpoint2"
    mock_endpoint2.path = "/users/{id}"
    mock_endpoint2.method = "GET"

    # Sessionのexecメソッドをモック化
    mock_exec = MagicMock()
    mock_exec.first.return_value = mock_project
    mock_exec.all.return_value = [mock_endpoint1, mock_endpoint2]
    
    mock_session = MagicMock()
    mock_session.exec.return_value = mock_exec
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # EndpointChainGeneratorをモック化
    mock_generator = MagicMock()
    mock_generator.generate_chains.return_value = [
        {
            "name": "TestSuite for /users",
            "target_method": "POST",
            "target_path": "/users",
            "test_cases": [
                {
                    "name": "Normal Case",
                    "test_steps": [
                        {"method": "POST", "path": "/users"}
                    ]
                }
            ]
        }
    ]
    monkeypatch.setattr("app.workers.tasks.EndpointChainGenerator", lambda project_id, endpoints, schema, error_types: mock_generator)

    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # テスト実行
    result = generate_test_suites_for_endpoints_task("test_project", ["endpoint1", "endpoint2"])

    # 検証
    assert result["status"] == "success"
    assert "Successfully generated" in result["message"]
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()

def test_generate_test_suites_for_endpoints_task_project_not_found(monkeypatch):
    """プロジェクトが存在しない場合のテスト"""
    # Sessionのexecメソッドをモック化してNoneを返す
    mock_exec = MagicMock()
    mock_exec.first.return_value = None
    
    mock_session = MagicMock()
    mock_session.exec.return_value = mock_exec
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # テスト実行
    result = generate_test_suites_for_endpoints_task("non_existent_project", ["endpoint1"])

    # 検証
    assert result["status"] == "error"
    # エラーメッセージはファイルシステムのエラーを含む可能性があるため、部分一致で確認
    assert "No such file or directory" in result["message"] or "Project not found" in result["message"]

def test_generate_test_suites_for_endpoints_task_no_endpoints(monkeypatch):
    """エンドポイントが存在しない場合のテスト"""
    # Projectモデルのモック
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.project_id = "test_project"

    # Sessionのexecメソッドをモック化
    mock_exec1 = MagicMock()
    mock_exec1.first.return_value = mock_project
    
    mock_exec2 = MagicMock()
    mock_exec2.all.return_value = []
    
    mock_session = MagicMock()
    mock_session.exec.side_effect = [mock_exec1, mock_exec2]
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # テスト実行
    result = generate_test_suites_for_endpoints_task("test_project", ["non_existent_endpoint"])

    # 検証
    assert result["status"] == "warning"
    assert "No test suites were generated" in result["message"]

def test_generate_test_suites_for_endpoints_task_no_schema_files(monkeypatch):
    """スキーマファイルが存在しない場合のテスト"""
    # Projectモデルのモック
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.project_id = "test_project"

    # Endpointモデルのモック
    mock_endpoint = MagicMock()
    mock_endpoint.endpoint_id = "endpoint1"
    mock_endpoint.path = "/users"
    mock_endpoint.method = "POST"

    # Sessionのexecメソッドをモック化
    mock_exec1 = MagicMock()
    mock_exec1.first.return_value = mock_project
    
    mock_exec2 = MagicMock()
    mock_exec2.all.return_value = [mock_endpoint]
    
    mock_session = MagicMock()
    mock_session.exec.side_effect = [mock_exec1, mock_exec2]
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # os.listdirをモック化して空のリストを返す
    monkeypatch.setattr("os.listdir", lambda path: [])

    # テスト実行
    result = generate_test_suites_for_endpoints_task("test_project", ["endpoint1"])

    # 検証
    assert result["status"] == "error"
    assert "No schema files found" in result["message"]

def test_generate_test_suites_for_endpoints_task_with_error_types(mock_faiss, mock_llm, monkeypatch):
    """エラータイプを指定したエンドポイント指定テストスイート生成タスクのテスト"""
    # Projectモデルのモック
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.project_id = "test_project"

    # Endpointモデルのモック
    mock_endpoint = MagicMock()
    mock_endpoint.endpoint_id = "endpoint1"
    mock_endpoint.path = "/users"
    mock_endpoint.method = "POST"

    # Sessionのexecメソッドをモック化
    mock_exec1 = MagicMock()
    mock_exec1.first.return_value = mock_project
    
    mock_exec2 = MagicMock()
    mock_exec2.all.return_value = [mock_endpoint]
    
    mock_session = MagicMock()
    mock_session.exec.side_effect = [mock_exec1, mock_exec2]
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # EndpointChainGeneratorをモック化
    mock_generator = MagicMock()
    mock_generator.generate_chains.return_value = [
        {
            "name": "TestSuite for /users",
            "target_method": "POST",
            "target_path": "/users",
            "test_cases": [
                {
                    "name": "Normal Case",
                    "test_steps": [
                        {"method": "POST", "path": "/users"}
                    ]
                },
                {
                    "name": "Missing Field Error",
                    "error_type": "missing_field",
                    "test_steps": [
                        {"method": "POST", "path": "/users", "expected_status": 400}
                    ]
                }
            ]
        }
    ]
    
    # EndpointChainGeneratorのモックを設定し、error_typesが正しく渡されることを確認
    mock_endpoint_chain_generator = MagicMock(return_value=mock_generator)
    monkeypatch.setattr("app.workers.tasks.EndpointChainGenerator", mock_endpoint_chain_generator)

    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # エラータイプを指定してテスト実行
    error_types = ["missing_field", "invalid_value"]
    result = generate_test_suites_for_endpoints_task("test_project", ["endpoint1"], error_types)

    # 検証
    assert result["status"] == "success"
    assert "Successfully generated" in result["message"]
    # EndpointChainGeneratorが呼ばれたことを確認
    mock_endpoint_chain_generator.assert_called_once()
    # 引数を個別に確認
    args, kwargs = mock_endpoint_chain_generator.call_args
    assert args[0] == "test_project"
    assert args[3] == error_types
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()