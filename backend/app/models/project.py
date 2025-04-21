from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
from .base import TimestampModel

class Project(TimestampModel, table=True):
    """プロジェクトモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True, unique=True)
    name: str
    description: Optional[str] = None
    
    # リレーションシップ
    schemas: List["Schema"] = Relationship(back_populates="project")
    test_runs: List["TestRun"] = Relationship(back_populates="project")

class Schema(TimestampModel, table=True):
    """OpenAPIスキーマモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    filename: str
    file_path: str
    content_type: str
    
    # リレーションシップ
    project: Project = Relationship(back_populates="schemas")