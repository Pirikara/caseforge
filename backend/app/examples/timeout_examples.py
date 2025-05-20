"""
タイムアウト処理のユーティリティの使用例

このモジュールは、timeout.pyで定義されたタイムアウト処理ユーティリティの使用方法を示すサンプルコードを提供します。
同期処理と非同期処理の両方でのタイムアウト処理の使用例を含みます。
"""

import asyncio
import os
import time
from typing import Dict, Any, List

import httpx
import requests

from app.exceptions import TimeoutException, handle_exceptions
from app.logging_config import logger
from app.utils.timeout import (
    timeout, 
    async_timeout, 
    run_with_timeout, 
    run_async_with_timeout,
    get_timeout_config
)

import logging
logging.basicConfig(level=logging.INFO)

os.environ["TIMEOUT_API_CALL"] = "5.0"
os.environ["TIMEOUT_DB_QUERY"] = "10.0"
os.environ["TIMEOUT_LLM_CALL"] = "60.0"

@timeout(2.0)
def slow_function() -> str:
    """タイムアウトするテスト関数（同期）"""
    print("slow_function: 処理を開始します")
    time.sleep(3)  # 3秒間スリープ（タイムアウトは2秒）
    print("slow_function: 処理が完了しました")  # この行は実行されない
    return "完了"


@timeout(timeout_key="API_CALL")
def api_call(url: str) -> Dict[str, Any]:
    """外部APIを呼び出す関数（設定からタイムアウト値を取得）"""
    print(f"api_call: {url} にリクエストを送信します")
    response = requests.get(url, timeout=get_timeout_config("API_CALL"))
    print(f"api_call: ステータスコード {response.status_code} を受信しました")
    return response.json()


@async_timeout(2.0)
async def slow_async_function() -> str:
    """タイムアウトするテスト関数（非同期）"""
    print("slow_async_function: 処理を開始します")
    await asyncio.sleep(3)  # 3秒間スリープ（タイムアウトは2秒）
    print("slow_async_function: 処理が完了しました")  # この行は実行されない
    return "完了"


@async_timeout(timeout_key="API_CALL")
async def async_api_call(url: str) -> Dict[str, Any]:
    """外部APIを非同期で呼び出す関数（設定からタイムアウト値を取得）"""
    print(f"async_api_call: {url} にリクエストを送信します")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=float(get_timeout_config("API_CALL")))
        print(f"async_api_call: ステータスコード {response.status_code} を受信しました")
        return response.json()


@handle_exceptions(fallback_value={"status": "error", "message": "API呼び出しに失敗しました"})
@timeout(timeout_key="API_CALL")
def safe_api_call(url: str) -> Dict[str, Any]:
    """例外処理とタイムアウト処理を組み合わせた関数"""
    print(f"safe_api_call: {url} にリクエストを送信します")
    response = requests.get(url, timeout=get_timeout_config("API_CALL"))
    print(f"safe_api_call: ステータスコード {response.status_code} を受信しました")
    return response.json()


def run_with_timeout_example() -> None:
    """run_with_timeoutを使用した例"""
    print("\n=== run_with_timeout の使用例 ===")
    
    def long_running_task(duration: int) -> str:
        print(f"long_running_task: {duration}秒間処理を実行します")
        time.sleep(duration)
        return f"{duration}秒の処理が完了しました"
    
    try:
        # 正常に完了する場合
        result = run_with_timeout(long_running_task, 3.0, 1)
        print(f"結果: {result}")
        
        # タイムアウトする場合
        result = run_with_timeout(long_running_task, 2.0, 5)
        print(f"結果: {result}")  # この行は実行されない
    except TimeoutException as e:
        print(f"タイムアウト例外が発生しました: {e}")


async def run_async_with_timeout_example() -> None:
    """run_async_with_timeoutを使用した例"""
    print("\n=== run_async_with_timeout の使用例 ===")
    
    async def long_running_async_task(duration: int) -> str:
        print(f"long_running_async_task: {duration}秒間処理を実行します")
        await asyncio.sleep(duration)
        return f"{duration}秒の処理が完了しました"
    
    try:
        # 正常に完了する場合
        result = await run_async_with_timeout(long_running_async_task, 3.0, 1)
        print(f"結果: {result}")
        
        # タイムアウトする場合
        result = await run_async_with_timeout(long_running_async_task, 2.0, 5)
        print(f"結果: {result}")  # この行は実行されない
    except TimeoutException as e:
        print(f"タイムアウト例外が発生しました: {e}")


