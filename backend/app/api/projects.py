from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.schema import save_and_index_schema
from app.services.testgen import trigger_test_generation
from app.services.teststore import list_testcases
from app.services.runner import run_tests, list_test_runs, get_run_result
from app.workers.tasks import generate_tests_task
from fastapi.responses import JSONResponse
from pathlib import Path

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("/{project_id}/schema")
async def upload_schema(project_id: str, file: UploadFile = File(...)):
    if file.content_type not in ["application/json", "application/x-yaml", "text/yaml"]:
        raise HTTPException(status_code=400, detail="Invalid content type")
    contents = await file.read()
    save_and_index_schema(project_id, contents, file.filename)
    return {"message": "Schema uploaded and indexed successfully."}

@router.post("/{project_id}/generate-tests")
async def generate_tests(project_id: str):
    task_id = trigger_test_generation(project_id)
    return {"message": "Test generation started", "task_id": task_id}

@router.get("/{project_id}/tests")
async def get_generated_tests(project_id: str):
    tests = list_testcases(project_id)
    return JSONResponse(content=tests)

@router.post("/{project_id}/run")
async def run_project_tests(project_id: str):
    results = await run_tests(project_id)
    return {"message": "Test run complete", "results": results}

@router.get("/{project_id}/runs")
async def get_run_history(project_id: str):
    return list_test_runs(project_id)

@router.get("/{project_id}/runs/{run_id}")
async def get_run_detail(project_id: str, run_id: str):
    result = get_run_result(project_id, run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse(content=result)

@router.get("/")
async def list_projects():
    from app.services.schema import list_projects
    return list_projects()

@router.post("/")
async def create_project(project_id: str = Query(...)):
    path = Path(f"/code/data/schemas/{project_id}")
    if path.exists():
        raise HTTPException(status_code=409, detail="Project already exists")
    path.mkdir(parents=True, exist_ok=True)
    return {"status": "created", "project_id": project_id}

@router.post("/{project_id}/generate")
def deprecated_generate_tests(project_id: str):
    print(f"Generating tests for project {project_id}")
    generate_tests_task.delay(project_id)
    return {"status": "queued"}
