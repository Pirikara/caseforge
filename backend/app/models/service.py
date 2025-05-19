from sqlmodel import Field, Relationship
from typing import Optional, List, ForwardRef
from .base import TimestampModel

# 循環インポートを避けるために ForwardRef を使用
TestSuite = ForwardRef("TestSuite")
TestRun = ForwardRef("TestRun")
Endpoint = ForwardRef("Endpoint")

class Service(TimestampModel, table=True):
    __tablename__ = "service"
    """サービスモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: str = Field(index=True, unique=True)
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = Field(default=None)

    # リレーションシップ
    schemas: List["Schema"] = Relationship(back_populates="service", sa_relationship_kwargs={"cascade": "delete, all"})
    # 新しいリレーションシップ
    test_suites: List["TestSuite"] = Relationship(back_populates="service", sa_relationship_kwargs={"cascade": "delete, all"})
    test_runs: List["TestRun"] = Relationship(back_populates="service", sa_relationship_kwargs={"cascade": "delete, all"})
    # エンドポイント管理のリレーションシップ
    endpoints: List["Endpoint"] = Relationship(back_populates="service", sa_relationship_kwargs={"cascade": "delete, all"})

class Schema(TimestampModel, table=True):
    """OpenAPIスキーマモデル"""
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="service.id")
    filename: str
    file_path: str
    content_type: str
    
    # リレーションシップ
    service: Service = Relationship(back_populates="schemas")
