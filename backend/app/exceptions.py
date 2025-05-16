"""
Caseforgeアプリケーションの例外クラス階層

このモジュールは、アプリケーション全体で使用される例外クラスの階層を定義します。
構造化された例外処理により、エラーハンドリングの一貫性と明確なエラーメッセージを提供します。
各例外クラスには適切なエラーコードが割り当てられ、エラーの種類を明確に区別できます。
"""
from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(Enum):
    """エラーコード定義"""
    # 一般的なエラー (1000-1999)
    GENERAL_ERROR = 1000
    CONFIGURATION_ERROR = 1001
    TIMEOUT_ERROR = 1002
    RESOURCE_ERROR = 1003
    
    # LLM関連エラー (2000-2999)
    LLM_ERROR = 2000
    PROMPT_ERROR = 2001
    MODEL_CALL_ERROR = 2002
    RAG_ERROR = 2003
    
    # テスト関連エラー (3000-3999)
    TEST_ERROR = 3000
    TEST_GENERATION_ERROR = 3001
    TEST_EXECUTION_ERROR = 3002
    TEST_VALIDATION_ERROR = 3003
    
    # API関連エラー (4000-4999)
    API_ERROR = 4000
    OPENAPI_PARSE_ERROR = 4001
    ENDPOINT_ERROR = 4002
    REQUEST_ERROR = 4003
    RESPONSE_ERROR = 4004
    
    # データ処理関連エラー (5000-5999)
    DATA_ERROR = 5000
    DATABASE_ERROR = 5001
    VALIDATION_ERROR = 5002
    SERIALIZATION_ERROR = 5003


