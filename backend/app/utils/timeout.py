"""
タイムアウト処理のユーティリティモジュール

このモジュールは、同期・非同期関数の実行にタイムアウト機能を提供します。
設定値は環境変数やconfigから取得でき、タイムアウト発生時は適切な例外をスローします。
"""

import asyncio
import functools
import os
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, TypeVar, Union, cast

from app.config import settings
from app.exceptions import TimeoutException
from app.logging_config import logger

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])

DEFAULT_TIMEOUT = 30.0

def get_timeout_config(timeout_key: str, default: float = DEFAULT_TIMEOUT) -> float:
    """
    環境変数または設定から特定のタイムアウト値を取得する
    
    Args:
        timeout_key: タイムアウト設定のキー
        default: デフォルト値
        
    Returns:
        タイムアウト値（秒）
    """
    env_value = os.environ.get(f"TIMEOUT_{timeout_key.upper()}")
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            logger.warning(f"Invalid timeout value in environment variable TIMEOUT_{timeout_key.upper()}: {env_value}")
    
    try:
        timeout_attr = f"TIMEOUT_{timeout_key.upper()}"
        if hasattr(settings, timeout_attr):
            return float(getattr(settings, timeout_attr))
    except (AttributeError, ValueError):
        pass
    
    return default

def timeout(seconds: Optional[Union[float, str]] = None, timeout_key: Optional[str] = None) -> Callable[[F], F]:
    """
    同期関数にタイムアウト機能を追加するデコレータ
    
    Args:
        seconds: タイムアウト秒数（直接指定する場合）
        timeout_key: 設定から取得するタイムアウト値のキー
        
    Returns:
        デコレータ関数
        
    Examples:
        >>> @timeout(5.0)
        >>> def slow_function():
        >>>     time.sleep(10)
        >>>     return "Done"
        
        >>> @timeout(timeout_key="API_CALL")
        >>> def api_call():
        >>>     # API呼び出し処理
        >>>     pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            timeout_value = _resolve_timeout(seconds, timeout_key)
            
            if not hasattr(signal, 'SIGALRM'):
                return _thread_based_timeout(func, timeout_value, *args, **kwargs)
            
            def timeout_handler(signum: int, frame: Any) -> None:
                raise TimeoutException(
                    f"Function {func.__name__} timed out after {timeout_value} seconds",
                    details={"function": func.__name__, "timeout": timeout_value}
                )
            
            original_handler = signal.getsignal(signal.SIGALRM)
            
            signal.signal(signal.SIGALRM, timeout_handler)
            
            try:
                signal.setitimer(signal.ITIMER_REAL, timeout_value)
                result = func(*args, **kwargs)
                return result
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, original_handler)
        
        return cast(F, wrapper)
    
    return decorator

def _thread_based_timeout(func: Callable[..., T], timeout_value: float, *args: Any, **kwargs: Any) -> T:
    """
    スレッドを使用したタイムアウト処理の実装
    
    Args:
        func: 実行する関数
        timeout_value: タイムアウト秒数
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数
        
    Returns:
        関数の戻り値
        
    Raises:
        TimeoutException: タイムアウトが発生した場合
    """
    result = []
    exception = []
    
    def target() -> None:
        try:
            result.append(func(*args, **kwargs))
        except Exception as e:
            exception.append(e)
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_value)
    
    if thread.is_alive():
        raise TimeoutException(
            f"Function {func.__name__} timed out after {timeout_value} seconds",
            details={"function": func.__name__, "timeout": timeout_value}
        )
    
    if exception:
        raise exception[0]
    
    return result[0]

def async_timeout(seconds: Optional[Union[float, str]] = None, timeout_key: Optional[str] = None) -> Callable[[AsyncF], AsyncF]:
    """
    非同期関数にタイムアウト機能を追加するデコレータ
    
    Args:
        seconds: タイムアウト秒数（直接指定する場合）
        timeout_key: 設定から取得するタイムアウト値のキー
        
    Returns:
        デコレータ関数
        
    Examples:
        >>> @async_timeout(5.0)
        >>> async def slow_async_function():
        >>>     await asyncio.sleep(10)
        >>>     return "Done"
        
        >>> @async_timeout(timeout_key="DB_QUERY")
        >>> async def db_query():
        >>>     # データベースクエリ処理
        >>>     pass
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            timeout_value = _resolve_timeout(seconds, timeout_key)
            
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_value)
            except asyncio.TimeoutError:
                raise TimeoutException(
                    f"Async function {func.__name__} timed out after {timeout_value} seconds",
                    details={"function": func.__name__, "timeout": timeout_value}
                )
        
        return cast(AsyncF, wrapper)
    
    return decorator

def _resolve_timeout(seconds: Optional[Union[float, str]], timeout_key: Optional[str]) -> float:
    """
    タイムアウト値を解決する
    
    Args:
        seconds: タイムアウト秒数（直接指定する場合）
        timeout_key: 設定から取得するタイムアウト値のキー
        
    Returns:
        タイムアウト値（秒）
    """
    if seconds is not None:
        if isinstance(seconds, str):
            try:
                return float(seconds)
            except ValueError:
                logger.warning(f"Invalid timeout value: {seconds}, using default")
                return DEFAULT_TIMEOUT
        return float(seconds)
    
    if timeout_key is not None:
        return get_timeout_config(timeout_key)
    
    return DEFAULT_TIMEOUT

def run_with_timeout(func: Callable[..., T], timeout_value: float, *args: Any, **kwargs: Any) -> T:
    """
    関数を指定したタイムアウトで実行する
    
    Args:
        func: 実行する関数
        timeout_value: タイムアウト秒数
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数
        
    Returns:
        関数の戻り値
        
    Raises:
        TimeoutException: タイムアウトが発生した場合
        
    Examples:
        >>> result = run_with_timeout(slow_function, 5.0, arg1, arg2, kwarg1=value1)
    """
    if not hasattr(signal, 'SIGALRM'):
        return _thread_based_timeout(func, timeout_value, *args, **kwargs)
    
    def timeout_handler(signum: int, frame: Any) -> None:
        raise TimeoutException(
            f"Function {func.__name__} timed out after {timeout_value} seconds",
            details={"function": func.__name__, "timeout": timeout_value}
        )
    
    original_handler = signal.getsignal(signal.SIGALRM)
    
    signal.signal(signal.SIGALRM, timeout_handler)
    
    try:
        signal.setitimer(signal.ITIMER_REAL, timeout_value)
        result = func(*args, **kwargs)
        return result
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, original_handler)

async def run_async_with_timeout(func: Callable[..., Any], timeout_value: float, *args: Any, **kwargs: Any) -> Any:
    """
    非同期関数を指定したタイムアウトで実行する
    
    Args:
        func: 実行する非同期関数
        timeout_value: タイムアウト秒数
        *args: 関数の位置引数
        **kwargs: 関数のキーワード引数
        
    Returns:
        関数の戻り値
        
    Raises:
        TimeoutException: タイムアウトが発生した場合
        
    Examples:
        >>> result = await run_async_with_timeout(slow_async_function, 5.0, arg1, arg2, kwarg1=value1)
    """
    try:
        if asyncio.iscoroutinefunction(func):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_value)
        else:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                return await asyncio.wait_for(
                    loop.run_in_executor(executor, lambda: func(*args, **kwargs)),
                    timeout=timeout_value
                )
    except asyncio.TimeoutError:
        raise TimeoutException(
            f"Function {func.__name__} timed out after {timeout_value} seconds",
            details={"function": func.__name__, "timeout": timeout_value}
        )
