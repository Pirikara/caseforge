from sqlmodel import Field, Relationship
from typing import Optional, List
from ..base import TimestampModel
from ..project import Project

class TestSuite(TimestampModel, table=True):
    __tablename__ = "testsuite"
    """テストスイートモデル（APIエンドポイント単位のテスト群）"""
    id: str = Field(index=True, primary_key=True)
    project_id: int = Field(foreign_key="project.id") 
    target_method: str
    target_path: str
    name: str
    description: Optional[str] = None
    
    # リレーションシップ
    project: Project = Relationship(back_populates="test_suites")
    test_cases: List["TestCase"] = Relationship(back_populates="test_suite", sa_relationship_kwargs={"cascade": "delete, all"})
    test_runs: List["TestRun"] = Relationship(back_populates="test_suite", sa_relationship_kwargs={"cascade": "delete, all"})
