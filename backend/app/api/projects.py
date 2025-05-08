from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Body
from app.services.schema import save_and_index_schema, get_schema_content
from app.services.runner import get_recent_runs
from app.services.chain_generator import ChainStore
from app.services.chain_runner import run_chains, list_chain_runs, get_chain_run
from app.services.endpoint_parser import EndpointParser
from app.workers.tasks import generate_chains_task, generate_chains_for_endpoints_task
from fastapi.responses import JSONResponse
from pathlib import Path
from app.config import settings
from app.logging_config import logger
from app.schemas.project import ProjectCreate
from app.models import Endpoint, Project, engine
from sqlmodel import select, Session
from typing import List, Optional
import json

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
    schema_files: list = Depends(get_schema_files_or_400), # スキーマファイルの存在チェックのために残す
    endpoint_ids: Optional[List[str]] = Body(None, description="生成対象のエンドポイントIDのリスト。指定しない場合はスキーマ全体から生成します。")
):
    """
    プロジェクトのテストチェーンを生成するAPIエンドポイント。
    エンドポイントIDのリストが指定された場合は、それらのエンドポイントごとにチェーンを生成します。
    指定されない場合は、スキーマ全体から依存関係を考慮したチェーンを生成します。
    
    Args:
        project_id: プロジェクトID
        project_path: プロジェクトのパス (Depends)
        schema_files: スキーマファイルのリスト (Depends)
        endpoint_ids: 生成対象のエンドポイントIDのリスト (Optional)
        
    Returns:
        dict: 生成タスクの情報
    """
    logger.info(f"Triggering test chain generation for project {project_id}")
    
    try:
        if endpoint_ids:
            # エンドポイントIDが指定された場合、エンドポイントごとの生成タスクを呼び出す
            logger.info(f"Generating chains for selected endpoints: {endpoint_ids}")
            task_id = generate_chains_for_endpoints_task.delay(project_id, endpoint_ids).id
            task_type = "endpoints"
        else:
            # エンドポイントIDが指定されない場合、スキーマ全体からの生成タスクを呼び出す (既存の挙動)
            logger.info("Generating chains from entire schema.")
            task_id = generate_chains_task.delay(project_id).id
            task_type = "full_schema"
            
        if not task_id:
            logger.error(f"Failed to trigger test chain generation task for project {project_id}")
            raise HTTPException(status_code=500, detail="Failed to start test chain generation task")
            
        logger.info(f"Test chain generation task ({task_type}) started with ID: {task_id}")
        return {"message": f"Test chain generation ({task_type}) started", "task_id": task_id, "status": "generating"}
        
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

