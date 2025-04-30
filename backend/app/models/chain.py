from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from .base import TimestampModel
from .project import Project

class TestChain(TimestampModel, table=True):
    __tablename__ = "testchain"
    """テストチェーンモデル（複数ステップの依存関係を持つテストシナリオ）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    chain_id: str = Field(index=True)
    project_id: int = Field(foreign_key="project.id")
    name: str
    description: Optional[str] = None
    tags: Optional[str] = None  # カンマ区切りのタグ
    
    # リレーションシップ
    project: Project = Relationship(back_populates="test_chains")
    steps: List["TestChainStep"] = Relationship(back_populates="chain", sa_relationship_kwargs={"cascade": "delete, all"})
    runs: List["ChainRun"] = Relationship(back_populates="chain", sa_relationship_kwargs={"cascade": "delete, all"})
    
    @property
    def tag_list(self) -> List[str]:
        """タグのリストを返す"""
        return self.tags.split(",") if self.tags else []

class TestChainStep(TimestampModel, table=True):
    __tablename__ = "testchainstep"
    """テストチェーンステップモデル（チェーン内の1つのリクエスト）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    chain_id: int = Field(foreign_key="testchain.id")
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
    chain: TestChain = Relationship(back_populates="steps")
    results: List["StepResult"] = Relationship(back_populates="step")
    
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

class ChainRun(TimestampModel, table=True):
    __tablename__ = "chainrun"
    """テストチェーン実行モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: str = Field(index=True, unique=True)
    chain_id: int = Field(foreign_key="testchain.id")
    project_id: int = Field(foreign_key="project.id")
    status: str  # running, completed, failed
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # リレーションシップ
    chain: TestChain = Relationship(back_populates="runs")
    project: Project = Relationship(back_populates="chain_runs")
    step_results: List["StepResult"] = Relationship(back_populates="chain_run", sa_relationship_kwargs={"cascade": "delete, all"})

class StepResult(TimestampModel, table=True):
    __tablename__ = "stepresult"
    """テストチェーンステップ結果モデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    chain_run_id: int = Field(foreign_key="chainrun.id")
    step_id: int = Field(foreign_key="testchainstep.id")
    sequence: int
    status_code: Optional[int] = None
    passed: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    response_body_str: Optional[str] = Field(default=None)
    extracted_values_str: Optional[str] = Field(default=None)
    
    # リレーションシップ
    chain_run: ChainRun = Relationship(back_populates="step_results")
    step: TestChainStep = Relationship(back_populates="results")
    
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