from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.schema import save_and_index_schema

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/{project_id}/schema")
async def upload_schema(project_id: str, file: UploadFile = File(...)):
    if file.content_type not in ["application/json", "application/x-yaml", "text/yaml"]:
        raise HTTPException(status_code=400, detail="Invalid content type")

    contents = await file.read()
    await save_and_index_schema(project_id, contents, file.filename)
    return {"message": "Schema uploaded and indexed successfully."}