@router.delete("/{project_id}/chains/{chain_id}")
async def delete_chain(
    project_id: str,
    chain_id: str,
    project_path: Path = Depends(get_project_or_404) # プロジェクトの存在確認
):
    """
    テストチェーンを削除するAPIエンドポイント
    """
    logger.info(f"Deleting chain: project_id={project_id}, chain_id={chain_id}")
    try:
        # データベースからテストチェーンを削除 (カスケード設定により関連データも削除される)
        with Session(engine) as session:
            # project_id と chain_id を使用して TestChain を検索
            # TestChain モデルには project_id (int) と chain_id (str) がある
            # project_id (int) は Project モデルとのリレーションシップに使われるDB上のID
            # chain_id (str) はユーザーに見せるユニークなID
            # ここでは chain_id (str) を使用して検索する
            from app.models.chain import TestChain # TestChain モデルをインポート

            chain_query = select(TestChain).where(
                TestChain.chain_id == chain_id,
                TestChain.project_id == session.scalar(select(Project.id).where(Project.project_id == project_id))
            )
            db_chain = session.exec(chain_query).first()

            if not db_chain:
                logger.warning(f"Chain not found in DB during deletion: project_id={project_id}, chain_id={chain_id}")
                raise HTTPException(status_code=404, detail="Chain not found")

            session.delete(db_chain)
            session.commit()
            logger.info(f"Chain {chain_id} for project {project_id} and related data deleted from database.")

        # ChainStore にファイルシステム上のチェーンデータ削除機能があれば呼び出す
        # ChainStore の実装を確認する必要があるが、一旦スキップ

        return {"message": f"Chain {chain_id} for project {project_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chain {chain_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting chain: {str(e)}")

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

    except HTTPException:
        raise
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
        
    Returns:
        インポート結果
    """
    logger.info(f"Importing endpoints for project {project_id}")
    try:
        # プロジェクトの取得
        with Session(engine) as session:
            project_query = select(Project).where(Project.project_id == project_id)
            db_project = session.exec(project_query).first()
            
            if not db_project:
                logger.error(f"Project not found: {project_id}")
                raise HTTPException(status_code=404, detail="Project not found")
            
            logger.info(f"Found project: {db_project.name} (ID: {db_project.id}, project_id: {db_project.project_id})")
            
            # スキーマファイルの取得
            schema_files = list(project_path.glob("*.yaml")) + list(project_path.glob("*.yml")) + list(project_path.glob("*.json"))
            if not schema_files:
                logger.error(f"No schema files found in project directory: {project_path}")
                raise HTTPException(status_code=400, detail="No schema files found for this project")
            
            logger.info(f"Found schema files: {[f.name for f in schema_files]}")
            
            # 最新のスキーマファイルを取得
            latest_schema = max(schema_files, key=lambda x: x.stat().st_mtime)
            logger.info(f"Found latest schema file: {latest_schema.name}")
            
            # スキーマファイルの内容を取得
            try:
                with open(latest_schema, "r") as f:
                    schema_content = f.read()
                logger.info(f"Read schema content: {len(schema_content)} characters")
            except Exception as e:
                logger.error(f"Error reading schema file: {e}")
                raise HTTPException(status_code=500, detail=f"Error reading schema file: {str(e)}")
            
            # エンドポイントのパース
            try:
                parser = EndpointParser(schema_content)
                endpoints = parser.parse_endpoints(db_project.id)
                logger.info(f"Parsed {len(endpoints)} endpoints from schema")
                
                # デバッグ用に最初の数個のエンドポイントを出力
                if endpoints:
                    logger.info(f"First endpoint: {endpoints[0]}")
                else:
                    logger.warning("No endpoints parsed from schema")
            except Exception as e:
                logger.error(f"Error parsing endpoints: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error parsing endpoints: {str(e)}")
            
            # 既存のエンドポイントを削除
            try:
                existing_endpoints_query = select(Endpoint).where(Endpoint.project_id == db_project.id)
                existing_endpoints = session.exec(existing_endpoints_query).all()
                
                for endpoint in existing_endpoints:
                    session.delete(endpoint)
                
                logger.info(f"Deleted {len(existing_endpoints)} existing endpoints for project {project_id}")
            except Exception as e:
                logger.error(f"Error deleting existing endpoints: {e}")
                raise HTTPException(status_code=500, detail=f"Error deleting existing endpoints: {str(e)}")
            
            # 新しいエンドポイントを登録
            try:
                for endpoint_data in endpoints:
                    # デバッグログを追加
                    logger.info(f"エンドポイントデータ（保存前）: {endpoint_data['path']} {endpoint_data['method']}")
                    logger.info(f"  - request_body: {endpoint_data['request_body'] is not None}")
                    if endpoint_data['request_body']:
                        logger.info(f"  - request_body type: {type(endpoint_data['request_body'])}")
                    logger.info(f"  - request_headers: {endpoint_data['request_headers'] is not None}")
                    if endpoint_data['request_headers']:
                        logger.info(f"  - request_headers type: {type(endpoint_data['request_headers'])}")
                    logger.info(f"  - request_query_params: {endpoint_data['request_query_params'] is not None}")
                    if endpoint_data['request_query_params']:
                        logger.info(f"  - request_query_params type: {type(endpoint_data['request_query_params'])}")
                    logger.info(f"  - responses: {endpoint_data['responses'] is not None}")
                    if endpoint_data['responses']:
                        logger.info(f"  - responses type: {type(endpoint_data['responses'])}")
                    
                    endpoint = Endpoint(
                        project_id=endpoint_data["project_id"],
                        path=endpoint_data["path"],
                        method=endpoint_data["method"],
                        summary=endpoint_data.get("summary"),
                        description=endpoint_data.get("description"),
                        request_body_str=json.dumps(endpoint_data["request_body"]) if endpoint_data.get("request_body") is not None else None,
                        request_headers_str=json.dumps(endpoint_data["request_headers"]) if endpoint_data.get("request_headers") is not None else None,
                        request_query_params_str=json.dumps(endpoint_data["request_query_params"]) if endpoint_data.get("request_query_params") is not None else None,
                        responses_str=json.dumps(endpoint_data["responses"]) if endpoint_data.get("responses") is not None else None,
                    )
                    session.add(endpoint)
                
                session.commit()
                logger.info(f"Imported {len(endpoints)} endpoints for project {project_id}")
            except Exception as e:
                logger.error(f"Error saving endpoints: {e}", exc_info=True)
                session.rollback()
                raise HTTPException(status_code=500, detail=f"Error saving endpoints: {str(e)}")
            
            return {"success": True, "imported_count": len(endpoints)}
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
            # プロジェクトの取得
            try:
                project_query = select(Project).where(Project.project_id == project_id)
                db_project = session.exec(project_query).first()
                
                if not db_project:
                    logger.error(f"Project not found: {project_id}")
                    raise HTTPException(status_code=404, detail="Project not found")
                
                logger.info(f"Found project: {db_project.name} (ID: {db_project.id}, project_id: {db_project.project_id})")
            except Exception as e:
                logger.error(f"Error retrieving project: {e}")
                raise HTTPException(status_code=500, detail=f"Error retrieving project: {str(e)}")
            
            # エンドポイントの取得
            try:
                endpoints_query = select(Endpoint).where(Endpoint.project_id == db_project.id)
                endpoints = session.exec(endpoints_query).all()
                logger.info(f"Found {len(endpoints)} endpoints for project {project_id}")
            except Exception as e:
                logger.error(f"Error querying endpoints: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error querying endpoints: {str(e)}")
            
            # レスポンスの構築
            result = []
            for endpoint in endpoints:
                try:
                    # エンドポイントの詳細情報も含める
                    endpoint_data = {
                        "id": endpoint.endpoint_id,
                        "path": endpoint.path,
                        "method": endpoint.method,
                        "summary": endpoint.summary,
                        "description": endpoint.description,
                        "request_body": endpoint.request_body,
                        "request_headers": endpoint.request_headers,
                        "request_query_params": endpoint.request_query_params,
                        "responses": endpoint.responses
                    }
                    
                    # デバッグログを追加
                    logger.info(f"エンドポイント詳細データ（取得後）: {endpoint.endpoint_id}")
                    logger.info(f"  - request_body_str: {endpoint.request_body_str is not None}")
                    if endpoint.request_body_str:
                        logger.info(f"  - request_body_str length: {len(endpoint.request_body_str)}")
                        logger.info(f"  - request_body_str sample: {endpoint.request_body_str[:100] if len(endpoint.request_body_str) > 100 else endpoint.request_body_str}")
                    logger.info(f"  - request_body: {endpoint.request_body is not None}")
                    if endpoint.request_body:
                        logger.info(f"  - request_body type: {type(endpoint.request_body)}")
                    
                    logger.info(f"  - request_headers_str: {endpoint.request_headers_str is not None}")
                    logger.info(f"  - request_headers: {endpoint.request_headers is not None}")
                    if endpoint.request_headers:
                        logger.info(f"  - request_headers type: {type(endpoint.request_headers)}")
                    
                    logger.info(f"  - request_query_params_str: {endpoint.request_query_params_str is not None}")
                    logger.info(f"  - request_query_params: {endpoint.request_query_params is not None}")
                    if endpoint.request_query_params:
                        logger.info(f"  - request_query_params type: {type(endpoint.request_query_params)}")
                    
                    logger.info(f"  - responses_str: {endpoint.responses_str is not None}")
                    logger.info(f"  - responses: {endpoint.responses is not None}")
                    if endpoint.responses:
                        logger.info(f"  - responses type: {type(endpoint.responses)}")
                    
                    result.append(endpoint_data)
                except Exception as e:
                    logger.error(f"Error processing endpoint {endpoint.endpoint_id}: {e}")
                    # 個別のエンドポイント処理エラーはスキップして続行
                    continue
            
            logger.info(f"Returning {len(result)} endpoints for project {project_id}")
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing endpoints for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing endpoints: {str(e)}")

@router.post("/{project_id}/endpoints/generate-chain")
async def generate_chain_for_endpoints(
    project_id: str,
    endpoint_ids: List[str] = Body(..., embed=True),
    overwrite: bool = Body(True), # overwrite パラメータを追加
    project_path: Path = Depends(get_project_or_404)
):
    """
    選択したエンドポイントからテストチェーンを生成する
    
    Args:
        project_id: プロジェクトID
        endpoint_ids: 選択したエンドポイントIDのリスト
        overwrite: 既存のチェーンを上書きするかどうか (デフォルト: True)
        project_path: プロジェクトのパス
        
    Returns:
        生成結果
    """
    # デバッグログを追加
    logger.info(f"Received generate chain request for endpoints: {endpoint_ids}")
    logger.info(f"Number of selected endpoints: {len(endpoint_ids)}")
    logger.info(f"Overwrite flag received: {overwrite}")
    logger.info(f"Generating chain for selected endpoints in project {project_id}")
    try:
        with Session(engine) as session:
            project_query = select(Project).where(Project.project_id == project_id)
            db_project = session.exec(project_query).first()
            
            if not db_project:
                logger.error(f"Project not found: {project_id}")
                raise HTTPException(status_code=404, detail="Project not found")
            
            # 選択されたエンドポイントの取得
            selected_endpoints = []
            for endpoint_id in endpoint_ids:
                endpoint_query = select(Endpoint).where(
                    Endpoint.project_id == db_project.id,
                    Endpoint.endpoint_id == endpoint_id
                )
                endpoint = session.exec(endpoint_query).first()
                
                if endpoint:
                    selected_endpoints.append(endpoint)
            
            if not selected_endpoints:
                logger.error(f"No valid endpoints selected for project {project_id}")
                raise HTTPException(status_code=400, detail="No valid endpoints selected")
            
            # テストチェーン生成タスクを開始
            task_id = generate_chains_for_endpoints_task.delay(
                project_id,
                [endpoint.endpoint_id for endpoint in selected_endpoints]
            ).id
            
            if not task_id:
                logger.error(f"Failed to trigger test chain generation task for project {project_id}")
                raise HTTPException(status_code=500, detail="Failed to start test chain generation task")
                
            logger.info(f"Test chain generation task started with ID: {task_id}")
            return {
                "message": "Test chain generation started",
                "task_id": task_id,
                "status": "generating",
                "endpoint_count": len(selected_endpoints)
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating chain for endpoints in project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chain: {str(e)}")
