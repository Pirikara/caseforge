from app.logging_config import logger
from typing import Optional, List

def trigger_test_generation(service_id: int, error_types: Optional[List[str]] = None) -> Optional[str]:
    """
    テスト生成タスクを非同期で実行する
    
    Args:
        service_id: サービスID
        error_types: 生成するエラーケースのタイプ（オプション）
        
    Returns:
        タスクID。エラー時はNone。
    """
    try:
        from app.workers.tasks import generate_test_suites_task
        
        logger.info(f"Triggering test generation task for service {service_id}")
        result = generate_test_suites_task.delay(service_id, error_types)
        task_id = result.id
        logger.info(f"Test generation task started with ID: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"Error triggering test generation for service {service_id}: {e}")
        return None
