from typing import List
from sqlmodel import SQLModel, Field
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column

class SchemaChunk(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="service.id")
    path: str
    method: str
    content: str
    embedding: List[float] = Field(sa_column=Column(Vector(384)))
