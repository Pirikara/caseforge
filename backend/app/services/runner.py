import httpx
import json
import os
from datetime import datetime, timezone
from app.services.teststore import list_testcases
from app.config import settings
from app.logging_config import logger
from typing import List, Dict, Any
from app.utils.path_manager import path_manager

async def run_tests(id: int) -> list[dict]:
    base_url = settings.TEST_TARGET_URL
    results = []
    
    try:
        tests = list_testcases(id)
        if not tests:
            logger.warning(f"No tests found for service {id}")
            return []
            
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        log_path = path_manager.get_log_dir(str(id))
        path_manager.ensure_dir(log_path)
    
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            for test in tests:
                try:
                    req = test.get("request", {})
                    expected = test.get("expected", {})
                    method = req.get("method", "GET")
                    path = req.get("path", "/")
                    json_body = req.get("body")
    
                    try:
                        response = await client.request(method, path, json=json_body)
                        result = {
                            "id": test.get("id"),
                            "title": test.get("title"),
                            "status": response.status_code,
                            "pass": response.status_code == expected.get("status")
                        }
                    except httpx.RequestError as e:
                        logger.error(f"Request error for test {test.get('id')}: {e}")
                        result = {
                            "id": test.get("id"),
                            "title": test.get("title"),
                            "error": f"Request error: {str(e)}",
                            "pass": False
                        }
                    except Exception as e:
                        logger.error(f"Unexpected error for test {test.get('id')}: {e}")
                        result = {
                            "id": test.get("id"),
                            "title": test.get("title"),
                            "error": str(e),
                            "pass": False
                        }
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing test {test.get('id')}: {e}")
                    results.append({
                        "id": test.get("id", "unknown"),
                        "title": test.get("title", "Unknown test"),
                        "error": f"Test processing error: {str(e)}",
                        "pass": False
                    })
    
        try:
            log_file = path_manager.join_path(log_path, f"{timestamp}.json")
            with open(log_file, "w") as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
            
    except Exception as e:
        logger.error(f"Error running tests for service {id}: {e}")
        return [{"error": f"Failed to run tests: {str(e)}"}]
        
    return results

def list_test_runs(id: int) -> list[str]:
    """
    サービスのテスト実行履歴を取得する
    
    Args:
        id: サービスID
        
    Returns:
        テスト実行IDのリスト（日時の降順）
    """
    try:
        path = path_manager.get_log_dir(str(id))
        if not path_manager.exists(path):
            return []
        runs = sorted(os.listdir(str(path)), reverse=True)
        return runs
    except Exception as e:
        logger.error(f"Error listing test runs for service {id}: {e}")
        return []

def get_run_result(id: int, run_id: str) -> list[dict] | None:
    """
    特定のテスト実行結果を取得する
    
    Args:
        id: サービスID
        run_id: テスト実行ID
        
    Returns:
        テスト実行結果。ファイルが存在しない場合はNone。
    """
    try:
        path = path_manager.get_log_dir(str(id), run_id)
        if not path_manager.exists(path):
            logger.warning(f"Test run log not found: {path}")
            return None
        with open(path, "r") as f:
            result = json.load(f)
            return result
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in test run log {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading test run log {path}: {e}")
        return None

def get_recent_runs(limit: int = 5) -> Dict[str, Any]:
    """
    全サービスの最近のテスト実行を取得する
    
    Args:
        limit: 取得する実行数の上限
        
    Returns:
        RecentTestRunsResponse スキーマに適合する辞書
    """
    
    all_runs = []
    total_runs = 0
    passed_runs = 0
    failed_runs = 0
    completed_runs = 0
    running_runs = 0

    log_dir = path_manager.get_log_dir()
    if not path_manager.exists(log_dir):
        logger.warning(f"Log directory not found: {log_dir}")
        return {
            "recent_runs": [],
            "total_runs": 0,
            "passed_runs": 0,
            "failed_runs": 0,
            "completed_runs": 0,
            "running_runs": 0,
        }

    services = [d for d in os.listdir(str(log_dir)) if path_manager.is_dir(path_manager.join_path(log_dir, d))]

    for service_id in services:
        service_path = path_manager.get_log_dir(service_id)
        run_files = [f for f in os.listdir(str(service_path)) if f.endswith('.json')]

        for run_file in run_files:
            run_id = run_file.replace('.json', '')
            run_path = path_manager.join_path(service_path, run_file)

            try:
                try:
                    name_parts = run_id.split('_')
                    start_time_str = name_parts[0]
                    start_time = datetime.strptime(start_time_str, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
                    suite_id = name_parts[1] if len(name_parts) > 1 else ""
                except ValueError:
                    start_time = datetime.fromtimestamp(os.path.getmtime(str(run_path)), tzinfo=timezone.utc)
                    suite_id = ""

                with open(run_path, 'r') as f:
                    results = json.load(f)

                status = "completed"
                is_failed = False
                if results:
                    if any(not r.get('pass', False) for r in results):
                        status = "failed"
                        is_failed = True

                total_runs += 1
                if status == "completed":
                    completed_runs += 1
                    if not is_failed:
                        passed_runs += 1
                    else:
                        failed_runs += 1

                all_runs.append({
                    "id": run_id,
                    "suite_id": suite_id,
                    "status": status,
                    "start_time": start_time,
                    "end_time": datetime.fromtimestamp(os.path.getmtime(str(run_path)), tz=timezone.utc),
                    "test_case_results": [],
                })
            except FileNotFoundError:
                 logger.warning(f"Run file not found (possibly deleted during scan): {run_path}")
                 continue
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in run file {run_path}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing run file {run_path}: {e}", exc_info=True)
                continue

    all_runs.sort(key=lambda x: x["start_time"], reverse=True)

    recent_runs = all_runs[:limit]

    return {
        "recent_runs": recent_runs,
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "completed_runs": completed_runs,
        "running_runs": running_runs,
    }
