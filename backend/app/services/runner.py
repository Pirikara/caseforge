import httpx
import json
import os
import logging
from datetime import datetime, timezone
from app.services.teststore import list_testcases
from app.config import settings
from app.logging_config import logger

async def run_tests(project_id: str) -> list[dict]:
    base_url = settings.TEST_TARGET_URL
    results = []
    
    try:
        tests = list_testcases(project_id)
        if not tests:
            logger.warning(f"No tests found for project {project_id}")
            return []
            
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        log_path = f"{settings.LOG_DIR}/{project_id}"
        os.makedirs(log_path, exist_ok=True)
    
        async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
            for test in tests:
                try:
                    req = test.get("request", {})
                    expected = test.get("expected", {})
                    method = req.get("method", "GET")
                    path = req.get("path", "/")
                    json_body = req.get("body")
    
                    try:
                        logger.debug(f"Running test {test.get('id')}: {method} {path}")
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
            with open(f"{log_path}/{timestamp}.json", "w") as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save test results: {e}")
            
    except Exception as e:
        logger.error(f"Error running tests for project {project_id}: {e}")
        return [{"error": f"Failed to run tests: {str(e)}"}]
        
    return results

def list_test_runs(project_id: str) -> list[str]:
    """
    プロジェクトのテスト実行履歴を取得する
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        テスト実行IDのリスト（日時の降順）
    """
    try:
        path = f"{settings.LOG_DIR}/{project_id}"
        if not os.path.exists(path):
            logger.debug(f"No test runs found for project {project_id}")
            return []
        runs = sorted(os.listdir(path), reverse=True)
        logger.debug(f"Found {len(runs)} test runs for project {project_id}")
        return runs
    except Exception as e:
        logger.error(f"Error listing test runs for project {project_id}: {e}")
        return []

def get_run_result(project_id: str, run_id: str) -> list[dict]:
    """
    特定のテスト実行結果を取得する
    
    Args:
        project_id: プロジェクトID
        run_id: テスト実行ID
        
    Returns:
        テスト実行結果。ファイルが存在しない場合はNone。
    """
    try:
        path = f"{settings.LOG_DIR}/{project_id}/{run_id}.json"
        if not os.path.exists(path):
            logger.warning(f"Test run log not found: {path}")
            return None
        with open(path, "r") as f:
            result = json.load(f)
            logger.debug(f"Loaded test results for project {project_id}, run {run_id}")
            return result
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in test run log {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading test run log {path}: {e}")
        return None

def get_recent_runs(limit: int = 5) -> dict:
    """
    全プロジェクトの最近のテスト実行を取得する
    
    Args:
        limit: 取得する実行数の上限
        
    Returns:
        最近のテスト実行と統計情報を含む辞書
    """
    try:
        # 統計情報の初期化
        stats = {
            "totalTests": 0,
            "totalRuns": 0,
            "successRate": 0
        }
        
        # すべてのプロジェクトディレクトリを取得
        log_dir = settings.LOG_DIR
        if not os.path.exists(log_dir):
            logger.warning(f"Log directory not found: {log_dir}")
            return {"runs": [], "stats": stats}
            
        projects = [d for d in os.listdir(log_dir) if os.path.isdir(os.path.join(log_dir, d))]
        logger.debug(f"Found {len(projects)} projects with test runs")
        
        # すべてのテスト実行を収集
        all_runs = []
        for project_id in projects:
            project_path = os.path.join(log_dir, project_id)
            run_files = [f for f in os.listdir(project_path) if f.endswith('.json')]
            
            for run_file in run_files:
                run_id = run_file.replace('.json', '')
                run_path = os.path.join(project_path, run_file)
                
                try:
                    # ファイルの最終更新時間を取得
                    mod_time = os.path.getmtime(run_path)
                    
                    # 実行結果を読み込む
                    with open(run_path, 'r') as f:
                        results = json.load(f)
                    
                    # 成功したテストの数を計算
                    passed_tests = sum(1 for r in results if r.get('pass', False))
                    total_tests = len(results)
                    
                    # 統計情報を更新
                    stats["totalTests"] += total_tests
                    stats["totalRuns"] += 1
                    
                    # 実行情報を追加
                    all_runs.append({
                        "run_id": run_id,
                        "project_id": project_id,
                        "status": "completed",
                        "start_time": datetime.fromtimestamp(mod_time).isoformat(),
                        "success_rate": round(passed_tests / total_tests * 100) if total_tests > 0 else 0
                    })
                except Exception as e:
                    logger.error(f"Error processing run file {run_path}: {e}")
        
        # 日時でソート
        all_runs.sort(key=lambda x: x["start_time"], reverse=True)
        
        # 上限数に制限
        recent_runs = all_runs[:limit]
        
        # 成功率を計算
        if stats["totalRuns"] > 0:
            success_tests = sum(1 for run in all_runs for r in get_run_result(run["project_id"], run["run_id"]) or [] if r.get('pass', False))
            total_tests = sum(len(get_run_result(run["project_id"], run["run_id"]) or []) for run in all_runs)
            stats["successRate"] = round(success_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "runs": recent_runs,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting recent runs: {e}")
        return {
            "runs": [],
            "stats": {
                "totalTests": 0,
                "totalRuns": 0,
                "successRate": 0
            }
        }