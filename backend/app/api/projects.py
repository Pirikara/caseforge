from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from app.services.schema import save_and_index_schema, get_schema_content
from app.services.runner import get_recent_runs
from app.services.chain_generator import ChainStore
from app.services.chain_runner import run_test_suites, list_test_runs, get_test_run
from app.services.endpoint_parser import EndpointParser
from app.workers.tasks import generate_test_suites_task, generate_test_suites_for_endpoints_task # タスク名を変更
from fastapi.responses import JSONResponse
from pathlib import Path
from app.config import settings
from app.utils.path_manager import path_manager
from app.logging_config import logger
from app.schemas.project import ProjectCreate
from app.schemas.project import Endpoint as EndpointSchema 
from app.models import Endpoint, Project, TestCase, engine
from sqlmodel import select, Session, delete
from typing import List, Optional
import json
from app.schemas.test_schemas import TestSuite, TestSuiteWithCasesAndSteps, TestRun, TestRunWithResults, TestRunSummary, TestCaseWithSteps, TestStep
from pydantic import BaseModel
from app.models import get_session

class Message(BaseModel):
    message: str

from datetime import datetime

def convert_datetime_to_iso(data):
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, list):
        return [convert_datetime_to_iso(item) for item in data]
    if isinstance(data, dict):
        return {key: convert_datetime_to_iso(value) for key, value in data.items()}
    return data

class TestRunTriggered(BaseModel): # テスト実行トリガー時のレスポンススキーマ
    message: str
    task_id: Optional[str] = None # タスクIDは非同期実行の場合にのみ存在する
    status: str # "generating" or "triggered"

