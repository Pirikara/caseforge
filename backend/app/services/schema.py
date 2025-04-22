from app.config import settings
from app.logging_config import logger
from app.models import get_session, Project, Schema, engine
from app.services.rag import index_schema
from sqlmodel import Session, select
from fastapi import Depends
from pathlib import Path
import os
from typing import Optional
from datetime import datetime

async def save_and_index_schema(project_id: str, content: bytes, filename: str, session: Optional[Session] = None):
    """
    OpenAPIスキーマを保存し、インデックスを作成する
    
    Args:
        project_id: プロジェクトID
        content: スキーマファイルの内容
        filename: ファイル名
        session: データベースセッション
    """
    # セッションがない場合は新しいセッションを作成
    if session is None:
        session = Session(engine)
        
    try:
        # ファイルシステムへの保存
        os.makedirs(f"{settings.SCHEMA_DIR}/{project_id}", exist_ok=True)
        save_path = f"{settings.SCHEMA_DIR}/{project_id}/{filename}"
        
        with open(save_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Saved schema file for project {project_id}: {filename}")
        
        # データベースへの保存
        # プロジェクトの取得または作成
        project_query = select(Project).where(Project.project_id == project_id)
        db_project = session.exec(project_query).first()
        
        if not db_project:
            db_project = Project(project_id=project_id, name=project_id)
            session.add(db_project)
            session.commit()
            session.refresh(db_project)
            logger.info(f"Created new project in database: {project_id}")
        
        # スキーマの保存
        content_type = "application/json" if filename.endswith(".json") else "application/x-yaml"
        schema = Schema(
            project_id=db_project.id,
            filename=filename,
            file_path=save_path,
            content_type=content_type
        )
        session.add(schema)
        session.commit()
        logger.info(f"Saved schema to database for project {project_id}")
        
        # RAGインデックスの作成
        index_schema(project_id, save_path)
        logger.info(f"Indexed schema for project {project_id}")
        
        return {"message": "Schema uploaded and indexed successfully."}
    except Exception as e:
        logger.error(f"Error saving and indexing schema for project {project_id}: {e}")
        raise

async def list_projects(session: Optional[Session] = None):
    """
    プロジェクト一覧を取得する
    
    Args:
        session: データベースセッション
        
    Returns:
        プロジェクト一覧
    """
    # セッションがない場合は新しいセッションを作成
    if session is None:
        session = Session(engine)
        logger.debug(f"Created new database session for listing projects")
        
    try:
        logger.debug(f"Executing query to get all projects")
        query = select(Project)
        projects = session.exec(query).all()
        logger.info(f"Found {len(projects)} projects in database")
        
        # プロジェクトの詳細をログに出力
        for p in projects:
            logger.debug(f"Project: id={p.id}, project_id={p.project_id}, name={p.name}")
        
        result = [{"id": p.project_id, "name": p.name, "description": p.description, "created_at": p.created_at.isoformat() if p.created_at else datetime.now().isoformat()} for p in projects]
        return result
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        # ファイルシステムからプロジェクトを取得する代替手段
        try:
            logger.info("Attempting to list projects from filesystem as fallback")
            schema_dir = Path(settings.SCHEMA_DIR)
            if schema_dir.exists() and schema_dir.is_dir():
                projects = [d.name for d in schema_dir.iterdir() if d.is_dir()]
                logger.info(f"Found {len(projects)} projects in filesystem")
                # ファイルシステムからの取得では作成日時が不明なので現在時刻を使用
                now = datetime.now().isoformat()
                return [{"id": p, "name": p, "description": "", "created_at": now} for p in projects]
        except Exception as fallback_error:
            logger.error(f"Fallback error listing projects from filesystem: {fallback_error}")
        return []

async def create_project(project_id: str, name: str = None, description: str = None, session: Optional[Session] = None):
    """
    新規プロジェクトを作成する
    
    Args:
        project_id: プロジェクトID
        name: プロジェクト名（省略時はproject_idと同じ）
        description: プロジェクトの説明
        session: データベースセッション
        
    Returns:
        作成されたプロジェクト情報
    """
    # セッションがない場合は新しいセッションを作成
    if session is None:
        session = Session(engine)
        
    try:
        # プロジェクトの存在確認
        project_query = select(Project).where(Project.project_id == project_id)
        existing_project = session.exec(project_query).first()
        
        if existing_project:
            logger.debug(f"Project already exists: {project_id}")
            return {"status": "error", "message": "Project already exists"}
        
        # ディレクトリ作成
        path = os.path.join(settings.SCHEMA_DIR, project_id)
        if not os.path.exists(path):
            os.makedirs(path)
            logger.info(f"Created new project directory: {project_id}")
        
        # データベースに保存
        project = Project(
            project_id=project_id,
            name=name or project_id,
            description=description
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        logger.info(f"Created new project in database: {project_id}")
        
        return {"status": "created", "project_id": project_id, "id": project.id}
    except Exception as e:
        logger.error(f"Error creating project {project_id}: {e}")
        raise