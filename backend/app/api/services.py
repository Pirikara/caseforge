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
from app.schemas.service import ServiceCreate
from app.schemas.service import Endpoint as EndpointSchema 
from app.models import Endpoint, Service, TestCase, engine
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

class TestRunTriggered(BaseModel):
    message: str
    task_id: Optional[str] = None
    status: str

class RecentTestRunsResponse(BaseModel):
    recent_runs: List[TestRun]
    total_runs: int
    passed_runs: int
    failed_runs: int
    completed_runs: int
    running_runs: int

router = APIRouter(prefix="/api/services", tags=["services"])

def get_service_or_404(service_id: str) -> Path:
    """
    サービスの存在を確認し、存在しない場合は404エラーを発生させる
    
    Args:
        service_id: サービスID
        
    Returns:
        サービスのパス
        
    Raises:
        HTTPException: サービスが存在しない場合
    """
    service_path = path_manager.get_schema_dir(service_id)
    if not path_manager.exists(service_path):
        logger.error(f"Service directory not found: {service_path}")
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
    return service_path

def get_schema_files_or_400(service_id: str = None, service_path: Path = Depends(get_service_or_404)) -> list:
    """
    サービスのスキーマファイルを取得し、存在しない場合は400エラーを発生させる
    
    Args:
        service_path: サービスのパス
        
    Returns:
        スキーマファイルのリスト
        
    Raises:
        HTTPException: スキーマファイルが存在しない場合
    """
    schema_files = list(service_path.glob("*.yaml")) + list(service_path.glob("*.yml")) + list(service_path.glob("*.json"))
    if not schema_files:
        logger.error(f"No schema files found in service directory: {service_path}")
        raise HTTPException(status_code=400, detail="No schema files found for this service. Please upload a schema first.")
    logger.info(f"Found schema files: {[f.name for f in schema_files]}")
    return schema_files

@router.get("/{service_id}/schema")
async def get_schema(service_id: str, service_path: Path = Depends(get_service_or_404)):
    """
    サービスのスキーマを取得する
    
    Args:
        service_id: サービスID
        service_path: サービスのパス
        
    Returns:
        スキーマの内容
    """
    logger.info(f"Getting schema for service {service_id}")
    try:
        schema_files = list(service_path.glob("*.yaml")) + list(service_path.glob("*.yml")) + list(service_path.glob("*.json"))
        if not schema_files:
            logger.error(f"No schema files found in service directory: {service_path}")
            raise HTTPException(status_code=404, detail="No schema files found for this service")
        
        latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"Found latest schema file: {latest_schema.name}")
        
        content = get_schema_content(service_id, latest_schema.name)
        
        content_type = "application/json" if latest_schema.name.endswith(".json") else "application/x-yaml"
        
        return {
            "filename": latest_schema.name,
            "content": content,
            "content_type": content_type
        }
    except FileNotFoundError as e:
        logger.error(f"Schema file not found for service {service_id}: {e}")
        raise HTTPException(status_code=404, detail="Schema file not found")
    except Exception as e:
        logger.error(f"Error getting schema for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting schema: {str(e)}")

@router.post("/{service_id}/schema")
async def upload_schema(service_id: str, file: UploadFile = File(...)):
    logger.info(f"Uploading schema for service {service_id}: {file.filename}")
    try:
        if file.content_type not in ["application/json", "application/x-yaml", "text/yaml"]:
            logger.warning(f"Invalid content type for schema upload: {file.content_type}")
            raise HTTPException(status_code=400, detail="Invalid content type")
        contents = await file.read()
        await save_and_index_schema(service_id, contents, file.filename)
        logger.info(f"Schema uploaded and indexed successfully for service {service_id}")
        return {"message": "Schema uploaded and indexed successfully."}
    except Exception as e:
        logger.error(f"Error uploading schema for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading schema: {str(e)}")

