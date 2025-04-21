import os
from pathlib import Path
from app.services.rag import index_schema

SCHEMA_DIR = "/code/data/schemas"

def save_and_index_schema(project_id: str, content: bytes, filename: str):
    os.makedirs(f"{SCHEMA_DIR}/{project_id}", exist_ok=True)
    save_path = f"{SCHEMA_DIR}/{project_id}/{filename}"

    with open(save_path, "wb") as f:
        f.write(content)

    index_schema(project_id, save_path)

def list_projects() -> list[str]:
    """
    保存されたスキーマのディレクトリからプロジェクト一覧を取得
    """
    schema_root = Path(SCHEMA_DIR)
    if not schema_root.exists():
        return []

    return [p.name for p in schema_root.iterdir() if p.is_dir()]

def create_project(project_id: str):
    path = os.path.join(SCHEMA_DIR, project_id)
    if not os.path.exists(path):
        os.makedirs(path)