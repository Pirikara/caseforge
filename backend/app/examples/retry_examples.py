"""
リトライ処理のユーティリティの使用例

このモジュールは、retry.pyで定義されたリトライ処理ユーティリティの使用方法を示すサンプルコードを提供します。
同期処理と非同期処理の両方でのリトライ処理の使用例を含みます。
"""

import asyncio
import os
import random
import time
from typing import Dict, Any, List, Optional

import httpx
import requests

from app.exceptions import MaxRetriesExceededException
from app.logging_config import logger
from app.utils.retry import (
    retry, 
    async_retry, 
    run_with_retry, 
    run_async_with_retry,
    RetryStrategy
)

# ロガーの設定
import logging
logging.basicConfig(level=logging.INFO)

# リトライ設定の例（実際のアプリケーションでは、config.pyに定義するか環境変数で設定）
os.environ["RETRY_API_CALL_MAX_RETRIES"] = "3"
os.environ["RETRY_API_CALL_RETRY_DELAY"] = "1.0"
os.environ["RETRY_API_CALL_STRATEGY"] = "exponential"

os.environ["RETRY_DB_QUERY_MAX_RETRIES"] = "5"
os.environ["RETRY_DB_QUERY_RETRY_DELAY"] = "0.5"
os.environ["RETRY_DB_QUERY_STRATEGY"] = "linear"

os.environ["RETRY_LLM_CALL_MAX_RETRIES"] = "2"
os.environ["RETRY_LLM_CALL_RETRY_DELAY"] = "2.0"
os.environ["RETRY_LLM_CALL_STRATEGY"] = "constant"


# 同期関数でのリトライ処理の例
@retry(max_retries=3, retry_delay=1.0)
def unstable_function() -> str:
    """ランダムに失敗するテスト関数（同期）"""
    print("unstable_function: 処理を開始します")
    if random.random() < 0.7:  # 70%の確率で失敗
        print("unstable_function: エラーが発生しました")
        raise ValueError("ランダムエラー")
    print("unstable_function: 処理が完了しました")
    return "完了"


@retry(retry_key="API_CALL")
def api_call(url: str) -> Dict[str, Any]:
    """外部APIを呼び出す関数（設定からリトライ設定を取得）"""
    print(f"api_call: {url} にリクエストを送信します")
    response = requests.get(url, timeout=5.0)
    print(f"api_call: ステータスコード {response.status_code} を受信しました")
    return response.json()


# 非同期関数でのリトライ処理の例
@async_retry(max_retries=3, retry_delay=1.0)
async def unstable_async_function() -> str:
    """ランダムに失敗するテスト関数（非同期）"""
    print("unstable_async_function: 処理を開始します")
    if random.random() < 0.7:  # 70%の確率で失敗
        print("unstable_async_function: エラーが発生しました")
        raise ValueError("ランダムエラー")
    print("unstable_async_function: 処理が完了しました")
    return "完了"


@async_retry(retry_key="API_CALL")
async def async_api_call(url: str) -> Dict[str, Any]:
    """外部APIを非同期で呼び出す関数（設定からリトライ設定を取得）"""
    print(f"async_api_call: {url} にリクエストを送信します")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=5.0)
        print(f"async_api_call: ステータスコード {response.status_code} を受信しました")
        return response.json()


# 特定の例外のみをリトライする例
@retry(
    max_retries=3,
    retry_delay=1.0,
    retry_exceptions=[ConnectionError, TimeoutError]
)
def selective_retry_function() -> str:
    """特定の例外のみをリトライするテスト関数"""
    print("selective_retry_function: 処理を開始します")
    r = random.random()
    if r < 0.4:  # 40%の確率でConnectionError
        print("selective_retry_function: 接続エラーが発生しました")
        raise ConnectionError("接続エラー")
    elif r < 0.7:  # 30%の確率でValueError（リトライされない）
        print("selective_retry_function: 値エラーが発生しました")
        raise ValueError("値エラー")
    print("selective_retry_function: 処理が完了しました")
    return "完了"


