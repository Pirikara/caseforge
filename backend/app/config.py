import os
import json
import yaml
from typing import Any, Dict, Optional, Union, TypeVar, Generic, cast
from functools import lru_cache
from pathlib import Path
from pydantic import ConfigDict, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 型変数の定義
T = TypeVar('T')

class ConfigValue(Generic[T]):
    """設定値を表すクラス。環境変数、設定ファイル、デフォルト値の優先順位を管理する"""
    
    def __init__(
        self, 
        default: T, 
        env_var: Optional[str] = None, 
        config_path: Optional[str] = None,
        description: str = ""
    ):
        self.default = default
        self.env_var = env_var
        self.config_path = config_path
        self.description = description
        self._value: Optional[T] = None
        self._is_cached = False
    
    def get_value(self, config_data: Dict[str, Any] = None) -> T:
        """設定値を取得する。キャッシュがある場合はキャッシュから取得する"""
        if self._is_cached:
            return cast(T, self._value)
        
        # 環境変数から取得
        if self.env_var and self.env_var in os.environ:
            env_value = os.environ[self.env_var]
            self._value = self._convert_value(env_value)
            self._is_cached = True
            return cast(T, self._value)
        
        # 設定ファイルから取得
        if config_data and self.config_path:
            try:
                # ドット記法でネストした設定値にアクセス
                paths = self.config_path.split('.')
                value = config_data
                for path in paths:
                    value = value[path]
                self._value = self._convert_value(value)
                self._is_cached = True
                return cast(T, self._value)
            except (KeyError, TypeError):
                # 設定ファイルに該当のパスがない場合は無視
                pass
        
        # デフォルト値を返す
        self._value = self.default
        self._is_cached = True
        return self.default
    
    def _convert_value(self, value: Any) -> T:
        """値を適切な型に変換する"""
        if isinstance(self.default, bool) and isinstance(value, str):
            return cast(T, value.lower() == "true")
        elif isinstance(self.default, int) and isinstance(value, str):
            return cast(T, int(value))
        elif isinstance(self.default, float) and isinstance(value, str):
            return cast(T, float(value))
        elif isinstance(self.default, list) and isinstance(value, str):
            return cast(T, value.split(','))
        elif isinstance(self.default, dict) and isinstance(value, str):
            try:
                return cast(T, json.loads(value))
            except json.JSONDecodeError:
                return self.default
        else:
            return cast(T, value)
    
    def clear_cache(self) -> None:
        """キャッシュをクリアする"""
        self._is_cached = False
        self._value = None


class AppConfig:
    """アプリケーション設定"""
    NAME = ConfigValue[str](
        default="Caseforge",
        env_var="APP_NAME",
        config_path="app.name",
        description="アプリケーション名"
    )
    DEBUG = ConfigValue[bool](
        default=False,
        env_var="DEBUG",
        config_path="app.debug",
        description="デバッグモードの有効/無効"
    )
    DEBUG_PORT = ConfigValue[int](
        default=4444,
        env_var="DEBUG_PORT",
        config_path="app.debug_port",
        description="デバッグポート"
    )


class PathConfig:
    """ファイルパス設定"""
    SCHEMA_DIR = ConfigValue[str](
        default="/code/data/schemas",
        env_var="SCHEMA_DIR",
        config_path="paths.schema_dir",
        description="スキーマファイルの保存ディレクトリ"
    )
    TESTS_DIR = ConfigValue[str](
        default="/code/data/generated_tests",
        env_var="TESTS_DIR",
        config_path="paths.tests_dir",
        description="生成されたテストの保存ディレクトリ"
    )
    LOG_DIR = ConfigValue[str](
        default="/code/data/test_runs",
        env_var="LOG_DIR",
        config_path="paths.log_dir",
        description="テスト実行ログの保存ディレクトリ"
    )


