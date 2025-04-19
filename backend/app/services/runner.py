import httpx
from app.services.teststore import list_testcases

async def run_tests(project_id: str) -> list[dict]:
    base_url = "http://backend:8000"  # API テスト対象のベースURL（本番では外部URLに）
    results = []
    tests = list_testcases(project_id)

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

    return results