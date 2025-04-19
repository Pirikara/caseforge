from app.workers import celery_app
import time

@celery_app.task
def generate_tests_task(project_id: str):
    # 仮のダミー処理（後で LLM 呼び出しとテスト JSON 化に置換）
    print(f"Generating tests for project {project_id}...")
    time.sleep(3)
    print("Done.")
    return {"status": "completed"}