class RecentTestRunsResponse(BaseModel): # 最近のテスト実行レスポンススキーマ
    recent_runs: List[TestRun]
    total_runs: int
    passed_runs: int
    failed_runs: int
    completed_runs: int
    running_runs: int

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
    project_path = path_manager.get_schema_dir(project_id)
    if not path_manager.exists(project_path):
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
    schema_files: list = Depends(get_schema_files_or_400), # スキーマファイルの存在チェックのために残す
    endpoint_ids: Optional[List[str]] = Body(None, description="生成対象のエンドポイントIDのリスト。指定しない場合はスキーマ全体から生成します。"),
    error_types: Optional[List[str]] = Body(None, description="生成する異常系テストの種類リスト") # 異常系の種類リストを追加
):
    """
    プロジェクトのテストスイートを生成するAPIエンドポイント。
    エンドポイントIDのリストが指定された場合は、それらのエンドポイントごとにテストスイートを生成します。
    指定されない場合は、スキーマ全体から依存関係を考慮したテストスイートを生成します。
    
    Args:
        project_id: プロジェクトID
        project_path: プロジェクトのパス (Depends)
        schema_files: スキーマファイルのリスト (Depends)
        endpoint_ids: 生成対象のエンドポイントIDのリスト (Optional)
        
    Returns:
        dict: 生成タスクの情報
    """
    logger.info(f"Triggering test suite generation for project {project_id}")
    
    try:
        if endpoint_ids:
            # エンドポイントIDが指定された場合、エンドポイントごとの生成タスクを呼び出す
            logger.info(f"Generating test suites for selected endpoints: {endpoint_ids} with error types: {error_types}")
            task_id = generate_test_suites_for_endpoints_task.delay(project_id, endpoint_ids, error_types).id # error_types を追加
            task_type = "endpoints"
        else:
            # エンドポイントIDが指定されない場合、スキーマ全体からの生成タスクを呼び出す (既存の挙動)
            logger.info(f"Generating test suites from entire schema with error types: {error_types}.")
            task_id = generate_test_suites_task.delay(project_id, error_types).id # error_types を追加
            task_type = "full_schema"
            
        if not task_id:
            logger.error(f"Failed to trigger test suite generation task for project {project_id}")
            raise HTTPException(status_code=500, detail="Failed to start test suite generation task")
            
        logger.info(f"Test suite generation task ({task_type}) started with ID: {task_id}")
        return {"message": f"Test suite generation ({task_type}) started", "task_id": task_id, "status": "generating"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating test suites: {str(e)}")

@router.get("/{project_id}/test-suites", response_model=List[TestSuite]) # response_model を追加
async def get_test_suites(
    project_id: str,
    session: Session = Depends(get_session), # Session 依存性を追加
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching test suites for project {project_id}")
    try:
        chain_store = ChainStore()
        test_suites = chain_store.list_test_suites(session, project_id) # session を渡すように修正
        return JSONResponse(content=test_suites)
    except Exception as e:
        logger.error(f"Error fetching test suites for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching test suites: {str(e)}")

@router.get("/{project_id}/test-suites/{suite_id}", response_model=TestSuiteWithCasesAndSteps) # response_model を追加
async def get_test_suite_detail(
    project_id: str,
    suite_id: str,
    session: Session = Depends(get_session), # Session 依存性を追加
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching test suite details for project {project_id}, suite {suite_id}")
    try:
        chain_store = ChainStore()
        # session を渡すように修正
        test_suite = chain_store.get_test_suite(session, project_id, suite_id)
        if test_suite is None:
            logger.warning(f"Test suite not found: project {project_id}, suite {suite_id}")
            raise HTTPException(status_code=404, detail="Test suite not found")
        return JSONResponse(content=test_suite)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test suite details for project {project_id}, suite {suite_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test suite details: {str(e)}")

@router.delete("/{project_id}/test-suites/{suite_id}", response_model=Message) # response_model を追加
async def delete_test_suite(
    project_id: str,
    suite_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    テストスイートを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test suite: project_id={project_id}, suite_id={suite_id}")
    try:
        # データベースからテストスイートを削除 (カスケード設定により関連データも削除される)
        with Session(engine) as session:
            # project_id と suite_id を使用して TestSuite を検索
            # TestSuite モデルには project_id (int) と id (str) がある
            # project_id (int) は Project モデルとのリレーションシップに使われるDB上のID
            # id (str) はユーザーに見せるユニークなID
            # ここでは id (str) を使用して検索する
            from app.models.chain import TestSuite # TestSuite モデルをインポート

            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.project_id == session.scalar(select(Project.id).where(Project.project_id == project_id))
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during deletion: project_id={project_id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            session.delete(db_test_suite)
            session.commit()
            logger.info(f"Test suite {suite_id} for project {project_id} and related data deleted from database.")

        # ChainStore にファイルシステム上のテストスイートデータ削除機能があれば呼び出す
        # ChainStore の実装を確認する必要があるが、一旦スキップ
        # chain_store = ChainStore()
        # chain_store.delete_test_suite(project_id, suite_id)

        return {"message": f"Test suite {suite_id} for project {project_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test suite {suite_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test suite: {str(e)}")

@router.get("/{project_id}/test-cases")
async def get_test_cases(
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
    logger.info(f"Getting test cases for project {project_id}")
    try:
        # ChainStoreを使ってテストスイートを取得
        chain_store = ChainStore()
        test_suites = chain_store.list_test_suites(project_id)
        
        # 各テストスイートからテストケースを抽出してフラットなリストにする
        test_cases = []
        for suite in test_suites:
            if "test_cases" in suite:
                test_cases.extend(suite["test_cases"])
                
        return JSONResponse(content=test_cases)
    except Exception as e:
        logger.error(f"Error getting test cases for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting test cases: {str(e)}")
    
@router.post("/{project_id}/run-test-suites", response_model=TestRunTriggered) # response_model を追加
async def run_test_suites_endpoint(
    project_id: str,
    suite_id: str = None,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Running test suites for project {project_id}")
    try:
        # run_test_suites はテスト実行結果を直接返す
        results = await run_test_suites(project_id, suite_id)
        logger.info(f"Test suite run completed for project {project_id}")
        
        # TestRunTriggered レスポンスモデルに合わせて情報を返す
        # run_test_suites は同期的に実行されるため、task_id は None となる
        return {
            "message": "Test suite run complete",
            "task_id": None, # 同期実行のため None
            "status": "completed" # 同期実行のため completed
        }
    except Exception as e:
        logger.error(f"Error running test suites for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error running test suites: {str(e)}")

@router.get("/{project_id}/runs", response_model=List[TestRunSummary]) # response_model を List[TestRunSummary] に変更
async def get_run_history(
    project_id: str,
    limit: int = 10,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching run history for project {project_id}")
    try:
        return list_test_runs(project_id, limit)
    except Exception as e:
        logger.error(f"Error fetching run history for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run history: {str(e)}")

@router.get("/{project_id}/runs/{run_id}", response_model=TestRunWithResults) # response_model を追加
async def get_run_detail(
    project_id: str,
    run_id: str,
    project_path: Path = Depends(get_project_or_404)
):
    logger.info(f"Fetching run details for project {project_id}, run {run_id}")
    try:
        result = get_test_run(project_id, run_id)
        if result is None:
            logger.warning(f"Test run not found: project {project_id}, run {run_id}")
            raise HTTPException(status_code=404, detail="Test run not found")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run details for project {project_id}, run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run details: {str(e)}")

@router.get("/recent-runs", response_model=RecentTestRunsResponse) # response_model を追加
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
        logger.debug(f"Checking filesystem for project directory: {settings.SCHEMA_DIR}/{project.project_id}")
        path = path_manager.get_schema_dir(project.project_id)
        if path_manager.exists(path):
            logger.warning(f"Filesystem check failed: Project directory already exists at {path}")
            raise HTTPException(status_code=409, detail="Project already exists")
        
        # データベースにプロジェクトを作成
        logger.debug(f"Attempting to create project in database: {project.project_id}")
        from app.services.schema import create_project as db_create_project
        result = await db_create_project(
            project_id=project.project_id,
            name=project.name,
            description=project.description,
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

@router.put("/{project_id}")
async def update_project(project_id: str, updated_project_data: dict = Body(...)):
    """
    プロジェクトを更新するAPIエンドポイント
    """
    logger.info(f"Updating project: {project_id}")
    logger.info(f"Received update data: {updated_project_data}") # 追加
    try:
        with Session(engine) as session:
            project_query = select(Project).where(Project.project_id == project_id)
            db_project = session.exec(project_query).first()

            if not db_project:
                logger.warning(f"Project not found in DB during update: {project_id}")
                raise HTTPException(status_code=404, detail="Project not found")

            # 更新データをプロジェクトオブジェクトに適用
            for key, value in updated_project_data.items():
                # Projectモデルに存在する属性のみを更新
                if hasattr(db_project, key):
                    setattr(db_project, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute: {key}")


            session.add(db_project)
            session.commit()
            session.refresh(db_project)
            logger.info(f"Project {project_id} updated successfully.")

            # 更新されたプロジェクト情報を返す（必要に応じてスキーマを定義）
            return {
                "id": db_project.project_id,
                "name": db_project.name,
                "description": db_project.description,
                "base_url": db_project.base_url,
                "created_at": db_project.created_at.isoformat()
            }
        # except HTTPException: # このexceptブロックは不要
        #     raise # このraiseは不要
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: str, project_path: Path = Depends(get_project_or_404)):
    """
    プロジェクトを削除するAPIエンドポイント
    """
    logger.info(f"Deleting project: {project_id}")
    try:
        # データベースからプロジェクトを削除 (カスケード設定により関連データも削除される)
        with Session(engine) as session:
            project_query = select(Project).where(Project.project_id == project_id)
            db_project = session.exec(project_query).first()

            if not db_project:
                # get_project_or_404 ですでにチェックされているが、念のため
                logger.warning(f"Project not found in DB during deletion: {project_id}")
                raise HTTPException(status_code=404, detail="Project not found")

            session.delete(db_project)
            session.commit()
            logger.info(f"Project {project_id} and related data deleted from database.")

        # ファイルシステムからプロジェクトディレクトリを削除
        import shutil
        shutil.rmtree(project_path)
        logger.info(f"Project directory {project_path} deleted from file system.")

        return {"message": f"Project {project_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")

@router.post("/{project_id}/endpoints/import")
async def import_endpoints(project_id: str, project_path: Path = Depends(get_project_or_404)):
    """
    スキーマからエンドポイントを抽出してDBに一括登録する
    
    Args:
        project_id: プロジェクトID
        project_path: プロジェクトのパス
    """
    logger.info(f"Importing endpoints for project {project_id}")
    try:
        # スキーマファイルを読み込み、エンドポイントを抽出
        schema_files = list(project_path.glob("*.yaml")) + list(project_path.glob("*.yml")) + list(project_path.glob("*.json"))
        if not schema_files:
            logger.warning(f"No schema files found for project {project_id} during import.")
            raise HTTPException(status_code=400, detail="No schema files found for this project. Please upload a schema first.")

        # 最新のスキーマファイルを取得
        latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"Using latest schema file for import: {latest_schema.name}")

        content = get_schema_content(project_id, latest_schema.name)
        parser = EndpointParser(content)
        endpoints_data = parser.parse_endpoints(project_id) # parse を parse_endpoints に修正し、project_id を渡す

        # データベースにエンドポイントを登録または更新
        with Session(engine) as session:
            # 既存のエンドポイントを全て削除
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is not None:
                delete_statement = delete(Endpoint).where(Endpoint.project_id == project_db_id)
                session.exec(delete_statement)
                session.commit()
                logger.info(f"Deleted existing endpoints for project {project_id} (DB ID: {project_db_id}).")
            else:
                 # プロジェクトがDBに存在しない場合はエラー（get_project_or_404でチェック済みだが念のため）
                 logger.error(f"Project with project_id {project_id} not found in database during endpoint import.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")


            # 新しいエンドポイントを登録
            updated_endpoints = []
            for ep_data in endpoints_data:
                # Endpoint モデルのインスタンスを作成
                # project_id は Project モデルとのリレーションシップに使われるDB上のID (int) を設定
                endpoint = Endpoint(
                    project_id=project_db_id,
                    path=ep_data["path"],
                    method=ep_data["method"],
                    summary=ep_data.get("summary"),
                    description=ep_data.get("description"),
                    # プロパティセッターを使用してJSON文字列として保存
                    request_body=ep_data.get("request_body"),
                    request_headers=ep_data.get("request_headers"),
                    request_query_params=ep_data.get("request_query_params"),
                    responses=ep_data.get("responses")
                )
                session.add(endpoint)
                updated_endpoints.append(endpoint) # 追加されたエンドポイントをリストに追加

            session.commit()

            # 追加されたエンドポイントをリフレッシュしてIDなどを取得
            for ep in updated_endpoints:
                session.refresh(ep)

            logger.info(f"Successfully imported and saved {len(updated_endpoints)} endpoints for project {project_id}")

            # デバッグログの追加
            logger.info(f"Debug: updated_endpoints type: {type(updated_endpoints)}")
            if updated_endpoints:
                logger.info(f"Debug: First element type: {type(updated_endpoints[0])}")
                try:
                    dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in updated_endpoints]
                    logger.info(f"Debug: Dumped endpoints successfully. First dumped element: {dumped_endpoints[0] if dumped_endpoints else 'N/A'}")
                except Exception as dump_error:
                    logger.error(f"Debug: Error during model_dump: {dump_error}", exc_info=True)
                    # エラーが発生した要素を特定するためのログ
                    for i, ep in enumerate(updated_endpoints):
                         try:
                             EndpointSchema.from_orm(ep).model_dump()
                         except Exception as single_dump_error:
                             logger.error(f"Debug: Error dumping element at index {i}: {single_dump_error}", exc_info=True)

            dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in updated_endpoints]
            json_compatible_endpoints = [convert_datetime_to_iso(ep_dict) for ep_dict in dumped_endpoints]
            return JSONResponse(content=json_compatible_endpoints)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing endpoints for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error importing endpoints: {str(e)}")

@router.get("/{project_id}/endpoints")
async def list_endpoints(
    project_id: str,
    project_path: Path = Depends(get_project_or_404)
):
    """
    プロジェクトのエンドポイント一覧を取得する
    
    Args:
        project_id: プロジェクトID
        project_path: プロジェクトのパス
        
    Returns:
        エンドポイントのリスト
    """
    logger.info(f"Listing endpoints for project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 # プロジェクトがDBに存在しない場合はエラー（get_project_or_404でチェック済みだが念のため）
                 logger.error(f"Project with project_id {project_id} not found in database during endpoint listing.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")
            
            # エンドポイントを path と method でソート
            endpoints = sorted(session.exec(select(Endpoint).where(Endpoint.project_id == project_db_id)).all(), key=lambda ep: (ep.path, ep.method))

            dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in endpoints]
            json_compatible_endpoints = [convert_datetime_to_iso(ep_dict) for ep_dict in dumped_endpoints]
            return JSONResponse(content=json_compatible_endpoints)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing endpoints for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing endpoints: {str(e)}")

@router.post("/{project_id}/endpoints/generate-suite")
async def generate_test_suite_for_endpoints(
    project_id: str,
    endpoint_ids: List[int] = Body(..., description="テストスイートを生成するエンドポイントのIDのリスト"),
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    指定されたエンドポイントIDに基づいてテストスイートを生成するAPIエンドポイント。
    """
    logger.info(f"Generating test suite for specific endpoints in project {project_id}: {endpoint_ids}")
    try:
        # 非同期タスクをトリガー
        task_id = generate_test_suites_for_endpoints_task.delay(project_id, endpoint_ids).id

        if not task_id:
            logger.error(f"Failed to trigger test suite generation task for endpoints in project {project_id}")
            raise HTTPException(status_code=500, detail="Failed to start test suite generation task")

        logger.info(f"Test suite generation task for endpoints started with ID: {task_id}")
        return {"message": "Test suite generation for endpoints started", "task_id": task_id, "status": "generating"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_test_suite_for_endpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating test suite for endpoints: {str(e)}")

@router.get("/{project_id}/test-suites/{suite_id}/test-cases", response_model=List[TestCase])
async def list_test_cases_for_suite(
    project_id: str,
    suite_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストスイートに紐づくテストケース一覧を取得するAPIエンドポイント
    """
    logger.info(f"Listing test cases for suite {suite_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test case listing for suite.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestSuite を project_id (int) と suite_id (str) で検索
            from app.models.chain import TestSuite # TestSuite モデルをインポート
            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.project_id == project_db_id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during test case listing: project_id={project_id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            # TestSuite に紐づく TestCases を取得
            # TestSuite モデルに test_cases リレーションシップがあることを前提とする
            test_cases = db_test_suite.test_cases

            # TestCases のリストを返す (Pydantic モデルに変換が必要であればここで変換)
            # TestSuiteWithCasesAndSteps スキーマの TestCases リストの要素の型を確認
            from app.schemas.test_schemas import TestCase # TestCase スキーマをインポート
            return JSONResponse(content=[TestCase.from_orm(tc).model_dump() for tc in test_cases])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing test cases for suite {suite_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing test cases for suite: {str(e)}")

@router.get("/{project_id}/test-cases/{case_id}", response_model=TestCaseWithSteps)
async def get_test_case_detail(
    project_id: str,
    case_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストケースの詳細を取得するAPIエンドポイント
    """
    logger.info(f"Fetching test case details for case {case_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test case detail fetch.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestCase を project_id (int) と case_id (str) で検索
            from app.models.chain import TestCase # TestCase モデルをインポート
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.project_id == project_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during detail fetch: project_id={project_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            # TestCaseWithSteps スキーマに変換して返す
            from app.schemas.test_schemas import TestCaseWithSteps # TestCaseWithSteps スキーマをインポート
            return JSONResponse(content=TestCaseWithSteps.from_orm(db_test_case).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test case details for case {case_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test case details: {str(e)}")

@router.post("/{project_id}/test-suites/{suite_id}/test-cases", response_model=TestCase)
async def create_test_case(
    project_id: str,
    suite_id: str,
    test_case_data: dict = Body(...), # テストケースのデータを受け取る
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストスイートに新しいテストケースを作成するAPIエンドポイント
    """
    logger.info(f"Creating new test case for suite {suite_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test case creation.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestSuite を project_id (int) と suite_id (str) で検索
            from app.models.chain import TestSuite # TestSuite モデルをインポート
            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.project_id == project_db_id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during test case creation: project_id={project_id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            # TestCase モデルのインスタンスを作成
            # test_case_data には suite_id は含まれていないはずなので、ここで設定
            # project_id は Project モデルとのリレーションシップに使われるDB上のID (int) を設定
            from app.models.chain import TestCase # TestCase モデルをインポート
            test_case = TestCase(suite_id=db_test_suite.id, project_id=project_db_id, **test_case_data)

            session.add(test_case)
            session.commit()
            session.refresh(test_case)
            logger.info(f"Test case {test_case.id} created successfully for suite {suite_id}.")

            # 作成されたテストケースを返す (Pydantic モデルに変換)
            from app.schemas.test_schemas import TestCase # TestCase スキーマをインポート
            return TestCase.from_orm(test_case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test case for suite {suite_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating test case: {str(e)}")

@router.put("/{project_id}/test-cases/{case_id}", response_model=TestCase)
async def update_test_case(
    project_id: str,
    case_id: str,
    updated_test_case_data: dict = Body(...), # 更新データを受け取る
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストケースを更新するAPIエンドポイント
    """
    logger.info(f"Updating test case {case_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test case update.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestCase を project_id (int) と case_id (str) で検索
            from app.models.chain import TestCase # TestCase モデルをインポート
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.project_id == project_db_id
            )
            db_test_case = session.exec(test_case_query).first() # ここが間違っている可能性あり、test_case_query であるべき

            if not db_test_case:
                logger.warning(f"Test case not found in DB during update: project_id={project_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            # 更新データをテストケースオブジェクトに適用
            for key, value in updated_test_case_data.items():
                # TestCaseモデルに存在する属性のみを更新
                if hasattr(db_test_case, key):
                    setattr(db_test_case, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute in TestCase: {key}")

            session.add(db_test_case)
            session.commit()
            session.refresh(db_test_case)
            logger.info(f"Test case {case_id} updated successfully.")

            # 更新されたテストケースを返す (Pydantic モデルに変換)
            from app.schemas.test_schemas import TestCase # TestCase スキーマをインポート
            return TestCase.from_orm(db_test_case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test case {case_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating test case: {str(e)}")

@router.delete("/{project_id}/test-cases/{case_id}", response_model=Message)
async def delete_test_case(
    project_id: str,
    case_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストケースを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test case: project_id={project_id}, case_id={case_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test case deletion.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestCase を project_id (int) と case_id (str) で検索
            from app.models.chain import TestCase # TestCase モデルをインポート
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.project_id == project_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during deletion: project_id={project_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            session.delete(db_test_case)
            session.commit()
            logger.info(f"Test case {case_id} for project {project_id} deleted from database.")

        return {"message": f"Test case {case_id} for project {project_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test case {case_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test case: {str(e)}")

@router.get("/{project_id}/test-cases/{case_id}/test-steps", response_model=List[TestStep])
async def list_test_steps_for_case(
    project_id: str,
    case_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストケースに紐づくテストステップ一覧を取得するAPIエンドポイント
    """
    logger.info(f"Listing test steps for case {case_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test step listing for case.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestCase を project_id (int) と case_id (str) で検索
            from app.models.chain import TestCase # TestCase モデルをインポート
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.project_id == project_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during test step listing: project_id={project_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            # TestCase に紐づく TestSteps を取得
            # TestCase モデルに test_steps リレーションシップがあることを前提とする
            test_steps = db_test_case.test_steps

            # TestSteps のリストを返す (Pydantic モデルに変換)
            from app.schemas.test_schemas import TestStep # TestStep スキーマをインポート
            return JSONResponse(content=[TestStep.from_orm(ts).model_dump() for ts in test_steps])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing test steps for case {case_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing test steps for case: {str(e)}")

@router.get("/{project_id}/test-steps/{step_id}", response_model=TestStep)
async def get_test_step_detail(
    project_id: str,
    step_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストステップの詳細を取得するAPIエンドポイント
    """
    logger.info(f"Fetching test step details for step {step_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test step detail fetch.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestStep を project_id (int) と step_id (str) で検索
            from app.models.chain import TestStep # TestStep モデルをインポート
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.project_id == project_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                logger.warning(f"Test step not found in DB during detail fetch: project_id={project_id}, step_id={step_id}")
                raise HTTPException(status_code=404, detail="Test step not found")

            # TestStep スキーマに変換して返す
            from app.schemas.test_schemas import TestStep # TestStep スキーマをインポート
            return JSONResponse(content=TestStep.from_orm(db_test_step).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test step details for step {step_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test step details: {str(e)}")

@router.post("/{project_id}/test-cases/{case_id}/test-steps", response_model=TestStep)
async def create_test_step(
    project_id: str,
    case_id: str,
    test_step_data: dict = Body(...), # テストステップのデータを受け取る
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストケースに新しいテストステップを作成するAPIエンドポイント
    """
    logger.info(f"Creating new test step for case {case_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test step creation.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestCase を project_id (int) と case_id (str) で検索
            from app.models.chain import TestCase # TestCase モデルをインポート
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.project_id == project_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during test step creation: project_id={project_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            # TestStep モデルのインスタンスを作成
            # test_step_data には case_id は含まれていないはずなので、ここで設定
            # project_id は Project モデルとのリレーションシップに使われるDB上のID (int) を設定
            from app.models.chain import TestStep # TestStep モデルをインポート
            test_step = TestStep(case_id=db_test_case.id, project_id=project_db_id, **test_step_data)

            session.add(test_step)
            session.commit()
            session.refresh(test_step)
            logger.info(f"Test step {test_step.id} created successfully for case {case_id}.")

            # 作成されたテストステップを返す (Pydantic モデルに変換)
            from app.schemas.test_schemas import TestStep # TestStep スキーマをインポート
            return TestStep.from_orm(test_step)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test step for case {case_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating test step: {str(e)}")

@router.put("/{project_id}/test-steps/{step_id}", response_model=TestStep)
async def update_test_step(
    project_id: str,
    step_id: str,
    updated_test_step_data: dict = Body(...), # 更新データを受け取る
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストステップを更新するAPIエンドポイント
    """
    logger.info(f"Updating test step {step_id} in project {project_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test step update.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestStep を project_id (int) と step_id (str) で検索
            from app.models.chain import TestStep # TestStep モデルをインポート
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.project_id == project_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                logger.warning(f"Test step not found in DB during update: project_id={project_id}, step_id={step_id}")
                raise HTTPException(status_code=404, detail="Test step not found")

            # 更新データをテストステップオブジェクトに適用
            for key, value in updated_test_step_data.items():
                # TestStepモデルに存在する属性のみを更新
                if hasattr(db_test_step, key):
                    setattr(db_test_step, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute in TestStep: {key}")

            session.add(db_test_step)
            session.commit()
            session.refresh(db_test_step)
            logger.info(f"Test step {step_id} updated successfully.")

            # 更新されたテストステップを返す (Pydantic モデルに変換)
            from app.schemas.test_schemas import TestStep # TestStep スキーマをインポート
            return TestStep.from_orm(db_test_step)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test step {step_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating test step: {str(e)}")

@router.delete("/{project_id}/test-steps/{step_id}", response_model=Message)
async def delete_test_step(
    project_id: str,
    step_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    特定のテストステップを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test step: project_id={project_id}, step_id={step_id}")
    try:
        with Session(engine) as session:
            # project_id (str) から Project の DB上の id (int) を取得
            project_db_id = session.scalar(select(Project.id).where(Project.project_id == project_id))
            if project_db_id is None:
                 logger.error(f"Project with project_id {project_id} not found in database during test step deletion.")
                 raise HTTPException(status_code=404, detail="Project not found in database.")

            # TestStep を project_id (int) と step_id (str) で検索
            from app.models.chain import TestStep # TestStep モデルをインポート
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.project_id == project_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                logger.warning(f"Test step not found in DB during deletion: project_id={project_id}, step_id={step_id}")
                raise HTTPException(status_code=404, detail="Test step not found")

            session.delete(db_test_step)
            session.commit()
            logger.info(f"Test step {step_id} for project {project_id} deleted from database.")

        return {"message": f"Test step {step_id} for project {project_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test step {step_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test step: {str(e)}")
