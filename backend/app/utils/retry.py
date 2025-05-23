"""
リトライ処理のユーティリティモジュール

このモジュールは、同期・非同期関数の実行にリトライ機能を提供します。
設定値は環境変数やconfigから取得でき、リトライ回数を超えた場合は適切な例外をスローします。
"""

import asyncio
import functools
import os
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from app.config import settings
from app.exceptions import CaseforgeException, ErrorCode
from app.logging_config import logger

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_MAX_RETRY_DELAY = 60.0
DEFAULT_RETRY_JITTER = 0.1
DEFAULT_BACKOFF_FACTOR = 2.0


class RetryStrategy(Enum):
    """リトライ戦略の種類"""
    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class MaxRetriesExceededException(CaseforgeException):
    """最大リトライ回数を超えた場合の例外"""
    def __init__(
        self,
        message: str = "最大リトライ回数を超えました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.GENERAL_ERROR, details)


def get_retry_config(retry_key: str, config_name: str, default: Union[int, float]) -> Union[int, float]:
    """
    環境変数または設定から特定のリトライ設定値を取得する
    
    Args:
        retry_key: リトライ設定のキー（例: "LLM_CALL"）
        config_name: 設定名（例: "MAX_RETRIES"）
        default: デフォルト値
        
    Returns:
        設定値
    """
    env_value = os.environ.get(f"RETRY_{retry_key.upper()}_{config_name.upper()}")
    if env_value:
        try:
            if isinstance(default, int):
                return int(env_value)
            return float(env_value)
        except ValueError:
            logger.warning(f"Invalid retry value in environment variable RETRY_{retry_key.upper()}_{config_name.upper()}: {env_value}")
    
    try:
        setting_attr = f"RETRY_{retry_key.upper()}_{config_name.upper()}"
        if hasattr(settings, setting_attr):
            value = getattr(settings, setting_attr)
            if isinstance(default, int):
                return int(value)
            return float(value)
    except (AttributeError, ValueError):
        pass
    
    return default


def get_retry_strategy(retry_key: str) -> RetryStrategy:
    """
    環境変数または設定からリトライ戦略を取得する
    
    Args:
        retry_key: リトライ設定のキー（例: "LLM_CALL"）
        
    Returns:
        リトライ戦略
    """
    env_value = os.environ.get(f"RETRY_{retry_key.upper()}_STRATEGY")
    if env_value:
        try:
            return RetryStrategy(env_value.lower())
        except ValueError:
            logger.warning(f"Invalid retry strategy in environment variable RETRY_{retry_key.upper()}_STRATEGY: {env_value}")
    
    try:
        setting_attr = f"RETRY_{retry_key.upper()}_STRATEGY"
        if hasattr(settings, setting_attr):
            strategy_value = getattr(settings, setting_attr).lower()
            return RetryStrategy(strategy_value)
    except (AttributeError, ValueError):
        pass
    
    return RetryStrategy.EXPONENTIAL


def calculate_next_delay(
    retry_count: int,
    strategy: RetryStrategy,
    base_delay: float,
    max_delay: float,
    backoff_factor: float,
    jitter: float
) -> float:
    """
    次のリトライまでの待機時間を計算する
    
    Args:
        retry_count: 現在のリトライ回数
        strategy: リトライ戦略
        base_delay: 基本待機時間（秒）
        max_delay: 最大待機時間（秒）
        backoff_factor: バックオフ係数
        jitter: ジッター（ランダム性）の大きさ
        
    Returns:
        待機時間（秒）
    """
    if strategy == RetryStrategy.CONSTANT:
        delay = base_delay
    elif strategy == RetryStrategy.LINEAR:
        delay = base_delay * (retry_count + 1)
    else:
        delay = base_delay * (backoff_factor ** retry_count)
    
    delay = min(delay, max_delay)
    
    if jitter > 0:
        jitter_amount = delay * jitter
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
    
    return max(0.0, delay)


def should_retry(
    exception: Exception,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_count: int = 0
) -> bool:
    """
    例外に基づいてリトライすべきかどうかを判断する
    
    Args:
        exception: 発生した例外
        retry_exceptions: リトライ対象の例外クラスのリスト
        max_retries: 最大リトライ回数
        retry_count: 現在のリトライ回数
        
    Returns:
        リトライすべきかどうか
    """
    if retry_count >= max_retries:
        return False
def retry(
    max_retries: Optional[Union[int, str]] = None,
    retry_delay: Optional[Union[float, str]] = None,
    max_retry_delay: Optional[Union[float, str]] = None,
    retry_jitter: Optional[Union[float, str]] = None,
    backoff_factor: Optional[Union[float, str]] = None,
    retry_strategy: Optional[Union[RetryStrategy, str]] = None,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    retry_if_result: Optional[Callable[[Any], bool]] = None,
    retry_key: Optional[str] = None
) -> Callable[[F], F]:
    """
    同期関数にリトライ機能を追加するデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        retry_delay: 初期リトライ間隔（秒）
        max_retry_delay: 最大リトライ間隔（秒）
        retry_jitter: ジッター（ランダム性）の大きさ
        backoff_factor: バックオフ係数
        retry_strategy: リトライ戦略
        retry_exceptions: リトライ対象の例外クラスのリスト
        retry_if_result: 結果に基づいてリトライするかどうかを判断する関数
        retry_key: 設定から取得するリトライ設定のキー
        
    Returns:
        デコレータ関数
        
    Examples:
        >>> @retry(max_retries=3, retry_delay=1.0)
        >>> def unstable_function():
        >>>     if random.random() < 0.7:
        >>>         raise ValueError("Random error")
        >>>     return "Success"
        
        >>> @retry(retry_key="API_CALL")
        >>> def api_call():
        >>>     # API呼び出し処理
        >>>     pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_retries = _resolve_retry_setting(max_retries, "MAX_RETRIES", DEFAULT_MAX_RETRIES, retry_key)
            _retry_delay = _resolve_retry_setting(retry_delay, "RETRY_DELAY", DEFAULT_RETRY_DELAY, retry_key)
            _max_retry_delay = _resolve_retry_setting(max_retry_delay, "MAX_RETRY_DELAY", DEFAULT_MAX_RETRY_DELAY, retry_key)
            _retry_jitter = _resolve_retry_setting(retry_jitter, "RETRY_JITTER", DEFAULT_RETRY_JITTER, retry_key)
            _backoff_factor = _resolve_retry_setting(backoff_factor, "BACKOFF_FACTOR", DEFAULT_BACKOFF_FACTOR, retry_key)
            
            _retry_strategy = retry_strategy
            if _retry_strategy is None and retry_key:
                _retry_strategy = get_retry_strategy(retry_key)
            if _retry_strategy is None or isinstance(_retry_strategy, str):
                try:
                    if isinstance(_retry_strategy, str):
                        _retry_strategy = RetryStrategy(_retry_strategy.lower())
                    else:
                        _retry_strategy = RetryStrategy.EXPONENTIAL
                except ValueError:
                    logger.warning(f"Invalid retry strategy: {_retry_strategy}, using EXPONENTIAL")
                    _retry_strategy = RetryStrategy.EXPONENTIAL
            
            _retry_if_result = retry_if_result or retry_result_evaluator
            
            _retry_exceptions = retry_exceptions
            if _retry_exceptions is None:
                _retry_exceptions = [Exception]
            
            retry_count = 0
            last_exception = None
            
            while True:
                try:
                    result = func(*args, **kwargs)
                    
                    if _retry_if_result(result):
                        if retry_count >= _max_retries:
                            logger.warning(
                                f"Max retries exceeded for {func.__name__} due to result evaluation",
                                extra={"retry_count": retry_count, "result": result}
                            )
                            return result
                        
                        retry_count += 1
                        delay = calculate_next_delay(
                            retry_count, _retry_strategy, _retry_delay,
                            _max_retry_delay, _backoff_factor, _retry_jitter
                        )
                        
                        time.sleep(delay)
                        continue
                    
                    return result
                    
                except tuple(_retry_exceptions) as e:
                    last_exception = e
                    
                    if not should_retry(e, _retry_exceptions, _max_retries, retry_count):
                        logger.warning(
                            f"Max retries exceeded for {func.__name__}",
                            extra={"retry_count": retry_count, "exception": str(e)}
                        )
                        if isinstance(e, CaseforgeException):
                            raise
                        raise MaxRetriesExceededException(
                            f"最大リトライ回数({_max_retries})を超えました: {func.__name__}",
                            details={
                                "function": func.__name__,
                                "max_retries": _max_retries,
                                "original_exception": str(e),
                                "exception_type": type(e).__name__
                            }
                        ) from e
                    
                    retry_count += 1
                    delay = calculate_next_delay(
                        retry_count, _retry_strategy, _retry_delay,
                        _max_retry_delay, _backoff_factor, _retry_jitter
                    )
                    
                    time.sleep(delay)
        
        return cast(F, wrapper)
    
    return decorator


def async_retry(
    max_retries: Optional[Union[int, str]] = None,
    retry_delay: Optional[Union[float, str]] = None,
    max_retry_delay: Optional[Union[float, str]] = None,
    retry_jitter: Optional[Union[float, str]] = None,
    backoff_factor: Optional[Union[float, str]] = None,
    retry_strategy: Optional[Union[RetryStrategy, str]] = None,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    retry_if_result: Optional[Callable[[Any], bool]] = None,
    retry_key: Optional[str] = None
) -> Callable[[AsyncF], AsyncF]:
    """
    非同期関数にリトライ機能を追加するデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        retry_delay: 初期リトライ間隔（秒）
        max_retry_delay: 最大リトライ間隔（秒）
        retry_jitter: ジッター（ランダム性）の大きさ
        backoff_factor: バックオフ係数
        retry_strategy: リトライ戦略
        retry_exceptions: リトライ対象の例外クラスのリスト
        retry_if_result: 結果に基づいてリトライするかどうかを判断する関数
        retry_key: 設定から取得するリトライ設定のキー
        
    Returns:
        デコレータ関数
        
    Examples:
        >>> @async_retry(max_retries=3, retry_delay=1.0)
        >>> async def unstable_async_function():
        >>>     if random.random() < 0.7:
        >>>         raise ValueError("Random error")
        >>>     return "Success"
        
        >>> @async_retry(retry_key="DB_QUERY")
        >>> async def db_query():
        >>>     # データベースクエリ処理
        >>>     pass
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            _max_retries = _resolve_retry_setting(max_retries, "MAX_RETRIES", DEFAULT_MAX_RETRIES, retry_key)
            _retry_delay = _resolve_retry_setting(retry_delay, "RETRY_DELAY", DEFAULT_RETRY_DELAY, retry_key)
            _max_retry_delay = _resolve_retry_setting(max_retry_delay, "MAX_RETRY_DELAY", DEFAULT_MAX_RETRY_DELAY, retry_key)
            _retry_jitter = _resolve_retry_setting(retry_jitter, "RETRY_JITTER", DEFAULT_RETRY_JITTER, retry_key)
            _backoff_factor = _resolve_retry_setting(backoff_factor, "BACKOFF_FACTOR", DEFAULT_BACKOFF_FACTOR, retry_key)
            
            _retry_strategy = retry_strategy
            if _retry_strategy is None and retry_key:
                _retry_strategy = get_retry_strategy(retry_key)
            if _retry_strategy is None or isinstance(_retry_strategy, str):
                try:
                    if isinstance(_retry_strategy, str):
                        _retry_strategy = RetryStrategy(_retry_strategy.lower())
                    else:
                        _retry_strategy = RetryStrategy.EXPONENTIAL
                except ValueError:
                    logger.warning(f"Invalid retry strategy: {_retry_strategy}, using EXPONENTIAL")
                    _retry_strategy = RetryStrategy.EXPONENTIAL
            
            _retry_if_result = retry_if_result or retry_result_evaluator
            
            _retry_exceptions = retry_exceptions
            if _retry_exceptions is None:
                _retry_exceptions = [Exception]
            
            retry_count = 0
            last_exception = None
            
            while True:
                try:
                    result = await func(*args, **kwargs)
                    
                    if _retry_if_result(result):
                        if retry_count >= _max_retries:
                            logger.warning(
                                f"Max retries exceeded for {func.__name__} due to result evaluation",
                                extra={"retry_count": retry_count, "result": result}
                            )
                            return result
                        
                        retry_count += 1
                        delay = calculate_next_delay(
                            retry_count, _retry_strategy, _retry_delay,
                            _max_retry_delay, _backoff_factor, _retry_jitter
                        )
                        
                        await asyncio.sleep(delay)
                        continue
                    
                    return result
                    
                except tuple(_retry_exceptions) as e:
                    last_exception = e
                    
                    if not should_retry(e, _retry_exceptions, _max_retries, retry_count):
                        logger.warning(
                            f"Max retries exceeded for {func.__name__}",
                            extra={"retry_count": retry_count, "exception": str(e)}
                        )
                        if isinstance(e, CaseforgeException):
                            raise
                        raise MaxRetriesExceededException(
                            f"最大リトライ回数({_max_retries})を超えました: {func.__name__}",
                            details={
                                "function": func.__name__,
                                "max_retries": _max_retries,
                                "original_exception": str(e),
                                "exception_type": type(e).__name__
                            }
                        ) from e
                    
                    retry_count += 1
                    delay = calculate_next_delay(
                        retry_count, _retry_strategy, _retry_delay,
                        _max_retry_delay, _backoff_factor, _retry_jitter
                    )
                    
                    await asyncio.sleep(delay)
        
        return cast(AsyncF, wrapper)
    
    return decorator
    


def retry_result_evaluator(result: Any) -> bool:
    """
    結果に基づいてリトライすべきかどうかを判断するデフォルト評価関数
    
    Args:
        result: 関数の戻り値
        
    Returns:
        リトライすべきかどうか（デフォルトではリトライしない）
    """
    return False
def _resolve_retry_setting(
    value: Optional[Union[int, float, str]],
    config_name: str,
    default: Union[int, float],
    retry_key: Optional[str]
) -> Union[int, float]:
    """
    リトライ設定値を解決する
    
    Args:
        value: 直接指定された値
        config_name: 設定名
        default: デフォルト値
        retry_key: 設定から取得するリトライ設定のキー
        
    Returns:
        解決された設定値
    """
    if value is not None:
        if isinstance(value, str):
            try:
                if isinstance(default, int):
                    return int(value)
                return float(value)
            except ValueError:
                logger.warning(f"Invalid retry value: {value}, using default")
                return default
        return value
    
    if retry_key is not None:
        return get_retry_config(retry_key, config_name, default)
    
    return default


def run_with_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY,
    retry_jitter: float = DEFAULT_RETRY_JITTER,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    retry_if_result: Optional[Callable[[Any], bool]] = None,
    **kwargs: Any
) -> T:
    """
    関数を指定したリトライ設定で実行する
    
    Args:
        func: 実行する関数
        *args: 関数の位置引数
        max_retries: 最大リトライ回数
        retry_delay: 初期リトライ間隔（秒）
        max_retry_delay: 最大リトライ間隔（秒）
        retry_jitter: ジッター（ランダム性）の大きさ
        backoff_factor: バックオフ係数
        retry_strategy: リトライ戦略
        retry_exceptions: リトライ対象の例外クラスのリスト
        retry_if_result: 結果に基づいてリトライするかどうかを判断する関数
        **kwargs: 関数のキーワード引数
        
    Returns:
        関数の戻り値
        
    Examples:
        >>> result = run_with_retry(
        >>>     unstable_function,
        >>>     max_retries=5,
        >>>     retry_delay=1.0,
        >>>     retry_strategy=RetryStrategy.EXPONENTIAL
        >>> )
    """
    _retry_if_result = retry_if_result or retry_result_evaluator
    
    _retry_exceptions = retry_exceptions
    if _retry_exceptions is None:
        _retry_exceptions = [Exception]
    
    retry_count = 0
    last_exception = None
    
    while True:
        try:
            result = func(*args, **kwargs)
            
            if _retry_if_result(result):
                if retry_count >= max_retries:
                    logger.warning(
                        f"Max retries exceeded for {func.__name__} due to result evaluation",
                        extra={"retry_count": retry_count, "result": result}
                    )
                    return result
                
                retry_count += 1
                delay = calculate_next_delay(
                    retry_count, retry_strategy, retry_delay,
                    max_retry_delay, backoff_factor, retry_jitter
                )
                
                time.sleep(delay)
                continue
            
            return result
            
        except tuple(_retry_exceptions) as e:
            last_exception = e
            
            if not should_retry(e, _retry_exceptions, max_retries, retry_count):
                logger.warning(
                    f"Max retries exceeded for {func.__name__}",
                    extra={"retry_count": retry_count, "exception": str(e)}
                )
                if isinstance(e, CaseforgeException):
                    raise
                raise MaxRetriesExceededException(
                    f"最大リトライ回数({max_retries})を超えました: {func.__name__}",
                    details={
                        "function": func.__name__,
                        "max_retries": max_retries,
                        "original_exception": str(e),
                        "exception_type": type(e).__name__
                    }
                ) from e
            
            retry_count += 1
            delay = calculate_next_delay(
                retry_count, retry_strategy, retry_delay,
                max_retry_delay, backoff_factor, retry_jitter
            )
            
            time.sleep(delay)


