from sqlmodel import Field, Relationship
from typing import Optional, List, Any, Dict
from datetime import datetime
import json
from ..base import TimestampModel
from ..project import Project
from .case import TestCase

class TestRun(TimestampModel, table=True):
    __tablename__ = "testrun"
    """テスト実行モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    suite_id: str = Field(foreign_key="testsuite.id")
    project_id: int = Field(foreign_key="project.id")
    status: str  # running, completed, failed
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # リレーションシップ
    test_suite: "TestSuite" = Relationship(back_populates="test_runs")
    project: Project = Relationship(back_populates="test_runs")
    test_case_results: List["TestCaseResult"] = Relationship(back_populates="test_run", sa_relationship_kwargs={"cascade": "delete, all"})

class TestCaseResult(TimestampModel, table=True):
    __tablename__ = "testcaseresult"
    """テストケース結果モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="testrun.id")
    case_id: str = Field(foreign_key="testcase.id")
    status: str  # passed, failed, skipped
    error_message: Optional[str] = None
    
    # リレーションシップ
    test_run: TestRun = Relationship(back_populates="test_case_results")
    test_case: TestCase = Relationship(back_populates="test_case_results")
    step_results: List["StepResult"] = Relationship(back_populates="test_case_result", sa_relationship_kwargs={"cascade": "delete, all"})

class StepResult(TimestampModel, table=True):
    __tablename__ = "stepresult"
    """テストステップ結果モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    test_case_result_id: int = Field(foreign_key="testcaseresult.id")
    step_id: str = Field(foreign_key="teststep.id")
    sequence: int
    status_code: Optional[int] = None
    passed: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    response_body_str: Optional[str] = Field(default=None)
    extracted_values_str: Optional[str] = Field(default=None)
    
    # リレーションシップ
    test_case_result: TestCaseResult = Relationship(back_populates="step_results")
    test_step: "TestStep" = Relationship(back_populates="step_results")
    
    # JSON シリアライズ/デシリアライズのためのプロパティ
    @property
    def response_body(self) -> Any:
        if self.response_body_str:
            return json.loads(self.response_body_str)
        return None
    
    @response_body.setter
    def response_body(self, value: Any):
        if value is not None:
            self.response_body_str = json.dumps(value)
        else:
            self.response_body_str = None
    
    @property
    def extracted_values(self) -> Dict[str, Any]:
        if self.extracted_values_str:
            return json.loads(self.extracted_values_str)
        return {}
    
    @extracted_values.setter
    def extracted_values(self, value: Dict[str, Any]):
        if value is not None:
            self.extracted_values_str = json.dumps(value)
        else:
            self.extracted_values_str = None