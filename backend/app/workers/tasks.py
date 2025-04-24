from app.workers import celery_app
from app.services.teststore import save_testcases
from app.services.rag import ChromaEmbeddingFunction
from app.services.chain_generator import DependencyAwareRAG, ChainStore
from app.services.schema import get_schema_content
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
import os
import yaml
import logging
from app.config import settings

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

# 既存のテストケース生成タスク（廃止予定）
@celery_app.task
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
