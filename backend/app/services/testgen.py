from app.workers.tasks import generate_tests_task

def trigger_test_generation(project_id: str) -> str:
    result = generate_tests_task.delay(project_id)
    return result.id