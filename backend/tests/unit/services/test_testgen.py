import pytest
from unittest.mock import patch, MagicMock
from app.services.testgen import trigger_test_generation

def test_trigger_test_generation_success():
    """テスト生成タスクの正常系テスト"""
    # generate_test_suites_task.delayをモック化
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    
    with patch("app.workers.tasks.generate_test_suites_task") as mock_generate:
        mock_generate.delay.return_value = mock_task
        
        # テスト実行
        task_id = trigger_test_generation("test-project")
        
        # 検証
        assert task_id == "test-task-id"
        mock_generate.delay.assert_called_once_with("test-project", None)

def test_trigger_test_generation_with_error_types():
    """エラータイプを指定したテスト生成タスクのテスト"""
    # generate_test_suites_task.delayをモック化
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    
    with patch("app.workers.tasks.generate_test_suites_task") as mock_generate:
        mock_generate.delay.return_value = mock_task
        
        # エラータイプを指定してテスト実行
        error_types = ["missing_field", "invalid_value"]
        task_id = trigger_test_generation("test-project", error_types)
        
        # 検証
        assert task_id == "test-task-id"
        mock_generate.delay.assert_called_once_with("test-project", error_types)

def test_trigger_test_generation_error():
    """テスト生成タスクのエラー系テスト"""
    with patch("app.workers.tasks.generate_test_suites_task") as mock_generate:
        # 例外を発生させる
        mock_generate.delay.side_effect = Exception("Test error")
        
        # テスト実行
        task_id = trigger_test_generation("test-project")
        
        # 検証
        assert task_id is None
        mock_generate.delay.assert_called_once_with("test-project", None)

def test_circular_import_prevention():
    """循環インポートが発生しないことを確認するテスト"""
    # このテストは実際には何も実行しませんが、
    # テストが実行できること自体が循環インポートが解決されていることの証明になります
    
    # app.services.testgenとapp.workers.tasksの両方をインポート
    import app.services.testgen
    import app.workers.tasks
    
    # 両方のモジュールが正常にインポートできることを確認
    assert hasattr(app.services.testgen, "trigger_test_generation")
    assert hasattr(app.workers.tasks, "generate_test_suites_task")