async def run_async_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    max_retry_delay: float = DEFAULT_MAX_RETRY_DELAY,
    retry_jitter: float = DEFAULT_RETRY_JITTER,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retry_exceptions: Optional[List[Type[Exception]]] = None,
    retry_if_result: Optional[Callable[[Any], bool]] = None,
    **kwargs: Any
) -> Any:
    """
    非同期関数を指定したリトライ設定で実行する
    
    Args:
        func: 実行する非同期関数
        *args: 関数の位置引数
        max_retries: 最大リトライ回数
        retry_delay: 初期リトライ間隔（秒）
        max_retry_delay: 最大リトライ間隔（秒）
        retry_jitter: ジッター（ランダム性）の大きさ
        backoff_factor: バックオフ係数
        retry_strategy: リトライ戦略
        retry_exceptions: リトライ対象の例外クラスのリスト
        retry_if_result: 結果に基づいてリトライするかどうかを判断する関数
        **kwargs: 関数のキーワード引数
        
    Returns:
        関数の戻り値
        
    Examples:
        >>> result = await run_async_with_retry(
        >>>     unstable_async_function,
        >>>     max_retries=5,
        >>>     retry_delay=1.0,
        >>>     retry_strategy=RetryStrategy.EXPONENTIAL
        >>> )
    """
    _retry_if_result = retry_if_result or retry_result_evaluator
    
    _retry_exceptions = retry_exceptions
    if _retry_exceptions is None:
        _retry_exceptions = [Exception]
    
    retry_count = 0
    last_exception = None
    
    while True:
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, lambda: func(*args, **kwargs)
                )
            
            if _retry_if_result(result):
                if retry_count >= max_retries:
                    logger.warning(
                        f"Max retries exceeded for {func.__name__} due to result evaluation",
                        extra={"retry_count": retry_count, "result": result}
                    )
                    return result
                
                retry_count += 1
                delay = calculate_next_delay(
                    retry_count, retry_strategy, retry_delay,
                    max_retry_delay, backoff_factor, retry_jitter
                )
                
                await asyncio.sleep(delay)
                continue
            
            return result
            
        except tuple(_retry_exceptions) as e:
            last_exception = e
            
            if not should_retry(e, _retry_exceptions, max_retries, retry_count):
                logger.warning(
                    f"Max retries exceeded for {func.__name__}",
                    extra={"retry_count": retry_count, "exception": str(e)}
                )
                if isinstance(e, CaseforgeException):
                    raise
                raise MaxRetriesExceededException(
                    f"最大リトライ回数({max_retries})を超えました: {func.__name__}",
                    details={
                        "function": func.__name__,
                        "max_retries": max_retries,
                        "original_exception": str(e),
                        "exception_type": type(e).__name__
                    }
                ) from e
            
            retry_count += 1
            delay = calculate_next_delay(
                retry_count, retry_strategy, retry_delay,
                max_retry_delay, backoff_factor, retry_jitter
            )
            
            await asyncio.sleep(delay)