class LLMConfig:
    """LLM設定"""
    MODEL_NAME = ConfigValue[str](
        default="Hermes-3-Llama-3.1-8B",
        env_var="LLM_MODEL_NAME",
        config_path="llm.model_name",
        description="LLMモデル名"
    )
    OPENAI_API_BASE = ConfigValue[str](
        default="http://192.168.2.101:1234/v1",
        env_var="OPENAI_API_BASE",
        config_path="llm.openai_api_base",
        description="OpenAI API ベースURL"
    )
    OPENAI_API_KEY = ConfigValue[str](
        default="not-needed",
        env_var="OPENAI_API_KEY",
        config_path="llm.openai_api_key",
        description="OpenAI API キー"
    )
    PROVIDER = ConfigValue[str](
        default="",
        env_var="LLM_PROVIDER",
        config_path="llm.provider",
        description="LLMプロバイダー"
    )
    ANTHROPIC_API_KEY = ConfigValue[str](
        default="",
        env_var="ANTHROPIC_API_KEY",
        config_path="llm.anthropic_api_key",
        description="Anthropic API キー"
    )
    ANTHROPIC_MODEL_NAME = ConfigValue[str](
        default="claude-3-opus-20240229",
        env_var="ANTHROPIC_MODEL_NAME",
        config_path="llm.anthropic_model_name",
        description="Anthropicモデル名"
    )


class TestConfig:
    """テスト実行設定"""
    TARGET_URL = ConfigValue[str](
        default="http://backend:8000",
        env_var="TEST_TARGET_URL",
        config_path="test.target_url",
        description="テスト対象URL"
    )


class RedisConfig:
    """Redis設定"""
    URL = ConfigValue[str](
        default="redis://redis:6379/0",
        env_var="REDIS_URL",
        config_path="redis.url",
        description="Redis URL"
    )


class DatabaseConfig:
    """データベース設定"""
    URL = ConfigValue[str](
        default="postgresql://caseforge:caseforge@db:5432/caseforge",
        env_var="DATABASE_URL",
        config_path="database.url",
        description="データベースURL"
    )


class TimeoutConfig:
    """タイムアウト設定"""
    DEFAULT = ConfigValue[float](
        default=30.0,
        env_var="TIMEOUT_DEFAULT",
        config_path="timeout.default",
        description="デフォルトのタイムアウト値（秒）"
    )
    LLM_CALL = ConfigValue[float](
        default=60.0,
        env_var="TIMEOUT_LLM_CALL",
        config_path="timeout.llm_call",
        description="LLM呼び出しのタイムアウト値（秒）"
    )
    EMBEDDING = ConfigValue[float](
        default=120.0,
        env_var="TIMEOUT_EMBEDDING",
        config_path="timeout.embedding",
        description="埋め込み処理のタイムアウト値（秒）"
    )
    API_CALL = ConfigValue[float](
        default=10.0,
        env_var="TIMEOUT_API_CALL",
        config_path="timeout.api_call",
        description="API呼び出しのタイムアウト値（秒）"
    )
    HTTP_REQUEST = ConfigValue[float](
        default=30.0,
        env_var="TIMEOUT_HTTP_REQUEST",
        config_path="timeout.http_request",
        description="HTTPリクエストのタイムアウト値（秒）"
    )
    DB_QUERY = ConfigValue[float](
        default=15.0,
        env_var="TIMEOUT_DB_QUERY",
        config_path="timeout.db_query",
        description="データベースクエリのタイムアウト値（秒）"
    )
    DB_CONNECTION = ConfigValue[float](
        default=5.0,
        env_var="TIMEOUT_DB_CONNECTION",
        config_path="timeout.db_connection",
        description="データベース接続のタイムアウト値（秒）"
    )
    FILE_OPERATION = ConfigValue[float](
        default=10.0,
        env_var="TIMEOUT_FILE_OPERATION",
        config_path="timeout.file_operation",
        description="ファイル操作のタイムアウト値（秒）"
    )


