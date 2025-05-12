from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = None

class ProjectCreate(ProjectBase):
    project_id: str

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int
    project_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EndpointBase(BaseModel):
    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    request_body: Optional[Any] = None
    request_headers: Optional[Dict[str, Any]] = None # 追加
    request_query_params: Optional[Dict[str, Any]] = None # 追加
    responses: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class Endpoint(EndpointBase):
    id: str = Field(alias="endpoint_id") # endpoint_id を id として公開
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)