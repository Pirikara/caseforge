import warnings
import functools
from app.workers import celery_app
from app.services.teststore import save_testcases
from app.services.chain_generator import DependencyAwareRAG, ChainStore
from app.services.schema import get_schema_content
from app.services.endpoint_chain_generator import EndpointChainGenerator
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
import os
import yaml
import logging
from app.config import settings
from app.models import Endpoint, Project
from sqlmodel import select, Session
from app.models import get_session, engine
from typing import List, Dict

logger = logging.getLogger(__name__)

@celery_app.task
def generate_chains_task(project_id: str):
    """
    OpenAPIスキーマから依存関係を考慮したリクエストチェーンを生成するCeleryタスク
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        dict: 生成結果の情報
    """
    logger.info(f"Generating request chains for project {project_id}")
    
    try:
        # スキーマファイルの取得
        schema_path = f"{settings.SCHEMA_DIR}/{project_id}"
        schema_files = [f for f in os.listdir(schema_path) if f.endswith(('.yaml', '.yml', '.json'))]
        
        if not schema_files:
            logger.error(f"No schema files found for project {project_id}")
            return {"status": "error", "message": "No schema files found"}
        
        # 最初のスキーマファイルを使用
        schema_file = schema_files[0]
        schema_content = get_schema_content(project_id, schema_file)
        
        # スキーマのパース
        if schema_file.endswith('.json'):
            schema = json.loads(schema_content)
        else:
            schema = yaml.safe_load(schema_content)
        
        # 依存関係を考慮したRAGの初期化
        rag = DependencyAwareRAG(project_id, schema)
        
        # リクエストチェーンの生成
        chains = rag.generate_request_chains()
        logger.info(f"Successfully generated {len(chains)} request chains")
        
        # チェーンの保存
        chain_store = ChainStore()
        chain_store.save_chains(project_id, chains)
        
        return {"status": "completed", "count": len(chains)}
        
    except Exception as e:
        logger.error(f"Error generating request chains: {e}")
        return {"status": "error", "message": str(e)}

def deprecated(func):
    """非推奨関数を示すデコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Function {func.__name__} is deprecated and will be removed in future versions. "
            f"Use generate_chains_task instead.",
            category=DeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return wrapper

# 既存のテストケース生成タスク（廃止予定）
@celery_app.task
@deprecated
def generate_tests_task(project_id: str):
    """
    OpenAPIスキーマからテストケースを生成するCeleryタスク（廃止予定）
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        dict: 生成結果の情報
    """
    logger.info(f"Generating tests for project {project_id} (DEPRECATED)")
    logger.warning("This function is deprecated. Use generate_chains_task instead.")
    
    # 新しいタスクを呼び出す
    return generate_chains_task(project_id)

@celery_app.task
def generate_chains_for_endpoints_task(project_id: str, endpoint_ids: List[str]) -> Dict:
    """
    選択したエンドポイントからテストチェーンを生成するタスク
    
    Args:
        project_id: プロジェクトID
        endpoint_ids: 選択したエンドポイントIDのリスト
        
    Returns:
        生成結果
    """
    logger.info(f"Starting test chain generation for selected endpoints in project {project_id}")
    try:
        with Session(engine) as session:
            project_query = select(Project).where(Project.project_id == project_id)
            db_project = session.exec(project_query).first()
            
            if not db_project:
                logger.error(f"Project not found: {project_id}")
                return {"status": "error", "message": "Project not found"}
            
            # 選択されたエンドポイントの取得
            endpoints_query = select(Endpoint).where(
                Endpoint.project_id == db_project.id,
                Endpoint.endpoint_id.in_(endpoint_ids)
            )
            selected_endpoints = session.exec(endpoints_query).all()

            if not selected_endpoints:
                logger.error(f"No valid endpoints selected for project {project_id}")
                return {"status": "error", "message": "No valid endpoints selected"}

            # スキーマファイルの取得
            schema_path = f"{settings.SCHEMA_DIR}/{project_id}"
            schema_files = [f for f in os.listdir(schema_path) if f.endswith(('.yaml', '.yml', '.json'))]
            
            if not schema_files:
                logger.error(f"No schema files found for project {project_id}")
                return {"status": "error", "message": "No schema files found"}
            
            # 最初のスキーマファイルを使用
            schema_file = schema_files[0]
            schema_content = get_schema_content(project_id, schema_file)
            
            # スキーマのパース
            if schema_file.endswith('.json'):
                schema = json.loads(schema_content)
            else:
                schema = yaml.safe_load(schema_content)

            # エンドポイントごとにテストチェーンを生成
            generated_chains_count = 0
            all_generated_chains = []
            
            logger.info(f"Generating test chains for {len(selected_endpoints)} selected endpoints")
            # EndpointChainGeneratorを初期化
            generator = EndpointChainGenerator(project_id, selected_endpoints, schema)
            
            # 各エンドポイントに対してテストチェーンを生成
            generated_chains = generator.generate_chains()
            logger.info(f"Generated {len(generated_chains)} chains for selected endpoints")
            # 生成されたチェーンの詳細をログに出力
            logger.info(f"Generated {len(generated_chains)} chains for {len(selected_endpoints)} endpoints")
            for i, chain in enumerate(generated_chains):
                logger.info(f"Chain {i+1}: {chain.get('name')} with {len(chain.get('steps', []))} steps")
            
            if generated_chains:
                # 生成されたテストチェーンをデータベースに保存
                chain_store = ChainStore()
                # overwrite=Falseを指定して既存のチェーンを上書きしないようにする
                chain_store.save_chains(project_id, generated_chains, overwrite=False)
                generated_chains_count = len(generated_chains)
                logger.info(f"Successfully generated and saved {generated_chains_count} test chains")

        if generated_chains_count == 0:
                return {"status": "warning", "message": "No test chains were generated for the selected endpoints."}

        return {"status": "success", "message": f"Successfully generated and saved {generated_chains_count} test chains."}

    except Exception as e:
        logger.error(f"Error generating test chains for project {project_id}: {e}", exc_info=True)
        # タスク全体の失敗時はロールバック
        try:
            session.rollback()
            logger.info("Session rolled back successfully due to task error")
        except Exception as rollback_error:
            logger.error(f"Error rolling back session after task error: {rollback_error}")
        return {"status": "error", "message": str(e)}