# 結果に基づいてリトライする例
def is_retry_needed(result: Dict[str, Any]) -> bool:
    """結果に基づいてリトライが必要かどうかを判断する関数"""
    # ステータスコードが429（レート制限）または500番台の場合はリトライ
    status = result.get("status")
    if status == 429 or (status and status >= 500):
        return True
    return False


@retry(
    max_retries=3,
    retry_delay=1.0,
    retry_if_result=is_retry_needed
)
def result_based_retry_function() -> Dict[str, Any]:
    """結果に基づいてリトライするテスト関数"""
    print("result_based_retry_function: 処理を開始します")
    r = random.random()
    if r < 0.4:  # 40%の確率で429エラー
        print("result_based_retry_function: レート制限エラーが発生しました")
        return {"status": 429, "message": "Too Many Requests"}
    elif r < 0.7:  # 30%の確率で500エラー
        print("result_based_retry_function: サーバーエラーが発生しました")
        return {"status": 500, "message": "Internal Server Error"}
    print("result_based_retry_function: 処理が完了しました")
    return {"status": 200, "message": "OK"}


# 異なるバックオフ戦略の例
@retry(
    max_retries=5,
    retry_delay=1.0,
    retry_strategy=RetryStrategy.EXPONENTIAL,
    backoff_factor=2.0,
    retry_jitter=0.1
)
def exponential_backoff_function() -> str:
    """指数関数的バックオフを使用するテスト関数"""
    print("exponential_backoff_function: 処理を開始します")
    if random.random() < 0.7:  # 70%の確率で失敗
        print("exponential_backoff_function: エラーが発生しました")
        raise ValueError("ランダムエラー")
    print("exponential_backoff_function: 処理が完了しました")
    return "完了"


@retry(
    max_retries=5,
    retry_delay=1.0,
    retry_strategy=RetryStrategy.LINEAR,
    retry_jitter=0.1
)
def linear_backoff_function() -> str:
    """線形バックオフを使用するテスト関数"""
    print("linear_backoff_function: 処理を開始します")
    if random.random() < 0.7:  # 70%の確率で失敗
        print("linear_backoff_function: エラーが発生しました")
        raise ValueError("ランダムエラー")
    print("linear_backoff_function: 処理が完了しました")
    return "完了"


# run_with_retryを使用した例
def run_with_retry_example() -> None:
    """run_with_retryを使用した例"""
    print("\n=== run_with_retry の使用例 ===")
    
    def long_running_task(success_rate: float) -> str:
        print(f"long_running_task: 成功率 {success_rate*100}%で処理を実行します")
        if random.random() > success_rate:
            raise ValueError("ランダムエラー")
        return "処理が完了しました"
    
    try:
        # 成功率50%の関数を最大5回リトライ
        result = run_with_retry(
            long_running_task,
            0.5,  # success_rate引数
            max_retries=5,
            retry_delay=1.0,
            retry_strategy=RetryStrategy.EXPONENTIAL
        )
        print(f"結果: {result}")
    except MaxRetriesExceededException as e:
        print(f"最大リトライ回数を超えました: {e}")


# run_async_with_retryを使用した例
async def run_async_with_retry_example() -> None:
    """run_async_with_retryを使用した例"""
    print("\n=== run_async_with_retry の使用例 ===")
    
    async def long_running_async_task(success_rate: float) -> str:
        print(f"long_running_async_task: 成功率 {success_rate*100}%で処理を実行します")
        if random.random() > success_rate:
            raise ValueError("ランダムエラー")
        return "処理が完了しました"
    
    try:
        # 成功率30%の非同期関数を最大5回リトライ
        result = await run_async_with_retry(
            long_running_async_task,
            0.3,  # success_rate引数
            max_retries=5,
            retry_delay=1.0,
            retry_strategy=RetryStrategy.EXPONENTIAL
        )
        print(f"結果: {result}")
    except MaxRetriesExceededException as e:
        print(f"最大リトライ回数を超えました: {e}")


