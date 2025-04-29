from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, Dict, List
from datetime import datetime
import json
from uuid import uuid4
from .base import TimestampModel
from .project import Project

class Endpoint(TimestampModel, table=True):
    __tablename__ = "endpoint"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: str = Field(default_factory=lambda: str(uuid4()), index=True)
    project_id: int = Field(foreign_key="project.id")
    
    path: str  # e.g., "/users/{id}"
    method: str  # e.g., "GET", "POST", "PUT", "DELETE"
    
    summary: Optional[str] = None  # OpenAPIのsummary
    description: Optional[str] = None  # 詳細な説明
    
    request_body_str: Optional[str] = Field(default=None)  # リクエストボディ（JSON Schema形式）
    request_headers_str: Optional[str] = Field(default=None)  # 必要ヘッダー
    request_query_params_str: Optional[str] = Field(default=None)  # クエリパラメータ
    responses_str: Optional[str] = Field(default=None)  # レスポンス定義（ステータスコードごと）
    
    # リレーションシップ
    project: Project = Relationship(back_populates="endpoints")
    
    # JSON シリアライズ/デシリアライズのためのプロパティ
    @property
    def request_body(self) -> Optional[Dict]:
        if self.request_body_str:
            return json.loads(self.request_body_str)
        return None
    
    @request_body.setter
    def request_body(self, value: Optional[Dict]):
        if value is not None:
            self.request_body_str = json.dumps(value)
        else:
            self.request_body_str = None
    
    @property
    def request_headers(self) -> Dict:
        if self.request_headers_str:
            return json.loads(self.request_headers_str)
        return {}
    
    @request_headers.setter
    def request_headers(self, value: Optional[Dict]):
        if value is not None:
            self.request_headers_str = json.dumps(value)
        else:
            self.request_headers_str = None
    
    @property
    def request_query_params(self) -> Dict:
        if self.request_query_params_str:
            return json.loads(self.request_query_params_str)
        return {}
    
    @request_query_params.setter
    def request_query_params(self, value: Optional[Dict]):
        if value is not None:
            self.request_query_params_str = json.dumps(value)
        else:
            self.request_query_params_str = None
    
    @property
    def responses(self) -> Dict:
        if self.responses_str:
            return json.loads(self.responses_str)
        return {}
    
    @responses.setter
    def responses(self, value: Optional[Dict]):
        if value is not None:
            self.responses_str = json.dumps(value)
        else:
            self.responses_str = None