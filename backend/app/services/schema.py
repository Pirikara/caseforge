import os
from pathlib import Path
from typing import List, Optional
from app.services.rag import index_schema
from app.config import settings
from app.logging_config import logger

def save_and_index_schema(project_id: str, content: bytes, filename: str) -> None:
    """
    OpenAPIスキーマを保存し、RAG用にインデックスする
    
    Args:
        project_id: プロジェクトID
        content: スキーマファイルの内容
        filename: スキーマファイルの名前
    """
    try:
        os.makedirs(f"{settings.SCHEMA_DIR}/{project_id}", exist_ok=True)
        save_path = f"{settings.SCHEMA_DIR}/{project_id}/{filename}"

        with open(save_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Saved schema file for project {project_id}: {filename}")
        
        # RAG用にインデックス
        index_schema(project_id, save_path)
        logger.info(f"Indexed schema for project {project_id}")
    except Exception as e:
        logger.error(f"Error saving and indexing schema for project {project_id}: {e}")
        raise

def list_projects() -> List[str]:
    """
    保存されたスキーマのディレクトリからプロジェクト一覧を取得
    
    Returns:
        プロジェクトIDのリスト
    """
    try:
        schema_root = Path(settings.SCHEMA_DIR)
        if not schema_root.exists():
            logger.debug("Schema directory does not exist")
            return []

        projects = [p.name for p in schema_root.iterdir() if p.is_dir()]
        logger.debug(f"Found {len(projects)} projects")
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return []

def create_project(project_id: str) -> None:
    """
    新しいプロジェクトを作成する
    
    Args:
        project_id: プロジェクトID
    """
    try:
        path = os.path.join(settings.SCHEMA_DIR, project_id)
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created new project directory: {project_id}")
        else:
            logger.debug(f"Project directory already exists: {project_id}")
    except Exception as e:
        logger.error(f"Error creating project {project_id}: {e}")
        raise