from unittest.mock import patch, MagicMock
from app.services.testgen import trigger_test_generation

def test_trigger_test_generation_success():
    """テスト生成タスクの正常系テスト"""
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    
    with patch("app.workers.tasks.generate_test_suites_task") as mock_generate:
        mock_generate.delay.return_value = mock_task
        
        task_id = trigger_test_generation("test-service")
        
        assert task_id == "test-task-id"
        mock_generate.delay.assert_called_once_with("test-service", None)

def test_trigger_test_generation_with_error_types():
    """エラータイプを指定したテスト生成タスクのテスト"""
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    
    with patch("app.workers.tasks.generate_test_suites_task") as mock_generate:
        mock_generate.delay.return_value = mock_task
        
        error_types = ["missing_field", "invalid_value"]
        task_id = trigger_test_generation("test-service", error_types)
        
        assert task_id == "test-task-id"
        mock_generate.delay.assert_called_once_with("test-service", error_types)

def test_trigger_test_generation_error():
    """テスト生成タスクのエラー系テスト"""
    with patch("app.workers.tasks.generate_test_suites_task") as mock_generate:
        mock_generate.delay.side_effect = Exception("Test error")
        
        task_id = trigger_test_generation("test-service")
        
        assert task_id is None
        mock_generate.delay.assert_called_once_with("test-service", None)

def test_circular_import_prevention():
    """循環インポートが発生しないことを確認するテスト"""
    import app.services.testgen
    import app.workers.tasks
    
    assert hasattr(app.services.testgen, "trigger_test_generation")
    assert hasattr(app.workers.tasks, "generate_test_suites_task")
