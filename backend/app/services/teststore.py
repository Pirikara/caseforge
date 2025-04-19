import os
import json

TESTS_DIR = "/code/data/generated_tests"

def save_testcases(project_id: str, cases: list[dict]):
    os.makedirs(f"{TESTS_DIR}/{project_id}", exist_ok=True)
    with open(f"{TESTS_DIR}/{project_id}/tests.json", "w") as f:
        json.dump(cases, f, indent=2)

def list_testcases(project_id: str) -> list[dict]:
    path = f"{TESTS_DIR}/{project_id}/tests.json"
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)