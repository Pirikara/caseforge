import httpx
import json
import os
from datetime import datetime, timezone
from app.services.teststore import list_testcases
from app.config import settings
from app.logging_config import logger
from typing import List, Dict, Any

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

def get_run_result(project_id: str, run_id: str) -> list[dict] | None:
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

def get_recent_runs(limit: int = 5) -> Dict[str, Any]:
    """
    全プロジェクトの最近のテスト実行を取得する
    
    Args:
        limit: 取得する実行数の上限
        
    Returns:
        RecentTestRunsResponse スキーマに適合する辞書
    """
    logger.info(f"Fetching recent test runs with limit {limit}")
    
    all_runs = []
    total_runs = 0
    passed_runs = 0
    failed_runs = 0
    completed_runs = 0
    running_runs = 0 # 現在のログファイル構造では正確なrunningは判定困難だが、スキーマに合わせて追加

    log_dir = settings.LOG_DIR
    if not os.path.exists(log_dir):
        logger.warning(f"Log directory not found: {log_dir}")
        return {
            "recent_runs": [],
            "total_runs": 0,
            "passed_runs": 0,
            "failed_runs": 0,
            "completed_runs": 0,
            "running_runs": 0,
        }

    projects = [d for d in os.listdir(log_dir) if os.path.isdir(os.path.join(log_dir, d))]
    logger.debug(f"Found {len(projects)} projects with test runs logs")

    for project_id in projects:
        project_path = os.path.join(log_dir, project_id)
        run_files = [f for f in os.listdir(project_path) if f.endswith('.json')]

        for run_file in run_files:
            run_id = run_file.replace('.json', '')
            run_path = os.path.join(project_path, run_file)

            try:
                # ファイル名から開始時間を推測 (YYYYMMDD-HHMMSS 形式を想定)
                try:
                    # ファイル名が "YYYYMMDD-HHMMSS.json" または "YYYYMMDD-HHMMSS_suiteId.json" の形式を想定
                    name_parts = run_id.split('_')
                    start_time_str = name_parts[0]
                    start_time = datetime.strptime(start_time_str, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
                    suite_id = name_parts[1] if len(name_parts) > 1 else "" # None の代わりに空文字列を割り当てる
                except ValueError:
                    # ファイル名から取得できない場合はファイルの更新時間を使用
                    start_time = datetime.fromtimestamp(os.path.getmtime(run_path), tzinfo=timezone.utc)
                    suite_id = "" # suite_idも不明とする場合は空文字列

                # 実行結果を読み込む
                with open(run_path, 'r') as f:
                    results = json.load(f)

                # ステータスと成功/失敗を判定
                # ログファイルに直接ステータス情報がないため、結果から推測
                # 1つでも失敗があればfailed、そうでなければcompletedと仮定
                status = "completed"
                is_failed = False
                if results:
                    if any(not r.get('pass', False) for r in results):
                        status = "failed"
                        is_failed = True
                # 結果が空の場合はcompleted (テストケースが0件だった可能性) とみなす

                # 統計情報を更新
                total_runs += 1
                if status == "completed":
                    completed_runs += 1
                    if not is_failed:
                        passed_runs += 1
                    else:
                        failed_runs += 1
                # running_runs は現在のログ構造では正確に判定できないため、常に0とする

                # 実行情報を追加
                all_runs.append({
                    "id": run_id, # run_id を id に変更
                    "suite_id": suite_id,
                    "status": status,
                    "start_time": start_time, # isoformat() を削除
                    "end_time": datetime.fromtimestamp(os.path.getmtime(run_path), tz=timezone.utc), # isoformat() を削除
                    "test_case_results": [], # TestRun スキーマに合わせて追加 (空リスト)
                })
            except FileNotFoundError:
                 logger.warning(f"Run file not found (possibly deleted during scan): {run_path}")
                 continue # ファイルが見つからない場合はスキップ
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in run file {run_path}: {e}")
                # JSONエラーが発生した実行は失敗とみなし、統計に含めることも検討
                # ここでは一旦スキップ
                continue
            except Exception as e:
                logger.error(f"Error processing run file {run_path}: {e}", exc_info=True)
                # その他のエラーが発生した実行もスキップ
                continue

    # 日時でソート
    all_runs.sort(key=lambda x: x["start_time"], reverse=True)

    # 上限数に制限
    recent_runs = all_runs[:limit]

    # RecentTestRunsResponse スキーマに適合する形式で返す
    return {
        "recent_runs": recent_runs,
        "total_runs": total_runs,
        "passed_runs": passed_runs,
        "failed_runs": failed_runs,
        "completed_runs": completed_runs,
        "running_runs": running_runs, # 現在は常に0
    }