@timeout(timeout_key="LLM_CALL")
def mock_llm_call(prompt: str) -> str:
    """LLM呼び出しのモック関数"""
    print(f"mock_llm_call: プロンプト「{prompt}」を処理します")
    # 実際のLLM呼び出しをシミュレート
    time.sleep(2)
    return f"「{prompt}」に対する応答です。"


@async_timeout(timeout_key="DB_QUERY")
async def mock_db_query(query: str) -> List[Dict[str, Any]]:
    """データベースクエリのモック関数"""
    print(f"mock_db_query: クエリ「{query}」を実行します")
    # 実際のデータベースクエリをシミュレート
    await asyncio.sleep(1)
    return [{"id": 1, "name": "テストデータ1"}, {"id": 2, "name": "テストデータ2"}]


async def main() -> None:
    """メイン関数"""
    print("=== タイムアウト処理ユーティリティの使用例 ===")
    
    # 同期関数のタイムアウト例
    print("\n=== 同期関数のタイムアウト例 ===")
    try:
        result = slow_function()
        print(f"結果: {result}")  # この行は実行されない
    except TimeoutException as e:
        print(f"タイムアウト例外が発生しました: {e}")
    
    # 設定からタイムアウト値を取得する例
    print("\n=== 設定からタイムアウト値を取得する例 ===")
    api_timeout = get_timeout_config("API_CALL")
    db_timeout = get_timeout_config("DB_QUERY")
    llm_timeout = get_timeout_config("LLM_CALL")
    print(f"API呼び出しのタイムアウト: {api_timeout}秒")
    print(f"データベースクエリのタイムアウト: {db_timeout}秒")
    print(f"LLM呼び出しのタイムアウト: {llm_timeout}秒")
    
    # API呼び出しの例（タイムアウトしない場合）
    print("\n=== API呼び出しの例（タイムアウトしない場合） ===")
    try:
        # JSONPlaceholderは高速に応答するため、通常はタイムアウトしない
        result = api_call("https://jsonplaceholder.typicode.com/todos/1")
        print(f"結果: {result}")
    except (TimeoutException, requests.RequestException) as e:
        print(f"例外が発生しました: {e}")
    
    # 非同期関数のタイムアウト例
    print("\n=== 非同期関数のタイムアウト例 ===")
    try:
        result = await slow_async_function()
        print(f"結果: {result}")  # この行は実行されない
    except TimeoutException as e:
        print(f"タイムアウト例外が発生しました: {e}")
    
    # 非同期API呼び出しの例
    print("\n=== 非同期API呼び出しの例 ===")
    try:
        result = await async_api_call("https://jsonplaceholder.typicode.com/todos/1")
        print(f"結果: {result}")
    except (TimeoutException, httpx.RequestError) as e:
        print(f"例外が発生しました: {e}")
    
    # 例外処理と組み合わせた例
    print("\n=== 例外処理と組み合わせた例 ===")
    result = safe_api_call("https://jsonplaceholder.typicode.com/todos/1")
    print(f"結果: {result}")
    
    # 存在しないURLにリクエストを送信（例外が発生する）
    print("\n=== 存在しないURLにリクエスト（例外処理） ===")
    result = safe_api_call("https://non-existent-url.example.com")
    print(f"結果: {result}")  # フォールバック値が返される
    
    # run_with_timeoutの例
    run_with_timeout_example()
    
    # run_async_with_timeoutの例
    await run_async_with_timeout_example()
    
    # LLM呼び出しのモック例
    print("\n=== LLM呼び出しのモック例 ===")
    try:
        result = mock_llm_call("こんにちは、AIアシスタント")
        print(f"結果: {result}")
    except TimeoutException as e:
        print(f"タイムアウト例外が発生しました: {e}")
    
    # データベースクエリのモック例
    print("\n=== データベースクエリのモック例 ===")
    try:
        result = await mock_db_query("SELECT * FROM users")
        print(f"結果: {result}")
    except TimeoutException as e:
        print(f"タイムアウト例外が発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())
