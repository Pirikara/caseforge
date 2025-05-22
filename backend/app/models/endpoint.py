from sqlmodel import Field, Relationship
from sqlalchemy import Column
from typing import Optional, Dict, Any
from uuid import uuid4
from .base import TimestampModel
from .service import Service
from app.models.json_encode_dict import JSONEncodedDict

class Endpoint(TimestampModel, table=True):
    __tablename__ = "endpoint"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint_id: str = Field(default_factory=lambda: str(uuid4()), index=True)
    service_id: int = Field(foreign_key="service.id")
    
    path: str
    method: str
    
    summary: Optional[str] = None
    description: Optional[str] = None
    
    request_body: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    request_headers: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    request_query_params: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    responses: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONEncodedDict))
    
    # リレーションシップ
    service: Service = Relationship(back_populates="endpoints")
