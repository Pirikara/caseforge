from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from app.services.schema import save_and_index_schema, get_schema_content
from app.services.runner import get_recent_runs
from app.services.chain_generator import ChainStore
from app.services.chain_runner import run_test_suites, list_test_runs, get_test_run
from app.services.openapi.parser import EndpointParser
from app.workers.tasks import generate_test_suites_task, generate_test_suites_for_endpoints_task
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

def get_service_or_404(id: int) -> Path:
    """
    サービスの存在を確認し、存在しない場合は404エラーを発生させる
    
    Args:
        id: サービスID
        
    Returns:
        サービスのパス
        
    Raises:
        HTTPException: サービスが存在しない場合
    """
    service_path = path_manager.get_schema_dir(str(id))
    if not path_manager.exists(service_path):
        logger.error(f"Service directory not found: {service_path}")
        raise HTTPException(status_code=404, detail=f"Service {id} not found")
    return service_path

def get_schema_files_or_400(id: int = None, service_path: Path = Depends(get_service_or_404)) -> list:
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
        raise HTTPException(status_code=400, detail="No schema files found for this service. Please upload a schema first.")
    return schema_files

@router.get("/{id}/schema")
async def get_schema(id: int, service_path: Path = Depends(get_service_or_404)):
    """
    サービスのスキーマを取得する
    
    Args:
        id: サービスID
        service_path: サービスのパス
        
    Returns:
        スキーマの内容
    """
    logger.info(f"Getting schema for service {id}")
    try:
        schema_files = list(service_path.glob("*.yaml")) + list(service_path.glob("*.yml")) + list(service_path.glob("*.json"))
        if not schema_files:
            raise HTTPException(status_code=404, detail="No schema files found for this service")
        
        latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
        
        content = get_schema_content(str(id), latest_schema.name)
        
        content_type = "application/json" if latest_schema.name.endswith(".json") else "application/x-yaml"
        
        return {
            "filename": latest_schema.name,
            "content": content,
            "content_type": content_type
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Schema file not found: {str(e)}")

@router.post("/{id}/schema")
async def upload_schema(id: int, file: UploadFile = File(...)):
    logger.info(f"Uploading schema for service {id}: {file.filename}")
    try:
        if file.content_type not in ["application/json", "application/x-yaml", "text/yaml"]:
            logger.warning(f"Invalid content type for schema upload: {file.content_type}")
            raise HTTPException(status_code=400, detail="Invalid content type")
        contents = await file.read()
        await save_and_index_schema(str(id), contents, file.filename)
        logger.info(f"Schema uploaded and indexed successfully for service {id}")
        return {"message": "Schema uploaded and indexed successfully."}
    except Exception as e:
        logger.error(f"Error uploading schema for service {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error uploading schema: {str(e)}")

@router.post("/{id}/generate-tests")
async def generate_tests(
    id: int,
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
        id: サービスID
        service_path: サービスのパス (Depends)
        schema_files: スキーマファイルのリスト (Depends)
        endpoint_ids: 生成対象のエンドポイントIDのリスト (Optional)
        
    Returns:
        dict: 生成タスクの情報
    """
    logger.info(f"Triggering test suite generation for service {id}")
    
    try:
        if endpoint_ids:
            logger.info(f"Generating test suites for selected endpoints: {endpoint_ids} with error types: {error_types}")
            task_id = generate_test_suites_for_endpoints_task.delay(str(id), endpoint_ids, error_types).id
            task_type = "endpoints"
        else:
            logger.info(f"Generating test suites from entire schema with error types: {error_types}.")
            task_id = generate_test_suites_task.delay(str(id), error_types).id
            task_type = "full_schema"
            
        if not task_id:
            logger.error(f"Failed to trigger test suite generation task for service {id}")
            raise HTTPException(status_code=500, detail="Failed to start test suite generation task")
            
        logger.info(f"Test suite generation task ({task_type}) started with ID: {task_id}")
        return {"message": f"Test suite generation ({task_type}) started", "task_id": task_id, "status": "generating"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating test suites: {str(e)}")

@router.get("/{id}/test-suites", response_model=List[TestSuite])
async def get_test_suites(
    id: int,
    session: Session = Depends(get_session),
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching test suites for service {id}")
    try:
        chain_store = ChainStore()
        test_suites = chain_store.list_test_suites(session, str(id))
        return JSONResponse(content=test_suites)
    except Exception as e:
        logger.error(f"Error fetching test suites for service {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching test suites: {str(e)}")

@router.get("/{id}/test-suites/{suite_id}", response_model=TestSuiteWithCasesAndSteps)
async def get_test_suite_detail(
    id: int,
    suite_id: str,
    session: Session = Depends(get_session),
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching test suite details for service {id}, suite {suite_id}")
    try:
        chain_store = ChainStore()
        test_suite = chain_store.get_test_suite(session, str(id), suite_id)
        if test_suite is None:
            logger.warning(f"Test suite not found: service {id}, suite {suite_id}")
            raise HTTPException(status_code=404, detail="Test suite not found")
        return JSONResponse(content=test_suite)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching test suite details for service {id}, suite {suite_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching test suite details: {str(e)}")

@router.delete("/{id}/test-suites/{suite_id}", response_model=Message)
async def delete_test_suite(
    id: int,
    suite_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    テストスイートを削除するAPIエンドポイント
    """
    logger.info(f"Deleting test suite: id={id}, suite_id={suite_id}")
    try:
        with Session(engine) as session:
            from app.models.test.suite import TestSuite

            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.service_id == id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                logger.warning(f"Test suite not found in DB during deletion: id={id}, suite_id={suite_id}")
                raise HTTPException(status_code=404, detail="Test suite not found")

            session.delete(db_test_suite)
            session.commit()
            logger.info(f"Test suite {suite_id} for service {id} and related data deleted from database.")

        # ChainStore にファイルシステム上のテストスイートデータ削除機能があれば呼び出す
        # ChainStore の実装を確認する必要があるが、一旦スキップ
        # chain_store = ChainStore()
        # chain_store.delete_test_suite(str(id), suite_id)

        return {"message": f"Test suite {suite_id} for service {id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting test suite {suite_id} for service {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting test suite: {str(e)}")

@router.get("/{id}/test-cases")
async def get_test_cases(
    id: int,
    service_path: Path = Depends(get_service_or_404)
):
    """
    サービスのテストケース一覧を取得する
    
    Args:
        id: サービスID
        service_path: サービスのパス
        
    Returns:
        テストケースのリスト
    """
    logger.info(f"Getting test cases for service {id}")
    try:
        chain_store = ChainStore()
        test_suites = chain_store.list_test_suites(str(id))
        
        test_cases = []
        for suite in test_suites:
            if "test_cases" in suite:
                test_cases.extend(suite["test_cases"])
                
        return JSONResponse(content=test_cases)
    except Exception as e:
        logger.error(f"Error getting test cases for service {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting test cases: {str(e)}")
    
@router.post("/{id}/run-test-suites", response_model=TestRunTriggered)
async def run_test_suites_endpoint(
    id: int,
    suite_id: str = None,
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Running test suites for service {id}")
    try:
        results = await run_test_suites(str(id), suite_id)
        logger.info(f"Test suite run completed for service {id}")
        
        return {
            "message": "Test suite run complete",
            "task_id": None,
            "status": "completed"
        }
    except Exception as e:
        logger.error(f"Error running test suites for service {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error running test suites: {str(e)}")

@router.get("/{id}/runs", response_model=List[TestRunSummary])
async def get_run_history(
    id: int,
    limit: int = 10,
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching run history for service {id}")
    try:
        return list_test_runs(str(id), limit)
    except Exception as e:
        logger.error(f"Error fetching run history for service {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching run history: {str(e)}")

@router.get("/{id}/runs/{run_id}", response_model=TestRunWithResults)
async def get_run_detail(
    id: int,
    run_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    logger.info(f"Fetching run details for service {id}, run {run_id}")
    try:
        result = get_test_run(str(id), run_id)
        if result is None:
            logger.warning(f"Test run not found: service {id}, run {run_id}")
            raise HTTPException(status_code=404, detail="Test run not found")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching run details for service {id}, run {run_id}: {e}")
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
        # サービス作成時に service_id は不要になったため、ファイルシステムチェックは id で行う
        # ただし、id は DB 登録後に確定するため、ここではチェックしない
        # ファイルシステムディレクトリの作成は DB 登録後に行う
        
        from app.services.schema import create_service as db_create_service
        result = await db_create_service(
            name=service.name,
            description=service.description,
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=409, detail=result.get("message", "Service already exists"))
        
        # The result now contains the integer ID from the database
        created_service_id = result.get("id")
        logger.info(f"Created new service with ID: {created_service_id}")
        
        # Create the filesystem directory using the new integer ID
        # ファイルシステム上のディレクトリは int 型の ID を文字列に変換して使用
        path_manager.get_schema_dir(str(created_service_id)).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created service directory for ID: {created_service_id}")
        
        return {"status": "created", "id": created_service_id, "name": service.name, "description": service.description}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating service: {str(e)}")

@router.put("/{id}")
async def update_service(id: int, updated_service_data: dict = Body(...)):
    """
    サービスを更新するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_query = select(Service).where(Service.id == id)
            db_service = session.exec(service_query).first()

            if not db_service:
                logger.warning(f"Service not found in DB during update: {id}")
                raise HTTPException(status_code=404, detail="Service not found")

            for key, value in updated_service_data.items():
                if hasattr(db_service, key):
                    setattr(db_service, key, value)
                else:
                    logger.warning(f"Attempted to update non-existent attribute: {key}")


            session.add(db_service)
            session.commit()
            session.refresh(db_service)
            logger.info(f"Service {id} updated successfully.")

            return {
                "id": db_service.id,
                "name": db_service.name,
                "description": db_service.description,
                "base_url": db_service.base_url,
                "created_at": db_service.created_at.isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating service: {str(e)}")


@router.delete("/{id}")
async def delete_service(id: int, service_path: Path = Depends(get_service_or_404)):
    """
    サービスを削除するAPIエンドポイント
    """
    try:
        # データベースからサービスを削除 (カスケード設定により関連データも削除される)
        with Session(engine) as session:
            service_query = select(Service).where(Service.id == id)
            db_service = session.exec(service_query).first()

            if not db_service:
                raise HTTPException(status_code=404, detail="Service not found")

            session.delete(db_service)
            session.commit()
            logger.info(f"Service {id} and related data deleted from database.")

        import shutil
        shutil.rmtree(service_path)
        logger.info(f"Service directory {service_path} deleted from file system.")

        return {"message": f"Service {id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting service: {str(e)}")

@router.post("/{id}/endpoints/import")
async def import_endpoints(id: int, service_path: Path = Depends(get_service_or_404)):
    """
    スキーマからエンドポイントを抽出してDBに一括登録する
    
    Args:
        id: サービスID
        service_path: サービスのパス
    """
    logger.info(f"Importing endpoints for service {id}")
    try:
        schema_files = list(service_path.glob("*.yaml")) + list(service_path.glob("*.yml")) + list(service_path.glob("*.json"))
        if not schema_files:
            raise HTTPException(status_code=400, detail="No schema files found for this service. Please upload a schema first.")

        latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"Using latest schema file for import: {latest_schema.name}")

        content = get_schema_content(str(id), latest_schema.name)
        parser = EndpointParser(content)
        endpoints_data = parser.parse_endpoints(str(id))

        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is not None:
                delete_statement = delete(Endpoint).where(Endpoint.service_id == service_db_id)
                session.exec(delete_statement)
                session.commit()
            else:
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

            if updated_endpoints:
                try:
                    dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in updated_endpoints]
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
        raise HTTPException(status_code=500, detail=f"Error importing endpoints: {str(e)}")

@router.get("/{id}/endpoints")
async def list_endpoints(
    id: int,
    service_path: Path = Depends(get_service_or_404)
):
    """
    サービスのエンドポイント一覧を取得する
    
    Args:
        id: サービスID
        service_path: サービスのパス
        
    Returns:
        エンドポイントのリスト
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")
            
            endpoints = sorted(session.exec(select(Endpoint).where(Endpoint.service_id == service_db_id)).all(), key=lambda ep: (ep.path, ep.method))

            dumped_endpoints = [EndpointSchema.from_orm(ep).model_dump() for ep in endpoints]
            json_compatible_endpoints = [convert_datetime_to_iso(ep_dict) for ep_dict in dumped_endpoints]
            return JSONResponse(content=json_compatible_endpoints)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing endpoints: {str(e)}")

@router.post("/{id}/endpoints/generate-suite")
async def generate_test_suite_for_endpoints(
    id: int,
    endpoint_ids: List[int] = Body(..., description="テストスイートを生成するエンドポイントのIDのリスト"),
    service_path: Path = Depends(get_service_or_404)
):
    """
    指定されたエンドポイントIDに基づいてテストスイートを生成するAPIエンドポイント。
    """
    try:
        task_id = generate_test_suites_for_endpoints_task.delay(id, endpoint_ids).id

        if not task_id:
            raise HTTPException(status_code=500, detail="Failed to start test suite generation task")

        logger.info(f"Test suite generation task for endpoints started with ID: {task_id}")
        return {"message": "Test suite generation for endpoints started", "task_id": task_id, "status": "generating"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating test suite for endpoints: {str(e)}")

@router.get("/{id}/test-suites/{suite_id}/test-cases", response_model=List[TestCase])
async def list_test_cases_for_suite(
    id: int,
    suite_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストスイートに紐づくテストケース一覧を取得するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.suite import TestSuite
            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.service_id == service_db_id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                raise HTTPException(status_code=404, detail="Test suite not found")

            test_cases = db_test_suite.test_cases

            from app.schemas.test_schemas import TestCase
            return JSONResponse(content=[TestCase.from_orm(tc).model_dump() for tc in test_cases])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing test cases for suite: {str(e)}")

@router.get("/{id}/test-cases/{case_id}", response_model=TestCaseWithSteps)
async def get_test_case_detail(
    id: int,
    case_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースの詳細を取得するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.case import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                raise HTTPException(status_code=404, detail="Test case not found")

            from app.schemas.test_schemas import TestCaseWithSteps
            return JSONResponse(content=TestCaseWithSteps.from_orm(db_test_case).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test case details: {str(e)}")

@router.post("/{id}/test-suites/{suite_id}/test-cases", response_model=TestCase)
async def create_test_case(
    id: int,
    suite_id: str,
    test_case_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストスイートに新しいテストケースを作成するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.suite import TestSuite
            test_suite_query = select(TestSuite).where(
                TestSuite.id == suite_id,
                TestSuite.service_id == service_db_id
            )
            db_test_suite = session.exec(test_suite_query).first()

            if not db_test_suite:
                raise HTTPException(status_code=404, detail="Test suite not found")

            from app.models.test.case import TestCase
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
        raise HTTPException(status_code=500, detail=f"Error creating test case: {str(e)}")

@router.put("/{id}/test-cases/{case_id}", response_model=TestCase)
async def update_test_case(
    id: int,
    case_id: str,
    updated_test_case_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースを更新するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.case import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
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
        raise HTTPException(status_code=500, detail=f"Error updating test case: {str(e)}")

@router.delete("/{id}/test-cases/{case_id}", response_model=Message)
async def delete_test_case(
    id: int,
    case_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースを削除するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.case import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                raise HTTPException(status_code=404, detail="Test case not found")

            session.delete(db_test_case)
            session.commit()

        return {"message": f"Test case {case_id} for service {id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting test case: {str(e)}")

@router.get("/{id}/test-cases/{case_id}/test-steps", response_model=List[TestStep])
async def list_test_steps_for_case(
    id: int,
    case_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースに紐づくテストステップ一覧を取得するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.case import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                raise HTTPException(status_code=404, detail="Test case not found")

            test_steps = db_test_case.test_steps

            from app.schemas.test_schemas import TestStep
            return JSONResponse(content=[TestStep.from_orm(ts).model_dump() for ts in test_steps])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing test steps for case: {str(e)}")

@router.get("/{id}/test-steps/{step_id}", response_model=TestStep)
async def get_test_step_detail(
    id: int,
    step_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストステップの詳細を取得するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.step import TestStep
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.service_id == service_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                raise HTTPException(status_code=404, detail="Test step not found")

            from app.schemas.test_schemas import TestStep
            return JSONResponse(content=TestStep.from_orm(db_test_step).model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching test step details: {str(e)}")

@router.post("/{id}/test-cases/{case_id}/test-steps", response_model=TestStep)
async def create_test_step(
    id: int,
    case_id: str,
    test_step_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストケースに新しいテストステップを作成するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.case import TestCase
            test_case_query = select(TestCase).where(
                TestCase.id == case_id,
                TestCase.service_id == service_db_id
            )
            db_test_case = session.exec(test_case_query).first()

            if not db_test_case:
                raise HTTPException(status_code=404, detail="Test case not found")

            from app.models.test.step import TestStep
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
        raise HTTPException(status_code=500, detail=f"Error creating test step: {str(e)}")

@router.put("/{id}/test-steps/{step_id}", response_model=TestStep)
async def update_test_step(
    id: int,
    step_id: str,
    updated_test_step_data: dict = Body(...),
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストステップを更新するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.step import TestStep
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.service_id == service_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
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
        raise HTTPException(status_code=500, detail=f"Error updating test step: {str(e)}")

@router.delete("/{id}/test-steps/{step_id}", response_model=Message)
async def delete_test_step(
    id: str,
    step_id: str,
    service_path: Path = Depends(get_service_or_404)
):
    """
    特定のテストステップを削除するAPIエンドポイント
    """
    try:
        with Session(engine) as session:
            service_db_id = session.scalar(select(Service.id).where(Service.id == id))
            if service_db_id is None:
                 raise HTTPException(status_code=404, detail="Service not found in database.")

            from app.models.test.step import TestStep
            test_step_query = select(TestStep).where(
                TestStep.id == step_id,
                TestStep.service_id == service_db_id
            )
            db_test_step = session.exec(test_step_query).first()

            if not db_test_step:
                raise HTTPException(status_code=404, detail="Test step not found")

            session.delete(db_test_step)
            session.commit()

        return {"message": f"Test step {step_id} for service {id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting test step: {str(e)}")
