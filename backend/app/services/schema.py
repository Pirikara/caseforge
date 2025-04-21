import os
from app.services.rag import index_schema

SCHEMA_DIR = "/code/data/schemas"

def save_and_index_schema(project_id: str, content: bytes, filename: str):
    os.makedirs(f"{SCHEMA_DIR}/{project_id}", exist_ok=True)
    save_path = f"{SCHEMA_DIR}/{project_id}/{filename}"

    with open(save_path, "wb") as f:
        f.write(content)

    index_schema(project_id, save_path)