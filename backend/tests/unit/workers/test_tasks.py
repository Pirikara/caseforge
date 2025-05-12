import pytest
from app.workers.tasks import generate_test_suites_task # generate_chains_task を generate_test_suites_task に変更
from unittest.mock import patch, MagicMock

def test_generate_test_suites_task(mock_faiss, mock_llm, monkeypatch): # test_generate_chains_task を test_generate_test_suites_task に変更
    # get_schema_contentをモック化
    mock_get_schema = MagicMock()
    mock_get_schema.return_value = '{"openapi": "3.0.0", "paths": {"/users": {"post": {}}}}'
    monkeypatch.setattr("app.workers.tasks.get_schema_content", mock_get_schema)

    # os.listdirをモック化
    monkeypatch.setattr("os.listdir", lambda path: ["test.json"])

    # DependencyAwareRAGをモック化
    mock_rag = MagicMock()
    mock_rag.generate_request_chains.return_value = [ # generate_request_chains はそのまま
        {
            "name": "TestSuite 1", # Chain 1 を TestSuite 1 に変更
            "target_method": "POST", # target_method を追加
            "target_path": "/users", # target_path を追加
            "test_cases": [ # steps を test_cases に変更
                {
                    "name": "Normal Case", # 名前の変更
                    "test_steps": [ # steps を test_steps に変更
                        {"method": "POST", "path": "/users"},
                        {"method": "GET", "path": "/users/{id}"}
                    ]
                }
            ]
        }
    ]
    monkeypatch.setattr("app.workers.tasks.DependencyAwareRAG", lambda project_id, schema: mock_rag)

    # ChainStoreをモック化
    mock_store = MagicMock() # ChainStore の名前はそのまま
    monkeypatch.setattr("app.workers.tasks.ChainStore", lambda: mock_store)

    # テスト実行
    result = generate_test_suites_task("test_project") # generate_chains_task を generate_test_suites_task に変更

    # 検証
    assert "status" in result
    if result["status"] == "completed":
        assert result["count"] > 0
        # ChainStore.save_chainsが呼ばれたことを確認
        mock_store.save_chains.assert_called_once() # save_chains はそのまま
        args, kwargs = mock_store.save_chains.call_args
        assert args[0] == "test_project"
        assert isinstance(args[1], list)
        assert len(args[1]) == 1 # 生成されたテストスイートの数を確認
        assert "test_cases" in args[1][0] # test_cases キーが存在することを確認
    else:
        assert result["status"] == "error"
        assert "message" in result