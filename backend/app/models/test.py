from sqlmodel import Field, Relationship
from typing import Optional, List
from datetime import datetime
import json
from .base import TimestampModel
from .project import Project

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
    status_code: Optional[int] = None
    passed: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    response_body_str: Optional[str] = Field(default=None)
    
    # リレーションシップ
    test_run: TestRun = Relationship(back_populates="results")
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