class Config:
    """設定クラス"""
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        self._load_config_file()
        
        # 設定カテゴリの初期化
        self.app = AppConfig()
        self.paths = PathConfig()
        self.llm = LLMConfig()
        self.test = TestConfig()
        self.redis = RedisConfig()
        self.database = DatabaseConfig()
        self.timeout = TimeoutConfig()
    
    def _load_config_file(self) -> None:
        """設定ファイルを読み込む"""
        if not self.config_file:
            # 環境変数から設定ファイルのパスを取得
            self.config_file = os.environ.get("CONFIG_FILE", "config.yaml")
        
        # 設定ファイルが存在する場合は読み込む
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    if self.config_file.endswith(('.yaml', '.yml')):
                        self.config_data = yaml.safe_load(f)
                    elif self.config_file.endswith('.json'):
                        self.config_data = json.load(f)
            except Exception as e:
                print(f"設定ファイルの読み込みに失敗しました: {e}")
    
    def reload(self) -> None:
        """設定を再読み込みする"""
        self._load_config_file()
        self.clear_cache()
    
    def clear_cache(self) -> None:
        """すべての設定値のキャッシュをクリアする"""
        for category in [self.app, self.paths, self.llm, self.test, self.redis, self.database, self.timeout]:
            for attr_name in dir(category):
                if not attr_name.startswith('_'):
                    attr = getattr(category, attr_name)
                    if isinstance(attr, ConfigValue):
                        attr.clear_cache()
    
    def to_dict(self) -> Dict[str, Any]:
        """すべての設定値を辞書形式で取得する"""
        result = {}
        
        # 各カテゴリの設定値を取得
        for category_name, category in [
            ('app', self.app),
            ('paths', self.paths),
            ('llm', self.llm),
            ('test', self.test),
            ('redis', self.redis),
            ('database', self.database),
            ('timeout', self.timeout)
        ]:
            category_dict = {}
            for attr_name in dir(category):
                if not attr_name.startswith('_'):
                    attr = getattr(category, attr_name)
                    if isinstance(attr, ConfigValue):
                        category_dict[attr_name.lower()] = attr.get_value(self.config_data)
            result[category_name] = category_dict
        
        return result


# 互換性のために従来のSettingsクラスも維持
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
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL_NAME: str = os.environ.get("ANTHROPIC_MODEL_NAME", "claude-3-opus-20240229")
    
    # テスト実行設定
    TEST_TARGET_URL: str = os.environ.get("TEST_TARGET_URL", "http://backend:8000")
    
    # Redis設定
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    
    # データベース設定
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "postgresql://caseforge:caseforge@db:5432/caseforge")
    
    # タイムアウト設定（秒）
    # デフォルトのタイムアウト値
    TIMEOUT_DEFAULT: float = float(os.environ.get("TIMEOUT_DEFAULT", "30.0"))
    
    # LLM関連のタイムアウト
    TIMEOUT_LLM_CALL: float = float(os.environ.get("TIMEOUT_LLM_CALL", "60.0"))
    TIMEOUT_EMBEDDING: float = float(os.environ.get("TIMEOUT_EMBEDDING", "120.0"))
    
    # API関連のタイムアウト
    TIMEOUT_API_CALL: float = float(os.environ.get("TIMEOUT_API_CALL", "10.0"))
    TIMEOUT_HTTP_REQUEST: float = float(os.environ.get("TIMEOUT_HTTP_REQUEST", "30.0"))
    
    # データベース関連のタイムアウト
    TIMEOUT_DB_QUERY: float = float(os.environ.get("TIMEOUT_DB_QUERY", "15.0"))
    TIMEOUT_DB_CONNECTION: float = float(os.environ.get("TIMEOUT_DB_CONNECTION", "5.0"))
    
    # ファイル操作関連のタイムアウト
    TIMEOUT_FILE_OPERATION: float = float(os.environ.get("TIMEOUT_FILE_OPERATION", "10.0"))
    
    model_config = ConfigDict(env_file=".env")


# シングルトンインスタンスの作成
@lru_cache()
def get_config() -> Config:
    """設定のシングルトンインスタンスを取得する"""
    return Config()


# 従来のsettingsオブジェクトの作成（互換性のため）
settings = Settings()

# 新しい設定オブジェクト
config = get_config()