class CaseforgeException(Exception):
    """Caseforgeの基底例外クラス"""
    def __init__(
        self,
        message: str = "Caseforgeアプリケーションエラーが発生しました",
        error_code: ErrorCode = ErrorCode.GENERAL_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return f"[{self.error_code.name}:{self.error_code.value}] {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """例外情報を辞書形式で返す"""
        return {
            "error_code": self.error_code.value,
            "error_name": self.error_code.name,
            "message": self.message,
            "details": self.details
        }


# システム関連の例外クラス
class SystemException(CaseforgeException):
    """システム関連の基底例外クラス"""
    def __init__(
        self,
        message: str = "システムエラーが発生しました",
        error_code: ErrorCode = ErrorCode.GENERAL_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class ConfigurationException(SystemException):
    """設定エラー"""
    def __init__(
        self,
        message: str = "設定の読み込みまたは検証に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.CONFIGURATION_ERROR, details)


class TimeoutException(SystemException):
    """タイムアウトエラー"""
    def __init__(
        self,
        message: str = "処理がタイムアウトしました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.TIMEOUT_ERROR, details)


class ResourceException(SystemException):
    """リソース関連エラー"""
    def __init__(
        self,
        message: str = "必要なリソースにアクセスできませんでした",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.RESOURCE_ERROR, details)


# LLM関連の例外クラス
class LLMException(CaseforgeException):
    """LLM関連の基底例外クラス"""
    def __init__(
        self,
        message: str = "LLM処理中にエラーが発生しました",
        error_code: ErrorCode = ErrorCode.LLM_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class PromptException(LLMException):
    """プロンプト関連のエラー"""
    def __init__(
        self,
        message: str = "プロンプトの処理に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.PROMPT_ERROR, details)


class ModelCallException(LLMException):
    """モデル呼び出しエラー"""
    def __init__(
        self,
        message: str = "LLMモデルの呼び出しに失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.MODEL_CALL_ERROR, details)


class RAGException(LLMException):
    """RAG処理エラー"""
    def __init__(
        self,
        message: str = "RAG処理に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.RAG_ERROR, details)


# テスト関連の例外クラス
class TestException(CaseforgeException):
    """テスト関連の基底例外クラス"""
    def __init__(
        self,
        message: str = "テスト処理中にエラーが発生しました",
        error_code: ErrorCode = ErrorCode.TEST_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class TestGenerationException(TestException):
    """テスト生成エラー"""
    def __init__(
        self,
        message: str = "テストスイートの生成に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.TEST_GENERATION_ERROR, details)


class TestExecutionException(TestException):
    """テスト実行エラー"""
    def __init__(
        self,
        message: str = "テストの実行に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.TEST_EXECUTION_ERROR, details)


class TestValidationException(TestException):
    """テスト検証エラー"""
    def __init__(
        self,
        message: str = "テスト結果の検証に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.TEST_VALIDATION_ERROR, details)


# API関連の例外クラス
class APIException(CaseforgeException):
    """API関連の基底例外クラス"""
    def __init__(
        self,
        message: str = "API処理中にエラーが発生しました",
        error_code: ErrorCode = ErrorCode.API_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class OpenAPIParseException(APIException):
    """OpenAPIスキーマのパースエラー"""
    def __init__(
        self,
        message: str = "OpenAPIスキーマのパースに失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.OPENAPI_PARSE_ERROR, details)


class EndpointException(APIException):
    """エンドポイント関連エラー"""
    def __init__(
        self,
        message: str = "エンドポイント処理に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.ENDPOINT_ERROR, details)


class RequestException(APIException):
    """リクエスト関連エラー"""
    def __init__(
        self,
        message: str = "APIリクエストの処理に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.REQUEST_ERROR, details)


class ResponseException(APIException):
    """レスポンス関連エラー"""
    def __init__(
        self,
        message: str = "APIレスポンスの処理に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.RESPONSE_ERROR, details)


# データ処理関連の例外クラス
class DataException(CaseforgeException):
    """データ関連の基底例外クラス"""
    def __init__(
        self,
        message: str = "データ処理中にエラーが発生しました",
        error_code: ErrorCode = ErrorCode.DATA_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code, details)


class DatabaseException(DataException):
    """データベースエラー"""
    def __init__(
        self,
        message: str = "データベース操作に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.DATABASE_ERROR, details)


class ValidationException(DataException):
    """データ検証エラー"""
    def __init__(
        self,
        message: str = "入力データの検証に失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details)


class SerializationException(DataException):
    """シリアライズエラー"""
    def __init__(
        self,
        message: str = "データのシリアライズまたはデシリアライズに失敗しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.SERIALIZATION_ERROR, details)


# 例外処理ヘルパー関数
import functools
import logging
from typing import Type, Callable, TypeVar, cast, Union, List

# ロガーの設定
logger = logging.getLogger(__name__)

# 型変数の定義
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')


def handle_exceptions(
    fallback_value: Optional[T] = None,
    reraise: bool = False,
    log_level: int = logging.ERROR,
    handled_exceptions: List[Type[Exception]] = None
) -> Callable[[F], F]:
    """
    例外をキャッチして処理するデコレータ
    
    Args:
        fallback_value: 例外発生時に返す値
        reraise: 例外を再送出するかどうか
        log_level: ログレベル
        handled_exceptions: 処理する例外のリスト（Noneの場合はすべての例外を処理）
    
    Returns:
        デコレータ関数
    """
    if handled_exceptions is None:
        handled_exceptions = [Exception]
        
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except tuple(handled_exceptions) as e:
                # 例外情報をログに記録
                if isinstance(e, CaseforgeException):
                    logger.log(log_level, f"{e} - 詳細: {e.details}", exc_info=True)
                else:
                    logger.log(log_level, str(e), exc_info=True)
                
                # 例外を再送出するか、フォールバック値を返す
                if reraise:
                    raise
                return fallback_value
        return cast(F, wrapper)
    return decorator


def exception_to_response(exception: CaseforgeException) -> Dict[str, Any]:
    """
    例外をAPIレスポンス形式に変換する
    
    Args:
        exception: 変換する例外
    
    Returns:
        APIレスポンス形式の辞書
    """
    return {
        "success": False,
        "error": exception.to_dict()
    }


def safe_execute(func: Callable[..., T], *args: Any, **kwargs: Any) -> Union[T, None]:
    """
    関数を安全に実行し、例外が発生した場合はNoneを返す
    
    Args:
        func: 実行する関数
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数
    
    Returns:
        関数の戻り値、または例外発生時はNone
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if isinstance(e, CaseforgeException):
            logger.error(f"{e} - 詳細: {e.details}", exc_info=True)
        else:
            logger.error(f"予期しない例外が発生しました: {str(e)}", exc_info=True)
        return None


def convert_exception(
    exception_type: Type[CaseforgeException],
    message: Optional[str] = None
) -> Callable[[F], F]:
    """
    一般的な例外を特定のCaseforge例外に変換するデコレータ
    
    Args:
        exception_type: 変換先の例外タイプ
        message: 例外メッセージ（Noneの場合は元の例外のメッセージを使用）
    
    Returns:
        デコレータ関数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except CaseforgeException:
                # すでにCaseforge例外の場合はそのまま再送出
                raise
            except Exception as e:
                # 一般的な例外をCaseforge例外に変換
                error_message = message if message is not None else str(e)
                details = {"original_exception": str(e), "exception_type": type(e).__name__}
                raise exception_type(error_message, details=details) from e
        return cast(F, wrapper)
    return decorator