from sqlmodel import Field, Relationship
from sqlalchemy import Column
from typing import Optional, List, Any, Dict
from datetime import datetime
from .base import TimestampModel
from .service import Service
from app.models.json_encode_dict import JSONEncodedDict

class TestCase(TimestampModel, table=True):
    __test__ = False
    __tablename__ = "testcase"
    """テストケースモデル（1つのテストパターン）"""
    id: str = Field(index=True, primary_key=True) # Optional[int] から str に変更し、index=True を追加
    suite_id: str = Field(foreign_key="testsuite.id") # int から str に変更
    name: str
    description: Optional[str] = None
    error_type: Optional[str] = None # 例: invalid_input, authentication_error
    
    # リレーションシップ
    test_suite: "TestSuite" = Relationship(back_populates="test_cases")
    test_steps: List["TestStep"] = Relationship(back_populates="test_case", sa_relationship_kwargs={"cascade": "delete, all"})
    test_case_results: List["TestCaseResult"] = Relationship(back_populates="test_case", sa_relationship_kwargs={"cascade": "delete, all"})

class TestRun(TimestampModel, table=True):
    __tablename__ = "testrun"
    """テスト実行モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    suite_id: str = Field(foreign_key="testsuite.id")
    service_id: int = Field(foreign_key="service.id")
    status: str  # running, completed, failed
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # リレーションシップ
    test_suite: "TestSuite" = Relationship(back_populates="test_runs")
    service: Service = Relationship(back_populates="test_runs")
    test_case_results: List["TestCaseResult"] = Relationship(back_populates="test_run", sa_relationship_kwargs={"cascade": "delete, all"})

class TestCaseResult(TimestampModel, table=True):
    __tablename__ = "testcaseresult"
    """テストケース結果モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="testrun.id")
    case_id: str = Field(foreign_key="testcase.id") # int から str に変更
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
    response_body: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    extracted_values: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    
    # リレーションシップ
    test_case_result: TestCaseResult = Relationship(back_populates="step_results")
    test_step: "TestStep" = Relationship(back_populates="step_results")