@router.post("/{service_id}/generate-tests")
async def generate_tests(
    service_id: str,
    service_path: Path = Depends(get_service_or_404),
    schema_files: list = Depends(get_schema_files_or_400),
    endpoint_ids: Optional[List[str]] = Body(None, description="生成対象のエンドポイントIDのリスト。指定しない場合はスキーマ全体から生成します。"),
    error_types: Optional[List[str]] = Body(None, description="生成する異常系テストの種類リスト")
):
    """
    サービスのテストスイートを生成するAPIエンドポイント。
    エンドポイントIDのリストが指定された場合は、それらのエンドポイントごとにテストスイートを生成します。
    指定されない場合は、スキーマ全体から依存関係を考慮したテストスイートを生成します。
    
    Args:
        service_id: サービスID
        service_path: サービスのパス (Depends)
        schema_files: スキーマファイルのリスト (Depends)
        endpoint_ids: 生成対象のエンドポイントIDのリスト (Optional)
        
    Returns:
        dict: 生成タスクの情報
    """
    logger.info(f"Triggering test suite generation for service {service_id}")
    
    try:
        if endpoint_ids:
            logger.info(f"Generating test suites for selected endpoints: {endpoint_ids} with error types: {error_types}")
            task_id = generate_test_suites_for_endpoints_task.delay(service_id, endpoint_ids, error_types).id
            task_type = "endpoints"
        else:
            logger.info(f"Generating test suites from entire schema with error types: {error_types}.")
            task_id = generate_test_suites_task.delay(service_id, error_types).id
            task_type = "full_schema"
            
        if not task_id:
            logger.error(f"Failed to trigger test suite generation task for service {service_id}")
            raise HTTPException(status_code=500, detail="Failed to start test suite generation task")
            
        logger.info(f"Test suite generation task ({task_type}) started with ID: {task_id}")
        return {"message": f"Test suite generation ({task_type}) started", "task_id": task_id, "status": "generating"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating test suites: {str(e)}")

@router.get("/{service_id}/test-suites", response_model=List[TestSuite])
async def get_test_suites(
    service_id: str,
    session: Session = Depends(get_session),
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching test suites for service {service_id}")
    try:
        chain_store = ChainStore()
        test_suites = chain_store.list_test_suites(session, service_id)
        return JSONResponse(content=test_suites)
    except Exception as e:
        logger.error(f"Error fetching test suites for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching test suites: {str(e)}")

@router.get("/{service_id}/test-suites/{suite_id}", response_model=TestSuiteWithCasesAndSteps)
async def get_test_suite_detail(
    service_id: str,
    suite_id: str,
    session: Session = Depends(get_session),
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching test suite details for service {service_id}, suite {suite_id}")
    try:
        chain_store = ChainStore()
        test_suite = chain_store.get_test_suite(session, service_id, suite_id)
        if test_suite is None:
            logger.warning(f"Test suite not found: service {service_id}, suite {suite_id}")
            raise HTTPException(status_code=404, detail="Test suite not found")
        return JSONResponse(content=test_suite)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test suite details for service {service_id}, suite {suite_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test suite details: {str(e)}")

@router.delete("/{service_id}/test-suites/{suite_id}", response_model=Message)
async def delete_test_suite(
    service_id: str,
    suite_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    テストスイートを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test suite: service_id={service_id}, suite_id={suite_id}")
    try:
        with Session(engine) as session:
            from app.models.chain import TestSuite

            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.service_id == session.scalar(select(Service.id).where(Service.service_id == service_id))
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during deletion: service_id={service_id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            session.delete(db_test_suite)
            session.commit()
            logger.info(f"Test suite {suite_id} for service {service_id} and related data deleted from database.")

        # ChainStore にファイルシステム上のテストスイートデータ削除機能があれば呼び出す
        # ChainStore の実装を確認する必要があるが、一旦スキップ
        # chain_store = ChainStore()
        # chain_store.delete_test_suite(service_id, suite_id)

        return {"message": f"Test suite {suite_id} for service {service_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test suite {suite_id} for service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test suite: {str(e)}")

@router.get("/{service_id}/test-cases")
async def get_test_cases(
    service_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    サービスのテストケース一覧を取得する
    
    Args:
        service_id: サービスID
        service_path: サービスのパス
        
    Returns:
        テストケースのリスト
    """
    logger.info(f"Getting test cases for service {service_id}")
    try:
        chain_store = ChainStore()
        test_suites = chain_store.list_test_suites(service_id)
        
        test_cases = []
        for suite in test_suites:
            if "test_cases" in suite:
                test_cases.extend(suite["test_cases"])
                
        return JSONResponse(content=test_cases)
    except Exception as e:
        logger.error(f"Error getting test cases for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting test cases: {str(e)}")
    
@router.post("/{service_id}/run-test-suites", response_model=TestRunTriggered)
async def run_test_suites_endpoint(
    service_id: str,
    suite_id: str = None,
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Running test suites for service {service_id}")
    try:
        results = await run_test_suites(service_id, suite_id)
        logger.info(f"Test suite run completed for service {service_id}")
        
        return {
            "message": "Test suite run complete",
            "task_id": None,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error running test suites for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error running test suites: {str(e)}")

@router.get("/{service_id}/runs", response_model=List[TestRunSummary])
async def get_run_history(
    service_id: str,
    limit: int = 10,
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching run history for service {service_id}")
    try:
        return list_test_runs(service_id, limit)
    except Exception as e:
        logger.error(f"Error fetching run history for service {service_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run history: {str(e)}")

@router.get("/{service_id}/runs/{run_id}", response_model=TestRunWithResults)
async def get_run_detail(
    service_id: str,
    run_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching run details for service {service_id}, run {run_id}")
    try:
        result = get_test_run(service_id, run_id)
        if result is None:
            logger.warning(f"Test run not found: service {service_id}, run {run_id}")
            raise HTTPException(status_code=404, detail="Test run not found")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run details for service {service_id}, run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run details: {str(e)}")

@router.get("/recent-runs", response_model=RecentTestRunsResponse)
async def get_recent_test_runs(limit: int = 5):
    """
    全サービスの最近のテスト実行を取得する
    
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
async def list_services():
    logger.info("Listing all services")
    try:
        from app.services.schema import list_services
        return await list_services()
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing services: {str(e)}")

@router.post("/")
async def create_service(service: ServiceCreate):
    try:
        logger.debug(f"Checking filesystem for service directory: {settings.SCHEMA_DIR}/{service.service_id}")
        path = path_manager.get_schema_dir(service.service_id)
        if path_manager.exists(path):
            logger.warning(f"Filesystem check failed: Service directory already exists at {path}")
            raise HTTPException(status_code=409, detail="Service already exists")
        
        logger.debug(f"Attempting to create service in database: {service.service_id}")
        from app.services.schema import create_service as db_create_service
        result = await db_create_service(
            service_id=service.service_id,
            name=service.name,
            description=service.description,
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=409, detail=result.get("message", "Service already exists"))
        
        logger.info(f"Created new service: {service.service_id}")
        return {"status": "created", "service_id": service.service_id, "name": service.name, "description": service.description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating service: {str(e)}")

@router.put("/{service_id}")
async def update_service(service_id: str, updated_service_data: dict = Body(...)):
    """
    サービスを更新するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_query = select(Service).where(Service.service_id == service_id)
            db_service = session.exec(service_query).first()

            if not db_service:
                logger.warning(f"Service not found in DB during update: {service_id}")
                raise HTTPException(status_code=404, detail="Service not found")

            for key, value in updated_service_data.items():
                if hasattr(db_service, key):
                    setattr(db_service, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute: {key}")


            session.add(db_service)
            session.commit()
            session.refresh(db_service)
            logger.info(f"Service {service_id} updated successfully.")

            return {
                "id": db_service.service_id,
                "name": db_service.name,
                "description": db_service.description,
                "base_url": db_service.base_url,
                "created_at": db_service.created_at.isoformat()
            }
    except Exception as e:
        logger.error(f"Error updating service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating service: {str(e)}")


@router.delete("/{service_id}")
async def delete_service(service_id: str, service_path: Path = Depends(get_service_or_404)):
    """
    サービスを削除するAPIエンドポイント
    """
    logger.info(f"Deleting service: {service_id}")
    try:
        # データベースからサービスを削除 (カスケード設定により関連データも削除される)
        with Session(engine) as session:
            service_query = select(Service).where(Service.service_id == service_id)
            db_service = session.exec(service_query).first()

            if not db_service:
                # get_service_or_404 ですでにチェックされているが、念のため
                logger.warning(f"Service not found in DB during deletion: {service_id}")
                raise HTTPException(status_code=404, detail="Service not found")

            session.delete(db_service)
            session.commit()
            logger.info(f"Service {service_id} and related data deleted from database.")

        # ファイルシステムからサービスディレクトリを削除
        import shutil
        shutil.rmtree(service_path)
        logger.info(f"Service directory {service_path} deleted from file system.")

        return {"message": f"Service {service_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting service: {str(e)}")

@router.post("/{service_id}/endpoints/import")
async def import_endpoints(service_id: str, service_path: Path = Depends(get_service_or_404)):
    """
    スキーマからエンドポイントを抽出してDBに一括登録する
    
    Args:
        service_id: サービスID
        service_path: サービスのパス
    """
    logger.info(f"Importing endpoints for service {service_id}")
    try:
        schema_files = list(service_path.glob("*.yaml")) + list(service_path.glob("*.yml")) + list(service_path.glob("*.json"))
        if not schema_files:
            logger.warning(f"No schema files found for service {service_id} during import.")
            raise HTTPException(status_code=400, detail="No schema files found for this service. Please upload a schema first.")

        latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"Using latest schema file for import: {latest_schema.name}")

        content = get_schema_content(service_id, latest_schema.name)
        parser = EndpointParser(content)
        endpoints_data = parser.parse_endpoints(service_id)

        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is not None:
                delete_statement = delete(Endpoint).where(Endpoint.service_id == service_db_id)
                session.exec(delete_statement)
                session.commit()
                logger.info(f"Deleted existing endpoints for service {service_id} (DB ID: {service_db_id}).")
            else:
                 logger.error(f"Service with service_id {service_id} not found in database during endpoint import.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            updated_endpoints = []
            for ep_data in endpoints_data:
                endpoint = Endpoint(
                    service_id=service_db_id,
                    path=ep_data["path"],
                    method=ep_data["method"],
                    summary=ep_data.get("summary"),
                    description=ep_data.get("description"),
                    request_body=(
                        json.dumps(ep_data.get("request_body"), ensure_ascii=False)
                        if isinstance(ep_data.get("request_body"), dict)
                        else str(ep_data.get("request_body"))
                    ),
                    request_headers=(
                        json.dumps(ep_data.get("request_headers"), ensure_ascii=False)
                        if isinstance(ep_data.get("request_headers"), dict)
                        else str(ep_data.get("request_headers"))
                    ),
                    request_query_params=(
                        json.dumps(ep_data.get("request_query_params"), ensure_ascii=False)
                        if isinstance(ep_data.get("request_query_params"), dict)
                        else str(ep_data.get("request_query_params"))
                    ),
                    responses=(
                        json.dumps(ep_data.get("response"), ensure_ascii=False)
                        if isinstance(ep_data.get("response"), dict)
                        else str(ep_data.get("response"))
                    )
                )
                session.add(endpoint)
                updated_endpoints.append(endpoint)

            session.commit()

            for ep in updated_endpoints:
                session.refresh(ep)

            logger.info(f"Successfully imported and saved {len(updated_endpoints)} endpoints for service {service_id}")

            logger.info(f"Debug: updated_endpoints type: {type(updated_endpoints)}")
            if updated_endpoints:
                logger.info(f"Debug: First element type: {type(updated_endpoints[0])}")
                try:
                    dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in updated_endpoints]
                    logger.info(f"Debug: Dumped endpoints successfully. First dumped element: {dumped_endpoints[0] if dumped_endpoints else 'N/A'}")
                except Exception as dump_error:
                    logger.error(f"Debug: Error during model_dump: {dump_error}", exc_info=True)
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
        logger.error(f"Error importing endpoints for service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error importing endpoints: {str(e)}")

@router.get("/{service_id}/endpoints")
async def list_endpoints(
    service_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    サービスのエンドポイント一覧を取得する
    
    Args:
        service_id: サービスID
        service_path: サービスのパス
        
    Returns:
        エンドポイントのリスト
    """
    logger.info(f"Listing endpoints for service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during endpoint listing.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")
            
            endpoints = sorted(session.exec(select(Endpoint).where(Endpoint.service_id == service_db_id)).all(), key=lambda ep: (ep.path, ep.method))

            dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in endpoints]
            json_compatible_endpoints = [convert_datetime_to_iso(ep_dict) for ep_dict in dumped_endpoints]
            return JSONResponse(content=json_compatible_endpoints)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing endpoints for service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing endpoints: {str(e)}")

@router.post("/{service_id}/endpoints/generate-suite")
async def generate_test_suite_for_endpoints(
    service_id: str,
    endpoint_ids: List[int] = Body(..., description="テストスイートを生成するエンドポイントのIDのリスト"),
    service_path: Path = Depends(get_service_or_404)
):
    """
    指定されたエンドポイントIDに基づいてテストスイートを生成するAPIエンドポイント。
    """
    logger.info(f"Generating test suite for specific endpoints in service {service_id}: {endpoint_ids}")
    try:
        task_id = generate_test_suites_for_endpoints_task.delay(service_id, endpoint_ids).id

        if not task_id:
            logger.error(f"Failed to trigger test suite generation task for endpoints in service {service_id}")
            raise HTTPException(status_code=500, detail="Failed to start test suite generation task")

        logger.info(f"Test suite generation task for endpoints started with ID: {task_id}")
        return {"message": "Test suite generation for endpoints started", "task_id": task_id, "status": "generating"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_test_suite_for_endpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating test suite for endpoints: {str(e)}")

@router.get("/{service_id}/test-suites/{suite_id}/test-cases", response_model=List[TestCase])
async def list_test_cases_for_suite(
    service_id: str,
    suite_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストスイートに紐づくテストケース一覧を取得するAPIエンドポイント
    """
    logger.info(f"Listing test cases for suite {suite_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test case listing for suite.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestSuite
            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.service_id == service_db_id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during test case listing: service_id={service_id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            test_cases = db_test_suite.test_cases

            from app.schemas.test_schemas import TestCase
            return JSONResponse(content=[TestCase.from_orm(tc).model_dump() for tc in test_cases])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing test cases for suite {suite_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing test cases for suite: {str(e)}")

@router.get("/{service_id}/test-cases/{case_id}", response_model=TestCaseWithSteps)
async def get_test_case_detail(
    service_id: str,
    case_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースの詳細を取得するAPIエンドポイント
    """
    logger.info(f"Fetching test case details for case {case_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test case detail fetch.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during detail fetch: service_id={service_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            from app.schemas.test_schemas import TestCaseWithSteps
            return JSONResponse(content=TestCaseWithSteps.from_orm(db_test_case).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test case details for case {case_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test case details: {str(e)}")

@router.post("/{service_id}/test-suites/{suite_id}/test-cases", response_model=TestCase)
async def create_test_case(
    service_id: str,
    suite_id: str,
    test_case_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストスイートに新しいテストケースを作成するAPIエンドポイント
    """
    logger.info(f"Creating new test case for suite {suite_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test case creation.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestSuite
            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.service_id == service_db_id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during test case creation: service_id={service_id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            from app.models.chain import TestCase
            test_case = TestCase(suite_id=db_test_suite.id, service_id=service_db_id, **test_case_data)

            session.add(test_case)
            session.commit()
            session.refresh(test_case)
            logger.info(f"Test case {test_case.id} created successfully for suite {suite_id}.")

            from app.schemas.test_schemas import TestCase
            return TestCase.from_orm(test_case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test case for suite {suite_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating test case: {str(e)}")

@router.put("/{service_id}/test-cases/{case_id}", response_model=TestCase)
async def update_test_case(
    service_id: str,
    case_id: str,
    updated_test_case_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースを更新するAPIエンドポイント
    """
    logger.info(f"Updating test case {case_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test case update.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during update: service_id={service_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            for key, value in updated_test_case_data.items():
                if hasattr(db_test_case, key):
                    setattr(db_test_case, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute in TestCase: {key}")

            session.add(db_test_case)
            session.commit()
            session.refresh(db_test_case)
            logger.info(f"Test case {case_id} updated successfully.")

            from app.schemas.test_schemas import TestCase
            return TestCase.from_orm(db_test_case)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test case {case_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating test case: {str(e)}")

@router.delete("/{service_id}/test-cases/{case_id}", response_model=Message)
async def delete_test_case(
    service_id: str,
    case_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test case: service_id={service_id}, case_id={case_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test case deletion.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during deletion: service_id={service_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            session.delete(db_test_case)
            session.commit()
            logger.info(f"Test case {case_id} for service {service_id} deleted from database.")

        return {"message": f"Test case {case_id} for service {service_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test case {case_id} for service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test case: {str(e)}")

@router.get("/{service_id}/test-cases/{case_id}/test-steps", response_model=List[TestStep])
async def list_test_steps_for_case(
    service_id: str,
    case_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースに紐づくテストステップ一覧を取得するAPIエンドポイント
    """
    logger.info(f"Listing test steps for case {case_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test step listing for case.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during test step listing: service_id={service_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            test_steps = db_test_case.test_steps

            from app.schemas.test_schemas import TestStep
            return JSONResponse(content=[TestStep.from_orm(ts).model_dump() for ts in test_steps])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing test steps for case {case_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing test steps for case: {str(e)}")

@router.get("/{service_id}/test-steps/{step_id}", response_model=TestStep)
async def get_test_step_detail(
    service_id: str,
    step_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストステップの詳細を取得するAPIエンドポイント
    """
    logger.info(f"Fetching test step details for step {step_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test step detail fetch.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestStep
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.service_id == service_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                logger.warning(f"Test step not found in DB during detail fetch: service_id={service_id}, step_id={step_id}")
                raise HTTPException(status_code=404, detail="Test step not found")

            from app.schemas.test_schemas import TestStep
            return JSONResponse(content=TestStep.from_orm(db_test_step).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test step details for step {step_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test step details: {str(e)}")

@router.post("/{service_id}/test-cases/{case_id}/test-steps", response_model=TestStep)
async def create_test_step(
    service_id: str,
    case_id: str,
    test_step_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースに新しいテストステップを作成するAPIエンドポイント
    """
    logger.info(f"Creating new test step for case {case_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test step creation.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                logger.warning(f"Test case not found in DB during test step creation: service_id={service_id}, case_id={case_id}")
                raise HTTPException(status_code=404, detail="Test case not found")

            from app.models.chain import TestStep
            test_step = TestStep(case_id=db_test_case.id, service_id=service_db_id, **test_step_data)

            session.add(test_step)
            session.commit()
            session.refresh(test_step)
            logger.info(f"Test step {test_step.id} created successfully for case {case_id}.")

            from app.schemas.test_schemas import TestStep
            return TestStep.from_orm(test_step)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test step for case {case_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating test step: {str(e)}")

@router.put("/{service_id}/test-steps/{step_id}", response_model=TestStep)
async def update_test_step(
    service_id: str,
    step_id: str,
    updated_test_step_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストステップを更新するAPIエンドポイント
    """
    logger.info(f"Updating test step {step_id} in service {service_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test step update.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestStep
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.service_id == service_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                logger.warning(f"Test step not found in DB during update: service_id={service_id}, step_id={step_id}")
                raise HTTPException(status_code=404, detail="Test step not found")

            for key, value in updated_test_step_data.items():
                if hasattr(db_test_step, key):
                    setattr(db_test_step, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute in TestStep: {key}")

            session.add(db_test_step)
            session.commit()
            session.refresh(db_test_step)
            logger.info(f"Test step {step_id} updated successfully.")

            from app.schemas.test_schemas import TestStep
            return TestStep.from_orm(db_test_step)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating test step {step_id} in service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating test step: {str(e)}")

@router.delete("/{service_id}/test-steps/{step_id}", response_model=Message)
async def delete_test_step(
    service_id: str,
    step_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストステップを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test step: service_id={service_id}, step_id={step_id}")
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.service_id == service_id))
            if service_db_id is None:
                 logger.error(f"Service with service_id {service_id} not found in database during test step deletion.")
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.chain import TestStep
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.service_id == service_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                logger.warning(f"Test step not found in DB during deletion: service_id={service_id}, step_id={step_id}")
                raise HTTPException(status_code=404, detail="Test step not found")

            session.delete(db_test_step)
            session.commit()
            logger.info(f"Test step {step_id} for service {service_id} deleted from database.")

        return {"message": f"Test step {step_id} for service {service_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test step {step_id} for service {service_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test step: {str(e)}")
