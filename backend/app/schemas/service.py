from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import datetime
import json

class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = None

class ServiceCreate(ServiceBase):
    pass

    pass

class ServiceUpdate(ServiceBase):
    pass

class Service(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EndpointBase(BaseModel):
    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    request_headers: Optional[Dict[str, Any]] = None
    request_query_params: Optional[Dict[str, Any]] = None
    responses: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            try:
                data = data.dict()
            except AttributeError:
                data = vars(data)

        for field in ["request_body", "request_headers", "request_query_params", "responses"]:
            val = data.get(field)
            if val is None or val == "None":
                data[field] = {}
            elif isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except json.JSONDecodeError:
                    raise ValueError(f"Invalid JSON string for {field}: {val}")
        return data

class Endpoint(EndpointBase):
    id: str = Field(alias="endpoint_id")
    service_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
