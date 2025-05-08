from typing import Optional
from pydantic import BaseModel, ConfigDict
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