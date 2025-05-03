import os
import json
from typing import List, Dict, Any
from app.config import settings
from app.logging_config import logger

def save_testcases(project_id: str, cases: List[Dict[str, Any]]) -> None:
    """
    テストケースをJSONファイルに保存する
    
    Args:
        project_id: プロジェクトID
        cases: 保存するテストケースのリスト
    """
    try:
        os.makedirs(f"{settings.TESTS_DIR}/{project_id}", exist_ok=True)
        with open(f"{settings.TESTS_DIR}/{project_id}/tests.json", "w") as f:
            json.dump(cases, f, indent=2)
        logger.info(f"Saved {len(cases)} test cases for project {project_id}")
    except Exception as e:
        logger.error(f"Error saving test cases for project {project_id}: {e}")
        raise

def list_testcases(project_id: str) -> List[Dict[str, Any]]:
    """
    プロジェクトのテストケースを取得する
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        テストケースのリスト。ファイルが存在しない場合は空リスト。
    """
    try:
        path = f"{settings.TESTS_DIR}/{project_id}/tests.json"
        if not os.path.exists(path):
            logger.debug(f"No test cases found for project {project_id}")
            return []
        with open(path, "r") as f:
            cases = json.load(f)
            logger.debug(f"Loaded {len(cases)} test cases for project {project_id}")
            return cases
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in test cases file for project {project_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading test cases for project {project_id}: {e}")
        return []