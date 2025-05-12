from sqlmodel import Field, Relationship
from typing import Optional, List, ForwardRef
from .base import TimestampModel

# 循環インポートを避けるために ForwardRef を使用
TestSuite = ForwardRef("TestSuite") # TestChain を TestSuite に変更
TestRun = ForwardRef("TestRun") # TestRun はそのまま
Endpoint = ForwardRef("Endpoint") # Endpoint はそのまま

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
    # 新しいリレーションシップ
    test_suites: List["TestSuite"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"}) # test_chains を test_suites に変更, TestChain を TestSuite に変更
    test_runs: List["TestRun"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "delete, all"}) # chain_runs を test_runs に変更, ChainRun を TestRun に変更
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