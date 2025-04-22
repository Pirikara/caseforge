from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
import json
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
    request_body_str: Optional[str] = Field(default=None)
    expected_status: int
    expected_response_str: Optional[str] = Field(default=None)
    purpose: str  # functional, boundary, authZ, fuzz
    
    # リレーションシップ
    project: Project = Relationship(back_populates="test_cases")
    results: List["TestResult"] = Relationship(back_populates="test_case")
    
    # JSON シリアライズ/デシリアライズのためのプロパティ
    @property
    def request_body(self):
        if self.request_body_str:
            return json.loads(self.request_body_str)
        return None
    
    @request_body.setter
    def request_body(self, value):
        if value is not None:
            self.request_body_str = json.dumps(value)
        else:
            self.request_body_str = None
    
    @property
    def expected_response(self):
        if self.expected_response_str:
            return json.loads(self.expected_response_str)
        return None
    
    @expected_response.setter
    def expected_response(self, value):
        if value is not None:
            self.expected_response_str = json.dumps(value)
        else:
            self.expected_response_str = None

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
    response_body_str: Optional[str] = Field(default=None)
    
    # リレーションシップ
    test_run: TestRun = Relationship(back_populates="results")
    test_case: TestCase = Relationship(back_populates="results")
    
    # JSON シリアライズ/デシリアライズのためのプロパティ
    @property
    def response_body(self):
        if self.response_body_str:
            return json.loads(self.response_body_str)
        return None
    
    @response_body.setter
    def response_body(self, value):
        if value is not None:
            self.response_body_str = json.dumps(value)
        else:
            self.response_body_str = None