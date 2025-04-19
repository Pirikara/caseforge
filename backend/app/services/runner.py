import httpx
import json
import os
from datetime import datetime
from app.services.teststore import list_testcases

LOG_DIR = "/code/data/test_runs"

async def run_tests(project_id: str) -> list[dict]:
    base_url = "http://backend:8000"
    results = []
    tests = list_testcases(project_id)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_path = f"{LOG_DIR}/{project_id}"
    os.makedirs(log_path, exist_ok=True)

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for test in tests:
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
            except Exception as e:
                result = {
                    "id": test.get("id"),
                    "title": test.get("title"),
                    "error": str(e),
                    "pass": False
                }
            results.append(result)

    with open(f"{log_path}/{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)

    return results

def list_test_runs(project_id: str) -> list[str]:
    path = f"{LOG_DIR}/{project_id}"
    if not os.path.exists(path):
        return []
    return sorted(os.listdir(path), reverse=True)

def get_run_result(project_id: str, run_id: str) -> list[dict]:
    path = f"{LOG_DIR}/{project_id}/{run_id}.json"
    if not os.path.exists(path):
        return [{"error": "Log not found", "run_id": run_id}]
    with open(path, "r") as f:
        return json.load(f)