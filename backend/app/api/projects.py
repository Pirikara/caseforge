from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.schema import save_and_index_schema
from app.services.testgen import trigger_test_generation
from app.services.teststore import list_testcases
from app.services.runner import run_tests, list_test_runs, get_run_result, get_recent_runs
from app.workers.tasks import generate_tests_task
from fastapi.responses import JSONResponse
from pathlib import Path
from app.config import settings
from app.logging_config import logger
from app.schemas.project import ProjectCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("/{project_id}/schema")
async def upload_schema(project_id: str, file: UploadFile = File(...)):
    logger.info(f"Uploading schema for project {project_id}: {file.filename}")
    try:
        if file.content_type not in ["application/json", "application/x-yaml", "text/yaml"]:
            logger.warning(f"Invalid content type for schema upload: {file.content_type}")
            raise HTTPException(status_code=400, detail="Invalid content type")
        contents = await file.read()
        await save_and_index_schema(project_id, contents, file.filename)
        logger.info(f"Schema uploaded and indexed successfully for project {project_id}")
        return {"message": "Schema uploaded and indexed successfully."}
    except Exception as e:
        logger.error(f"Error uploading schema for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading schema: {str(e)}")

@router.post("/{project_id}/generate-tests")
async def generate_tests(project_id: str):
    logger.info(f"Triggering test generation for project {project_id}")
    try:
        # プロジェクトの存在確認
        project_path = Path(f"{settings.SCHEMA_DIR}/{project_id}")
        if not project_path.exists():
            logger.error(f"Project directory not found: {project_path}")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
            
        # スキーマファイルの存在確認
        schema_files = list(project_path.glob("*.yaml")) + list(project_path.glob("*.yml")) + list(project_path.glob("*.json"))
        if not schema_files:
            logger.error(f"No schema files found in project directory: {project_path}")
            raise HTTPException(status_code=400, detail="No schema files found for this project. Please upload a schema first.")
        
        logger.info(f"Found schema files: {[f.name for f in schema_files]}")
        
        # テスト生成タスクを開始
        task_id = trigger_test_generation(project_id)
        if not task_id:
            logger.error(f"Failed to trigger test generation task for project {project_id}")
            raise HTTPException(status_code=500, detail="Failed to start test generation task")
            
        logger.info(f"Test generation task started with ID: {task_id}")
        return {"message": "Test generation started", "task_id": task_id, "status": "generating", "count": 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating tests: {str(e)}")

@router.get("/{project_id}/tests")
async def get_generated_tests(project_id: str):
    logger.info(f"Fetching generated tests for project {project_id}")
    try:
        tests = list_testcases(project_id)
        return JSONResponse(content=tests)
    except Exception as e:
        logger.error(f"Error fetching tests for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching tests: {str(e)}")

@router.post("/{project_id}/run")
async def run_project_tests(project_id: str):
    logger.info(f"Running tests for project {project_id}")
    try:
        results = await run_tests(project_id)
        logger.info(f"Test run completed for project {project_id}")
        return {"message": "Test run complete", "results": results}
    except Exception as e:
        logger.error(f"Error running tests for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error running tests: {str(e)}")

@router.get("/{project_id}/runs")
async def get_run_history(project_id: str):
    logger.info(f"Fetching run history for project {project_id}")
    try:
        return list_test_runs(project_id)
    except Exception as e:
        logger.error(f"Error fetching run history for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run history: {str(e)}")

@router.get("/{project_id}/runs/{run_id}")
async def get_run_detail(project_id: str, run_id: str):
    logger.info(f"Fetching run details for project {project_id}, run {run_id}")
    try:
        result = get_run_result(project_id, run_id)
        if result is None:
            logger.warning(f"Run not found: project {project_id}, run {run_id}")
            raise HTTPException(status_code=404, detail="Run not found")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run details for project {project_id}, run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run details: {str(e)}")

@router.get("/recent-runs")
async def get_recent_test_runs(limit: int = 5):
    """
    全プロジェクトの最近のテスト実行を取得する
    
    Args:
        limit: 取得する実行数の上限
        
    Returns:
        最近のテスト実行と統計情報
    """
    logger.info(f"Fetching recent test runs with limit {limit}")
    try:
        result = get_recent_runs(limit)
        return result
    except Exception as e:
        logger.error(f"Error fetching recent test runs: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching recent test runs: {str(e)}")

@router.get("/")
async def list_projects():
    logger.info("Listing all projects")
    try:
        from app.services.schema import list_projects
        return await list_projects()
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing projects: {str(e)}")

@router.post("/")
async def create_project(project: ProjectCreate):
    try:
        # ファイルシステムのチェック
        path = Path(f"{settings.SCHEMA_DIR}/{project.project_id}")
        if path.exists():
            raise HTTPException(status_code=409, detail="Project already exists")
        
        # データベースにプロジェクトを作成
        from app.services.schema import create_project as db_create_project
        result = await db_create_project(
            project_id=project.project_id,
            name=project.name,
            description=project.description
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=409, detail=result.get("message", "Project already exists"))
        
        logger.info(f"Created new project: {project.project_id}")
        return {"status": "created", "project_id": project.project_id, "name": project.name, "description": project.description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating project: {str(e)}")
