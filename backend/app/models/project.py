from sqlmodel import Field, Relationship
from typing import Optional, List, ForwardRef
from .base import TimestampModel

# 循環インポートを避けるために ForwardRef を使用
TestRun = ForwardRef("TestRun")
TestChain = ForwardRef("TestChain")
ChainRun = ForwardRef("ChainRun")
Endpoint = ForwardRef("Endpoint")

class Project(TimestampModel, table=True):
    __tablename__ = "project"
    """プロジェクトモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True, unique=True)
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = Field(default=None)

    # リレーションシップ
    schemas: List["Schema"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"})
    # 既存のリレーションシップ（廃止予定）
    test_runs: List["TestRun"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"})
    # 新しいリレーションシップ
    test_chains: List["TestChain"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"})
    chain_runs: List["ChainRun"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"})
    # エンドポイント管理のリレーションシップ
    endpoints: List["Endpoint"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"})

class Schema(TimestampModel, table=True):
    """OpenAPIスキーマモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    filename: str
    file_path: str
    content_type: str
    
    # リレーションシップ
    project: Project = Relationship(back_populates="schemas")