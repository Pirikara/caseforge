from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.schema import save_and_index_schema
from app.services.testgen import trigger_test_generation

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/{project_id}/schema")
async def upload_schema(project_id: str, file: UploadFile = File(...)):
    if file.content_type not in ["application/json", "application/x-yaml", "text/yaml"]:
        raise HTTPException(status_code=400, detail="Invalid content type")

    contents = await file.read()
    await save_and_index_schema(project_id, contents, file.filename)
    return {"message": "Schema uploaded and indexed successfully."}

@router.post("/{project_id}/generate-tests")
async def generate_tests(project_id: str):
    task_id = trigger_test_generation(project_id)
    return {"message": "Test generation started", "task_id": task_id}