import os
import json
from typing import List, Dict, Any
from app.config import settings
from app.logging_config import logger
from app.utils.path_manager import path_manager

def save_testcases(project_id: str, cases: List[Dict[str, Any]]) -> None:
    """
    テストケースをJSONファイルに保存する
    
    Args:
        project_id: プロジェクトID
        cases: 保存するテストケースのリスト
    """
    try:
        tests_dir = path_manager.get_tests_dir(project_id)
        path_manager.ensure_dir(tests_dir)
        tests_file = path_manager.join_path(tests_dir, "tests.json")
        with open(tests_file, "w") as f:
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
        path = path_manager.join_path(path_manager.get_tests_dir(project_id), "tests.json")
        if not path_manager.exists(path):
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