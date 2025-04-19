from app.workers import celery_app
from app.services.teststore import save_testcases
import time

@celery_app.task
def generate_tests_task(project_id: str):
    # 仮のダミー処理（後で LLM 呼び出しとテスト JSON 化に置換）
    print(f"Generating tests for project {project_id}...")
    time.sleep(3)
    print("Done.")
    return {"status": "completed"}

@celery_app.task
def generate_tests_task(project_id: str):
    # 仮のテストケース（後で LLM に置換）
    dummy_tests = [
        {"id": "test_001", "title": "GET /pets returns 200", "request": {"method": "GET", "path": "/pets"}, "expected": {"status": 200}},
        {"id": "test_002", "title": "POST /pets validates input", "request": {"method": "POST", "path": "/pets", "body": {"name": 123}}, "expected": {"status": 422}}
    ]
    save_testcases(project_id, dummy_tests)
    return {"status": "completed", "count": len(dummy_tests)}