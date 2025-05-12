from sqlmodel import Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from .base import TimestampModel
from .project import Project

class TestSuite(TimestampModel, table=True):
    __tablename__ = "testsuite"
    """テストスイートモデル（APIエンドポイント単位のテスト群）"""
    id: str = Field(index=True, primary_key=True) # Optional[int] から str に変更し、index=True を追加
    project_id: int = Field(foreign_key="project.id") 
    target_method: str
    target_path: str
    name: str
    description: Optional[str] = None
    
    # リレーションシップ
    project: Project = Relationship(back_populates="test_suites")
    test_cases: List["TestCase"] = Relationship(back_populates="test_suite", sa_relationship_kwargs={"cascade": "delete, all"})
    test_runs: List["TestRun"] = Relationship(back_populates="test_suite", sa_relationship_kwargs={"cascade": "delete, all"})

class TestStep(TimestampModel, table=True):
    __tablename__ = "teststep"
    """テストステップモデル（テストケース内の1つのリクエスト）"""
    id: str = Field(index=True, primary_key=True) # Optional[int] から str に変更し、index=True を追加
    case_id: str = Field(foreign_key="testcase.id") # int から str に変更
    sequence: int  # ステップの実行順序
    name: Optional[str] = None
    method: str
    path: str
    request_headers_str: Optional[str] = Field(default=None)
    request_body_str: Optional[str] = Field(default=None)
    request_params_str: Optional[str] = Field(default=None)
    expected_status: Optional[int] = None
    extract_rules_str: Optional[str] = Field(default=None)  # JSONPath形式の抽出ルール
    
    # リレーションシップ
    test_case: "TestCase" = Relationship(back_populates="test_steps")
    step_results: List["StepResult"] = Relationship(back_populates="test_step", sa_relationship_kwargs={"cascade": "delete, all"})
    
    # JSON シリアライズ/デシリアライズのためのプロパティ
    @property
    def request_headers(self) -> Dict[str, Any]:
        if self.request_headers_str:
            return json.loads(self.request_headers_str)
        return {}
    
    @request_headers.setter
    def request_headers(self, value: Dict[str, Any]):
        if value is not None:
            self.request_headers_str = json.dumps(value)
        else:
            self.request_headers_str = None
    
    @property
    def request_body(self) -> Any:
        if self.request_body_str:
            return json.loads(self.request_body_str)
        return None
    
    @request_body.setter
    def request_body(self, value: Any):
        if value is not None:
            self.request_body_str = json.dumps(value)
        else:
            self.request_body_str = None
    
    @property
    def request_params(self) -> Dict[str, Any]:
        if self.request_params_str:
            return json.loads(self.request_params_str)
        return {}
    
    @request_params.setter
    def request_params(self, value: Dict[str, Any]):
        if value is not None:
            self.request_params_str = json.dumps(value)
        else:
            self.request_params_str = None
    
    @property
    def extract_rules(self) -> Dict[str, str]:
        if self.extract_rules_str:
            return json.loads(self.extract_rules_str)
        return {}
    
    @extract_rules.setter
    def extract_rules(self, value: Dict[str, str]):
        if value is not None:
            self.extract_rules_str = json.dumps(value)
        else:
            self.extract_rules_str = None