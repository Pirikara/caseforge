from sqlmodel import Field, Relationship
from sqlalchemy import Column
from typing import Optional, List, Dict, Any
from .base import TimestampModel
from .service import Service
from app.models.json_encode_dict import JSONEncodedDict 

class TestSuite(TimestampModel, table=True):
    __tablename__ = "testsuite"
    """テストスイートモデル（APIエンドポイント単位のテスト群）"""
    id: str = Field(index=True, primary_key=True)
    service_id: int = Field(foreign_key="service.id") 
    target_method: str
    target_path: str
    name: str
    description: Optional[str] = None
    
    # リレーションシップ
    service: Service = Relationship(back_populates="test_suites")
    test_cases: List["TestCase"] = Relationship(back_populates="test_suite", sa_relationship_kwargs={"cascade": "delete, all"})
    test_runs: List["TestRun"] = Relationship(back_populates="test_suite", sa_relationship_kwargs={"cascade": "delete, all"})

class TestStep(TimestampModel, table=True):
    __tablename__ = "teststep"
    """テストステップモデル（テストケース内の1つのリクエスト）"""
    id: str = Field(index=True, primary_key=True)
    case_id: str = Field(foreign_key="testcase.id")
    sequence: int
    name: Optional[str] = None
    method: str
    path: str
    request_headers: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    request_body: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    request_params: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    extract_rules: Optional[Dict[str, str]] = Field(sa_column=Column(JSONEncodedDict))
    expected_status: Optional[int] = None
    
    # リレーションシップ
    test_case: "TestCase" = Relationship(back_populates="test_steps")
    step_results: List["StepResult"] = Relationship(back_populates="test_step", sa_relationship_kwargs={"cascade": "delete, all"})
