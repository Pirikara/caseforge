from sqlmodel import Field, SQLModel, Relationship, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import TimestampModel
from .project import Project

class TestCase(TimestampModel, table=True):
    """テストケースモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    case_id: str = Field(index=True)
    project_id: int = Field(foreign_key="project.id")
    title: str
    method: str
    path: str
    request_body: Optional[Dict[str, Any]] = Field(default=None, sa_column=JSON)
    expected_status: int
    expected_response: Optional[Dict[str, Any]] = Field(default=None, sa_column=JSON)
    purpose: str  # functional, boundary, authZ, fuzz
    
    # リレーションシップ
    project: Project = Relationship(back_populates="test_cases")
    results: List["TestResult"] = Relationship(back_populates="test_case")

class TestRun(TimestampModel, table=True):
    """テスト実行モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    project_id: int = Field(foreign_key="project.id")
    status: str  # running, completed, failed
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # リレーションシップ
    project: Project = Relationship(back_populates="test_runs")
    results: List["TestResult"] = Relationship(back_populates="test_run")

class TestResult(TimestampModel, table=True):
    """テスト結果モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="testrun.id")
    test_case_id: int = Field(foreign_key="testcase.id")
    status_code: Optional[int] = None
    passed: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    response_body: Optional[Dict[str, Any]] = Field(default=None, sa_column=JSON)
    
    # リレーションシップ
    test_run: TestRun = Relationship(back_populates="results")
    test_case: TestCase = Relationship(back_populates="results")