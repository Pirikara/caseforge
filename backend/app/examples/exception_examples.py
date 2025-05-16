"""
例外クラスとヘルパー関数の使用例

このモジュールは、Caseforgeの例外クラスとヘルパー関数の使用方法を示すサンプルコードを提供します。
"""

import logging
from typing import Dict, Any, List

from app.exceptions import (
    # 基底例外クラス
    CaseforgeException, ErrorCode,
    
    # LLM関連の例外クラス
    LLMException, PromptException, ModelCallException, RAGException,
    
    # テスト関連の例外クラス
    TestException, TestGenerationException, TestExecutionException,
    
    # API関連の例外クラス
    APIException, OpenAPIParseException, RequestException,
    
    # データ処理関連の例外クラス
    DataException, DatabaseException, ValidationException,
    
    # システム関連の例外クラス
    SystemException, ConfigurationException, TimeoutException,
    
    # ヘルパー関数
    handle_exceptions, exception_to_response, safe_execute, convert_exception
)

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 基本的な例外の発生と捕捉
def basic_exception_example() -> None:
    """基本的な例外の発生と捕捉の例"""
    print("\n=== 基本的な例外の発生と捕捉 ===")
    
    try:
        # 基本的な例外を発生させる
        raise CaseforgeException("基本的なエラーが発生しました")
    except CaseforgeException as e:
        print(f"例外をキャッチしました: {e}")
        print(f"エラーコード: {e.error_code.name}:{e.error_code.value}")
        print(f"メッセージ: {e.message}")
        print(f"詳細: {e.details}")


# エラーコードとメッセージの使用
def error_code_example() -> None:
    """エラーコードとメッセージの使用例"""
    print("\n=== エラーコードとメッセージの使用 ===")
    
    try:
        # カスタムエラーコードを指定して例外を発生させる
        raise LLMException(
            message="LLMモデルの呼び出し中にエラーが発生しました",
            error_code=ErrorCode.MODEL_CALL_ERROR
        )
    except LLMException as e:
        print(f"例外をキャッチしました: {e}")
        print(f"エラーコード: {e.error_code.name}:{e.error_code.value}")
        print(f"メッセージ: {e.message}")


# 詳細情報の追加
def details_example() -> None:
    """詳細情報の追加例"""
    print("\n=== 詳細情報の追加 ===")
    
    try:
        # 詳細情報を含む例外を発生させる
        details = {
            "model": "gpt-4",
            "prompt": "テストプロンプト",
            "error": "Rate limit exceeded",
            "retry_after": 60
        }
        raise ModelCallException(
            message="APIレート制限に達しました",
            details=details
        )
    except ModelCallException as e:
        print(f"例外をキャッチしました: {e}")
        print(f"エラーコード: {e.error_code.name}:{e.error_code.value}")
        print(f"メッセージ: {e.message}")
        print(f"詳細: {e.details}")
        
        # 例外を辞書形式に変換
        error_dict = e.to_dict()
        print(f"辞書形式: {error_dict}")


# 例外階層の使用
def exception_hierarchy_example() -> None:
    """例外階層の使用例"""
    print("\n=== 例外階層の使用 ===")
    
    exceptions = [
        CaseforgeException("基本的なエラー"),
        LLMException("LLM関連エラー"),
        PromptException("プロンプトエラー"),
        TestExecutionException("テスト実行エラー"),
        OpenAPIParseException("OpenAPIパースエラー"),
        DatabaseException("データベースエラー")
    ]
    
    for exception in exceptions:
        try:
            raise exception
        except CaseforgeException as e:
            print(f"キャッチした例外: {type(e).__name__}")
            print(f"メッセージ: {e}")
            
            # 例外の種類を確認
            if isinstance(e, LLMException):
                print("これはLLM関連の例外です")
            elif isinstance(e, TestException):
                print("これはテスト関連の例外です")
            elif isinstance(e, APIException):
                print("これはAPI関連の例外です")
            elif isinstance(e, DataException):
                print("これはデータ処理関連の例外です")
            elif isinstance(e, SystemException):
                print("これはシステム関連の例外です")
            print()


# handle_exceptionsデコレータの使用例
@handle_exceptions(fallback_value=None, log_level=logging.WARNING)
def risky_function(value: int) -> int:
    """例外が発生する可能性のある関数"""
    if value < 0:
        raise ValidationException("値は0以上である必要があります")
    if value > 100:
        raise ValueError("値は100以下である必要があります")
    return value * 2


def decorator_example() -> None:
    """デコレータの使用例"""
    print("\n=== handle_exceptionsデコレータの使用 ===")
    
    # 正常なケース
    result1 = risky_function(50)
    print(f"正常なケース: {result1}")
    
    # Caseforge例外が発生するケース
    result2 = risky_function(-10)
    print(f"Caseforge例外が発生するケース: {result2}")
    
    # 一般的な例外が発生するケース
    result3 = risky_function(200)
    print(f"一般的な例外が発生するケース: {result3}")


# convert_exceptionデコレータの使用例
@convert_exception(DatabaseException, "データベース操作中にエラーが発生しました")
def database_operation(query: str) -> List[Dict[str, Any]]:
    """データベース操作を行う関数"""
    if "SELECT" not in query.upper():
        raise ValueError("無効なSQLクエリです")
    
    # 実際のデータベース操作の代わりにダミーデータを返す
    if "users" in query.lower():
        return [{"id": 1, "name": "ユーザー1"}, {"id": 2, "name": "ユーザー2"}]
    else:
        return []


def convert_exception_example() -> None:
    """convert_exceptionデコレータの使用例"""
    print("\n=== convert_exceptionデコレータの使用 ===")
    
    try:
        # 正常なケース
        result = database_operation("SELECT * FROM users")
        print(f"正常なケース: {result}")
        
        # 例外が発生するケース
        database_operation("INSERT INTO users VALUES (1, 'ユーザー1')")
    except DatabaseException as e:
        print(f"変換された例外をキャッチしました: {e}")
        print(f"エラーコード: {e.error_code.name}:{e.error_code.value}")
        print(f"詳細: {e.details}")


# safe_execute関数の使用例
def safe_execute_example() -> None:
    """safe_execute関数の使用例"""
    print("\n=== safe_execute関数の使用 ===")
    
    # 正常なケース
    result1 = safe_execute(lambda x: x * 2, 10)
    print(f"正常なケース: {result1}")
    
    # 例外が発生するケース
    result2 = safe_execute(lambda: 1 / 0)
    print(f"例外が発生するケース: {result2}")


# exception_to_response関数の使用例
def exception_to_response_example() -> None:
    """exception_to_response関数の使用例"""
    print("\n=== exception_to_response関数の使用 ===")
    
    try:
        raise TestGenerationException(
            message="テストケースの生成に失敗しました",
            details={"endpoint": "/api/users", "method": "POST"}
        )
    except TestGenerationException as e:
        # 例外をAPIレスポンス形式に変換
        response = exception_to_response(e)
        print(f"APIレスポンス: {response}")


def main() -> None:
    """メイン関数"""
    print("=== Caseforge例外クラスとヘルパー関数の使用例 ===")
    
    # 各例の実行
    basic_exception_example()
    error_code_example()
    details_example()
    exception_hierarchy_example()
    decorator_example()
    convert_exception_example()
    safe_execute_example()
    exception_to_response_example()


if __name__ == "__main__":
    main()