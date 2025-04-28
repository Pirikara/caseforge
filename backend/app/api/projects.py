from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from app.services.schema import save_and_index_schema, get_schema_content
from app.services.testgen import trigger_test_generation
from app.services.teststore import list_testcases
from app.services.runner import get_recent_runs
from app.services.chain_generator import ChainStore
from app.services.chain_runner import run_chains, list_chain_runs, get_chain_run
from app.workers.tasks import generate_chains_task
from fastapi.responses import JSONResponse
from pathlib import Path
from app.config import settings
from app.logging_config import logger
from app.schemas.project import ProjectCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])

def get_project_or_404(project_id: str) -> Path:
    """
    プロジェクトの存在を確認し、存在しない場合は404エラーを発生させる
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        プロジェクトのパス
        
    Raises:
        HTTPException: プロジェクトが存在しない場合
    """
    project_path = Path(f"{settings.SCHEMA_DIR}/{project_id}")
    if not project_path.exists():
        logger.error(f"Project directory not found: {project_path}")
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project_path

def get_schema_files_or_400(project_id: str = None, project_path: Path = Depends(get_project_or_404)) -> list:
    """
    プロジェクトのスキーマファイルを取得し、存在しない場合は400エラーを発生させる
    
    Args:
        project_path: プロジェクトのパス
        
    Returns:
        スキーマファイルのリスト
        
    Raises:
        HTTPException: スキーマファイルが存在しない場合
    """
    schema_files = list(project_path.glob("*.yaml")) + list(project_path.glob("*.yml")) + list(project_path.glob("*.json"))
    if not schema_files:
        logger.error(f"No schema files found in project directory: {project_path}")
        raise HTTPException(status_code=400, detail="No schema files found for this project. Please upload a schema first.")
    logger.info(f"Found schema files: {[f.name for f in schema_files]}")
    return schema_files

@router.get("/{project_id}/schema")
async def get_schema(project_id: str, project_path: Path = Depends(get_project_or_404)):
    """
    プロジェクトのスキーマを取得する
    
    Args:
        project_id: プロジェクトID
        project_path: プロジェクトのパス
        
    Returns:
        スキーマの内容
    """
    logger.info(f"Getting schema for project {project_id}")
    try:
        # プロジェクトディレクトリからスキーマファイルを検索
        schema_files = list(project_path.glob("*.yaml")) + list(project_path.glob("*.yml")) + list(project_path.glob("*.json"))
        if not schema_files:
            logger.error(f"No schema files found in project directory: {project_path}")
            raise HTTPException(status_code=404, detail="No schema files found for this project")
        
        # 最新のスキーマファイルを取得
        latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"Found latest schema file: {latest_schema.name}")
        
        # スキーマファイルの内容を取得
        content = get_schema_content(project_id, latest_schema.name)
        
        # ファイル形式に応じてContent-Typeを設定
        content_type = "application/json" if latest_schema.name.endswith(".json") else "application/x-yaml"
        
        return {
            "filename": latest_schema.name,
            "content": content,
            "content_type": content_type
        }
    except FileNotFoundError as e:
        logger.error(f"Schema file not found for project {project_id}: {e}")
        raise HTTPException(status_code=404, detail="Schema file not found")
    except Exception as e:
        logger.error(f"Error getting schema for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting schema: {str(e)}")

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
async def generate_tests(
    project_id: str,
    project_path: Path = Depends(get_project_or_404),
    schema_files: list = Depends(get_schema_files_or_400)
):
    logger.info(f"Triggering test chain generation for project {project_id}")
    try:
        # プロジェクトとスキーマファイルの存在は既に検証済み
        
        # テストチェーン生成タスクを開始
        task_id = generate_chains_task.delay(project_id).id
        if not task_id:
            logger.error(f"Failed to trigger test chain generation task for project {project_id}")
            raise HTTPException(status_code=500, detail="Failed to start test chain generation task")
            
        logger.info(f"Test chain generation task started with ID: {task_id}")
        return {"message": "Test chain generation started", "task_id": task_id, "status": "generating"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating test chains: {str(e)}")

@router.get("/{project_id}/chains")
async def get_chains(
    project_id: str,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching chains for project {project_id}")
    try:
        chain_store = ChainStore()
        chains = chain_store.list_chains(project_id)
        return JSONResponse(content=chains)
    except Exception as e:
        logger.error(f"Error fetching chains for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching chains: {str(e)}")

@router.get("/{project_id}/chains/{chain_id}")
async def get_chain_detail(
    project_id: str,
    chain_id: str,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching chain details for project {project_id}, chain {chain_id}")
    try:
        chain_store = ChainStore()
        chain = chain_store.get_chain(project_id, chain_id)
        if chain is None:
            logger.warning(f"Chain not found: project {project_id}, chain {chain_id}")
            raise HTTPException(status_code=404, detail="Chain not found")
        return JSONResponse(content=chain)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chain details for project {project_id}, chain {chain_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching chain details: {str(e)}")

@router.get("/{project_id}/tests")
async def get_tests(
    project_id: str,
    project_path: Path = Depends(get_project_or_404)
):
    """
    プロジェクトのテストケース一覧を取得する
    
    Args:
        project_id: プロジェクトID
        project_path: プロジェクトのパス
        
    Returns:
        テストケースのリスト
    """
    logger.info(f"Getting tests for project {project_id}")
    try:
        # ChainStoreを使ってチェーンを取得
        chain_store = ChainStore()
        chains = chain_store.list_chains(project_id)
        return JSONResponse(content=chains)
    except Exception as e:
        logger.error(f"Error getting tests for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting tests: {str(e)}")

@router.post("/{project_id}/run")
async def run_project_chains(
    project_id: str,
    chain_id: str = None,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Running chains for project {project_id}")
    try:
        results = await run_chains(project_id, chain_id)
        logger.info(f"Chain run completed for project {project_id}")
        return {"message": "Chain run complete", "results": results}
    except Exception as e:
        logger.error(f"Error running chains for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error running chains: {str(e)}")

@router.get("/{project_id}/runs")
async def get_run_history(
    project_id: str,
    limit: int = 10,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching run history for project {project_id}")
    try:
        return list_chain_runs(project_id, limit)
    except Exception as e:
        logger.error(f"Error fetching run history for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run history: {str(e)}")

@router.get("/{project_id}/runs/{run_id}")
async def get_run_detail(
    project_id: str,
    run_id: str,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching run details for project {project_id}, run {run_id}")
    try:
        result = get_chain_run(project_id, run_id)
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
