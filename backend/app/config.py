import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # アプリケーション設定
    APP_NAME: str = "Caseforge"
    DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
    
    # データパス設定
    SCHEMA_DIR: str = os.environ.get("SCHEMA_DIR", "/code/data/schemas")
    TESTS_DIR: str = os.environ.get("TESTS_DIR", "/code/data/generated_tests")
    LOG_DIR: str = os.environ.get("LOG_DIR", "/code/data/test_runs")
    
    # ChromaDB設定
    CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "/chroma/.chroma")
    
    # LLM設定
    LLM_MODEL_NAME: str = os.environ.get("LLM_MODEL_NAME", "Hermes-3-Llama-3.1-8B-GGUF")
    OPENAI_API_BASE: str = os.environ.get("OPENAI_API_BASE", "http://192.168.2.101:1234/v1")
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "not-needed")
    
    # テスト実行設定
    TEST_TARGET_URL: str = os.environ.get("TEST_TARGET_URL", "http://backend:8000")
    
    # Redis設定
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    
    class Config:
        env_file = ".env"

settings = Settings()