# LLM呼び出しのモック例
@retry(retry_key="LLM_CALL")
def mock_llm_call(prompt: str) -> str:
    """LLM呼び出しのモック関数"""
    print(f"mock_llm_call: プロンプト「{prompt}」を処理します")
    # 実際のLLM呼び出しをシミュレート
    if random.random() < 0.5:  # 50%の確率で失敗
        print("mock_llm_call: APIエラーが発生しました")
        raise ConnectionError("API接続エラー")
    time.sleep(1)
    return f"「{prompt}」に対する応答です。"


# データベースクエリのモック例
@async_retry(retry_key="DB_QUERY")
async def mock_db_query(query: str) -> List[Dict[str, Any]]:
    """データベースクエリのモック関数"""
    print(f"mock_db_query: クエリ「{query}」を実行します")
    # 実際のデータベースクエリをシミュレート
    if random.random() < 0.4:  # 40%の確率で失敗
        print("mock_db_query: データベース接続エラーが発生しました")
        raise ConnectionError("データベース接続エラー")
    await asyncio.sleep(0.5)
    return [{"id": 1, "name": "テストデータ1"}, {"id": 2, "name": "テストデータ2"}]


# タイムアウト処理と組み合わせた例
from app.utils.timeout import timeout

@timeout(seconds=2.0)
@retry(max_retries=3, retry_delay=0.5)
def timeout_with_retry() -> str:
    """タイムアウト処理とリトライ処理を組み合わせた関数"""
    print("timeout_with_retry: 処理を開始します")
    # ランダムに処理時間を決定
    sleep_time = random.uniform(0.5, 3.0)
    print(f"timeout_with_retry: {sleep_time}秒間スリープします")
    time.sleep(sleep_time)
    print("timeout_with_retry: 処理が完了しました")
    return "完了"


# メイン関数
async def main() -> None:
    """メイン関数"""
    print("=== リトライ処理ユーティリティの使用例 ===")
    
    # 同期関数のリトライ例
    print("\n=== 同期関数のリトライ例 ===")
    try:
        result = unstable_function()
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # 設定からリトライ設定を取得する例
    print("\n=== 設定からリトライ設定を取得する例 ===")
    try:
        # JSONPlaceholderは高速に応答するため、通常はリトライされない
        result = api_call("https://jsonplaceholder.typicode.com/todos/1")
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # 非同期関数のリトライ例
    print("\n=== 非同期関数のリトライ例 ===")
    try:
        result = await unstable_async_function()
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # 非同期API呼び出しの例
    print("\n=== 非同期API呼び出しの例 ===")
    try:
        result = await async_api_call("https://jsonplaceholder.typicode.com/todos/1")
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # 特定の例外のみをリトライする例
    print("\n=== 特定の例外のみをリトライする例 ===")
    try:
        result = selective_retry_function()
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # 結果に基づいてリトライする例
    print("\n=== 結果に基づいてリトライする例 ===")
    result = result_based_retry_function()
    print(f"結果: {result}")
    
    # 異なるバックオフ戦略の例
    print("\n=== 指数関数的バックオフの例 ===")
    try:
        result = exponential_backoff_function()
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    print("\n=== 線形バックオフの例 ===")
    try:
        result = linear_backoff_function()
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # run_with_retryの例
    run_with_retry_example()
    
    # run_async_with_retryの例
    await run_async_with_retry_example()
    
    # LLM呼び出しのモック例
    print("\n=== LLM呼び出しのモック例 ===")
    try:
        result = mock_llm_call("こんにちは、AIアシスタント")
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # データベースクエリのモック例
    print("\n=== データベースクエリのモック例 ===")
    try:
        result = await mock_db_query("SELECT * FROM users")
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")
    
    # タイムアウト処理と組み合わせた例
    print("\n=== タイムアウト処理と組み合わせた例 ===")
    try:
        result = timeout_with_retry()
        print(f"結果: {result}")
    except Exception as e:
        print(f"例外が発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())