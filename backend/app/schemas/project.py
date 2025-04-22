from pydantic import BaseModel

class ProjectCreate(BaseModel):
    """プロジェクト作成リクエストスキーマ"""
    project_id: str
    name: str
    description: str = ""