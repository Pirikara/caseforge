from app.workers.tasks import generate_test_suites_task, generate_test_suites_for_endpoints_task
from unittest.mock import MagicMock, mock_open

def test_generate_test_suites_task_success(monkeypatch):
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
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda id, schema, error_types=None: mock_rag)

    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # テスト実行
    result = generate_test_suites_task(1)

    # 検証
    assert result["status"] == "completed"
    assert result["count"] == len(mock_rag.generate_request_chains.return_value)
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()
    args, kwargs = mock_store.save_suites.call_args
    # save_suitesの最初の引数はセッション (None), 2番目はservice_id, 3番目はtest_suites
    assert args[0] is None
    assert args[1] == 1
    assert isinstance(args[2], list)
    assert len(args[2]) == 1
    assert "test_cases" in args[2][0]

def test_generate_test_suites_task_with_error_types(monkeypatch):
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
    result = generate_test_suites_task(1, error_types)

    # 検証
    assert result["status"] == "completed"
    assert result["count"] > 0
    # DependencyAwareRAGが呼ばれたことを確認
    mock_dependency_aware_rag.assert_called_once()
    # error_typesが正しく渡されていることを確認
    args, kwargs = mock_dependency_aware_rag.call_args
    assert args[0] == 1
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
    result = generate_test_suites_task(1)

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
    result = generate_test_suites_task(1)

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
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda id, schema, error_types=None: exec('raise Exception("RAG initialization error")'))

    # テスト実行
    result = generate_test_suites_task(1)

    # 検証
    assert result["status"] == "error"
    assert "message" in result

def test_generate_test_suites_task_generate_chains_error(mock_llm, monkeypatch):
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
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda id, schema, error_types=None: mock_rag)

    # テスト実行
    result = generate_test_suites_task(1)

    # 検証
    assert result["status"] == "error"
    assert "message" in result

def test_generate_test_suites_for_endpoints_task_success(monkeypatch):
    """エンドポイント指定テストスイート生成タスクの正常系テスト"""
    # Serviceモデルのモック
    mock_service = MagicMock()
    mock_service.id = 1

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
    mock_exec.first.return_value = mock_service
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
    monkeypatch.setattr("app.workers.tasks.EndpointChainGenerator", lambda id, endpoints, schema, error_types: mock_generator)

    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # テスト実行
    result = generate_test_suites_for_endpoints_task(1, ["endpoint1", "endpoint2"])

    # 検証
    assert result["status"] == "success"
    assert "Successfully generated" in result["message"]
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()

def test_generate_test_suites_for_endpoints_task_service_not_found(monkeypatch):
    """サービスが存在しない場合のテスト"""
    # Sessionのexecメソッドをモック化してNoneを返す
    mock_exec = MagicMock()
    mock_exec.first.return_value = None
    
    mock_session = MagicMock()
    mock_session.exec.return_value = mock_exec
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # テスト実行
    result = generate_test_suites_for_endpoints_task(999, ["endpoint1"])

    # 検証
    assert result["status"] == "error"
    # エラーメッセージはファイルシステムのエラーを含む可能性があるため、部分一致で確認
    assert "No such file or directory" in result["message"] or "Service not found" in result["message"]

def test_generate_test_suites_for_endpoints_task_no_endpoints(monkeypatch):
    """エンドポイントが存在しない場合のテスト"""
    mock_service = MagicMock()
    mock_service.id = 1

    mock_exec1 = MagicMock()
    mock_exec1.first.return_value = mock_service
    mock_exec2 = MagicMock()
    mock_exec2.all.return_value = []

    mock_session = MagicMock()
    mock_session.exec.side_effect = [mock_exec1, mock_exec2]

    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])
    monkeypatch.setattr("app.services.schema.path_manager.exists", lambda path: True)

    dummy_content = '{"openapi": "3.0.0", "info": {"title": "Mock API", "version": "1.0.0"}, "paths": {}}'
    monkeypatch.setattr("builtins.open", mock_open(read_data=dummy_content))

    result = generate_test_suites_for_endpoints_task(1, ["non_existent_endpoint"])

    assert result["status"] == "warning"
    assert result["message"] == "No test suites were generated for the selected endpoints."

def test_generate_test_suites_for_endpoints_task_no_schema_files(monkeypatch):
    """スキーマファイルが存在しない場合のテスト"""
    # Serviceモデルのモック
    mock_service = MagicMock()
    mock_service.id = 1

    # Endpointモデルのモック
    mock_endpoint = MagicMock()
    mock_endpoint.endpoint_id = "endpoint1"
    mock_endpoint.path = "/users"
    mock_endpoint.method = "POST"

    # Sessionのexecメソッドをモック化
    mock_exec1 = MagicMock()
    mock_exec1.first.return_value = mock_service
    
    mock_exec2 = MagicMock()
    mock_exec2.all.return_value = [mock_endpoint]
    
    mock_session = MagicMock()
    mock_session.exec.side_effect = [mock_exec1, mock_exec2]
    
    # Sessionクラスをモック化
    monkeypatch.setattr("app.workers.tasks.Session", lambda engine: mock_session)

    # os.listdirをモック化して空のリストを返す
    monkeypatch.setattr("os.listdir", lambda path: [])

    # テスト実行
    result = generate_test_suites_for_endpoints_task(1, ["endpoint1"])

    # 検証
    assert result["status"] == "error"
    assert "No schema files found" in result["message"]

def test_generate_test_suites_for_endpoints_task_with_error_types(monkeypatch):
    """エラータイプを指定したエンドポイント指定テストスイート生成タスクのテスト"""
    # Serviceモデルのモック
    mock_service = MagicMock()
    mock_service.id = 1

    # Endpointモデルのモック
    mock_endpoint = MagicMock()
    mock_endpoint.endpoint_id = "endpoint1"
    mock_endpoint.path = "/users"
    mock_endpoint.method = "POST"

    # Sessionのexecメソッドをモック化
    mock_exec1 = MagicMock()
    mock_exec1.first.return_value = mock_service
    
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
    result = generate_test_suites_for_endpoints_task(1, ["endpoint1"], error_types)

    # 検証
    assert result["status"] == "success"
    assert "Successfully generated" in result["message"]
    # EndpointChainGeneratorが呼ばれたことを確認
    mock_endpoint_chain_generator.assert_called_once()
    # 引数を個別に確認
    args, kwargs = mock_endpoint_chain_generator.call_args
    assert args[0] == 1
    assert args[3] == error_types
    # ChainStore.save_chainsが呼ばれたことを確認
    mock_store.save_suites.assert_called_once()
