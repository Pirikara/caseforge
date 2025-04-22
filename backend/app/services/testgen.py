from app.workers.tasks import generate_tests_task
from app.logging_config import logger
from typing import Optional

def trigger_test_generation(project_id: str) -> Optional[str]:
    """
    テスト生成タスクを非同期で実行する
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        タスクID。エラー時はNone。
    """
    try:
        logger.info(f"Triggering test generation task for project {project_id}")
        result = generate_tests_task.delay(project_id)
        task_id = result.id
        logger.info(f"Test generation task started with ID: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"Error triggering test generation for project {project_id}: {e}")
        return None