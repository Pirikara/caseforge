import pytest
from app.workers.tasks import generate_tests_task, generate_chains_task
from unittest.mock import patch, MagicMock

def test_generate_tests_task(mock_faiss, mock_llm, monkeypatch):
    # generate_chains_taskをモック化
    mock_generate_chains = MagicMock()
    mock_generate_chains.return_value = {"status": "completed", "count": 3}
    monkeypatch.setattr("app.workers.tasks.generate_chains_task", mock_generate_chains)
    
    # テスト実行
    result = generate_tests_task("test_project")
    
    # 検証
    assert "status" in result
    # 廃止予定の関数なので、generate_chains_taskが呼ばれたことを確認
    mock_generate_chains.assert_called_once_with("test_project")

def test_generate_chains_task(mock_faiss, mock_llm, monkeypatch):
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
            "name": "Chain 1",
            "steps": [
                {"method": "POST", "path": "/users"},
                {"method": "GET", "path": "/users/{id}"}
            ]
        }
    ]
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda project_id, schema: mock_rag)
    
    # ChainStoreをモック化
    mock_store = MagicMock()
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)
    
    # テスト実行
    result = generate_chains_task("test_project")
    
    # 検証
    assert "status" in result
    if result["status"] == "completed":
        assert result["count"] > 0
        # ChainStore.save_chainsが呼ばれたことを確認
        mock_store.save_chains.assert_called_once()
        args, kwargs = mock_store.save_chains.call_args
        assert args[0] == "test_project"
        assert isinstance(args[1], list)
    else:
        assert result["status"] == "error"
        assert "message" in result