import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # アプリケーション設定
    APP_NAME: str = "Caseforge"
    DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
    DEBUG_PORT: int = int(os.environ.get("DEBUG_PORT", "4444"))
    
    # データパス設定
    SCHEMA_DIR: str = os.environ.get("SCHEMA_DIR", "/code/data/schemas")
    TESTS_DIR: str = os.environ.get("TESTS_DIR", "/code/data/generated_tests")
    LOG_DIR: str = os.environ.get("LOG_DIR", "/code/data/test_runs")
    
    # LLM設定
    LLM_MODEL_NAME: str = os.environ.get("LLM_MODEL_NAME", "Hermes-3-Llama-3.1-8B")
    OPENAI_API_BASE: str = os.environ.get("OPENAI_API_BASE", "http://192.168.2.101:1234/v1")
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "not-needed")
    
    # テスト実行設定
    TEST_TARGET_URL: str = os.environ.get("TEST_TARGET_URL", "http://backend:8000")
    
    # Redis設定
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    
    # データベース設定
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "postgresql://caseforge:caseforge@db:5432/caseforge")
    
    model_config = ConfigDict(env_file=".env")

settings = Settings()