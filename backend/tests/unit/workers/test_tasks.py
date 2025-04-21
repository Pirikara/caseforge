import pytest
from app.workers.tasks import generate_tests_task
from unittest.mock import patch, MagicMock

def test_generate_tests_task(mock_chroma, mock_llm, monkeypatch):
    # save_testcasesをモック化
    mock_save = MagicMock()
    monkeypatch.setattr("app.workers.tasks.save_testcases", mock_save)
    
    # テスト実行
    result = generate_tests_task("test_project")
    
    # 検証
    assert result["status"] == "completed"
    assert result["count"] > 0
    
    # save_testcasesが呼ばれたことを確認
    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert args[0] == "test_project"
    assert isinstance(args[1], list)