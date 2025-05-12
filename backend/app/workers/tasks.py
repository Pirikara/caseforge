import warnings
import functools
from app.workers import celery_app
from app.services.chain_generator import DependencyAwareRAG, ChainStore
from app.services.schema import get_schema_content
from app.services.endpoint_chain_generator import EndpointChainGenerator
import json
import os
import yaml
import logging
from app.config import settings
from app.models import Endpoint, Project
from sqlmodel import select, Session
from app.models import engine
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

@celery_app.task
def generate_test_suites_task(project_id: str, error_types: Optional[List[str]] = None): # error_types 引数を追加
    """
    OpenAPIスキーマから依存関係を考慮したテストスイートを生成するCeleryタスク
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        dict: 生成結果の情報
    """
    logger.info(f"Generating test suites for project {project_id}") # ログメッセージを修正
    
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
        rag = DependencyAwareRAG(project_id, schema, error_types) # error_types を渡す
        
        # テストスイートの生成
        test_suites = rag.generate_request_chains() # メソッド名はそのまま
        logger.info(f"Successfully generated {len(test_suites)} test suites") # ログメッセージを修正
        
        # テストスイートの保存
        chain_store = ChainStore() # ChainStore の名前はそのまま
        chain_store.save_chains(project_id, test_suites) # save_chains メソッドはそのまま
        
        return {"status": "completed", "count": len(test_suites)} # count の対象を修正
        
    except Exception as e:
        logger.error(f"Error generating test suites: {e}", exc_info=True) # ログメッセージを修正, exc_info を追加
        return {"status": "error", "message": str(e)}

def deprecated(func):
    """非推奨関数を示すデコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Function {func.__name__} is deprecated and will be removed in future versions. "
            f"Use generate_test_suites_task instead.", # 警告メッセージを修正
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
    logger.warning("This function is deprecated. Use generate_test_suites_task instead.") # 警告メッセージを修正
    
    # 新しいタスクを呼び出す
    return generate_test_suites_task(project_id, None) # error_types は渡さない (廃止予定のため)

@celery_app.task
def generate_test_suites_for_endpoints_task(project_id: str, endpoint_ids: List[str], error_types: Optional[List[str]] = None) -> Dict:
    """
    選択したエンドポイントからテストスイートを生成するタスク
    
    Args:
        project_id: プロジェクトID
        endpoint_ids: 選択したエンドポイントIDのリスト
        
    Returns:
        生成結果
    """
    logger.info(f"Starting test suite generation for selected endpoints in project {project_id}")
    try:
        with Session(engine) as session:
            project_query = select(Project).where(Project.project_id == project_id)
            db_project = session.exec(project_query).first()
            
            if not db_project:
                logger.error(f"Project not found: {project_id}")
                return {"status": "error", "message": "Project not found"}
            
            # 取得したプロジェクトのIDをログ出力 (デバッグ用)
            logger.info(f"Found project with project_id (str): {project_id} and database id (int): {db_project.id}")

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

            # エンドポイントごとにテストスイートを生成
            generated_suites_count = 0 # generated_chains_count を generated_suites_count に変更
            all_generated_suites = [] # all_generated_chains を all_generated_suites に変更
            
            logger.info(f"Generating test suites for {len(selected_endpoints)} selected endpoints") # ログメッセージを修正
            # EndpointChainGeneratorを初期化
            generator = EndpointChainGenerator(project_id, selected_endpoints, schema, error_types) # error_types を渡す
            
            # 各エンドポイントに対してテストスイートを生成
            generated_suites = generator.generate_chains() # generate_chains はそのまま
            logger.info(f"Generated {len(generated_suites)} test suites for selected endpoints") # ログメッセージを修正
            # 生成されたテストスイートの詳細をログに出力
            logger.info(f"Generated {len(generated_suites)} test suites for {len(selected_endpoints)} endpoints") # ログメッセージを修正
            for i, suite in enumerate(generated_suites): # chain を suite に変更
                logger.info(f"TestSuite {i+1}: {suite.get('name')} with {len(suite.get('test_cases', []))} test cases") # ログメッセージを修正
                # 生成されたテストスイートの中身の一部をログに出力 (デバッグ用)
                if suite.get('test_cases'):
                    first_case = suite['test_cases'][0]
                    logger.info(f"  First TestCase: {first_case.get('name')} with {len(first_case.get('test_steps', []))} steps")
                    if first_case.get('test_steps'):
                        first_step = first_case['test_steps'][0]
                        logger.info(f"    First TestStep: {first_step.get('method')} {first_step.get('path')}")

            if generated_suites:
                logger.info(f"Saving {len(generated_suites)} test suites to the database. Project ID: {project_id}") # ログメッセージを修正
                # 生成されたテストスイートをデータベースに保存
                chain_store = ChainStore() # ChainStore の名前はそのまま
                # overwrite=Falseを指定して既存のテストスイートを上書きしないようにする
                chain_store.save_chains(session, project_id, generated_suites, overwrite=False) # session 引数を追加
                generated_suites_count = len(generated_suites) # generated_chains_count を generated_suites_count に変更
                logger.info(f"Successfully generated and saved {generated_suites_count} test suites") # ログメッセージを修正

        if generated_suites_count == 0: # generated_chains_count を generated_suites_count に変更
                return {"status": "warning", "message": "No test suites were generated for the selected endpoints."} # メッセージを修正

        return {"status": "success", "message": f"Successfully generated and saved {generated_suites_count} test suites."} # メッセージを修正

    except Exception as e:
        logger.error(f"Error generating test suites for project {project_id}: {e}", exc_info=True) # ログメッセージを修正
        # タスク全体の失敗時はロールバック
        try:
            session.rollback()
            logger.info("Session rolled back successfully due to task error")
        except Exception as rollback_error:
            logger.error(f"Error rolling back session after task error: {rollback_error}")
        return {"status": "error", "message": str(e)}
