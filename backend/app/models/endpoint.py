from sqlmodel import Field, Relationship
from sqlalchemy import Column
from typing import Optional, Dict, Any
from uuid import uuid4
from .base import TimestampModel
from .project import Project
from app.models.json_encode_dict import JSONEncodedDict

class Endpoint(TimestampModel, table=True):
    __tablename__ = "endpoint"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: str = Field(default_factory=lambda: str(uuid4()), index=True)
    project_id: int = Field(foreign_key="project.id")
    
    path: str  # e.g., "/users/{id}"
    method: str  # e.g., "GET", "POST", "PUT", "DELETE"
    
    summary: Optional[str] = None  # OpenAPIのsummary
    description: Optional[str] = None  # 詳細な説明
    
    request_body: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    request_headers: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    request_query_params: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    responses: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    
    # リレーションシップ
    project: Project = Relationship(back_populates="endpoints")
