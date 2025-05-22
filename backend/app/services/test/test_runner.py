"""
テスト実行クラスモジュール

このモジュールは、テスト実行のための抽象基底クラスと具体的な実装クラスを提供します。
テスト実行の堅牢性、柔軟性、保守性を向上させるための設計になっています。
"""

import abc
import asyncio
import httpx
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional, TypeVar, Generic, Callable
from pydantic import BaseModel, Field

from sqlmodel import Session, select

from app.config import settings
from app.logging_config import logger
from app.models import Service, TestSuite, TestRun, StepResult, TestStep, TestCase, TestCaseResult
from app.services.chain_generator import ChainStore
from app.exceptions import TimeoutException, CaseforgeException, ErrorCode
from app.utils.timeout import async_timeout
from app.utils.retry import async_retry, RetryStrategy
from app.services.test.variable_manager import VariableManager, VariableScope, VariableType

T = TypeVar('T')
ResultT = TypeVar('ResultT')


class TestStatus(str, Enum):
    """テストの実行状態を表す列挙型"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    COMPLETED = "completed"


class TestRunnerError(CaseforgeException):
    """テスト実行に関するエラー"""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.TEST_EXECUTION_ERROR, details)


class TestTimeoutError(TestRunnerError):
    """テスト実行のタイムアウトエラー"""
    def __init__(
        self,
        message: str = "テスト実行がタイムアウトしました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


class TestResult(BaseModel):
    """テスト結果の基底クラス"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: TestStatus = TestStatus.PENDING
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    def complete(self, status: TestStatus, error_message: Optional[str] = None) -> None:
        """テスト結果を完了状態に更新する"""
        self.end_time = datetime.now(timezone.utc)
        self.status = status
        if error_message:
            self.error_message = error_message
        
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class StepTestResult(TestResult):
    """テストステップの実行結果"""
    sequence: int
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    response_body: Optional[Any] = None
    passed: bool = False
    extracted_values: Dict[str, Any] = Field(default_factory=dict)


class CaseTestResult(TestResult):
    """テストケースの実行結果"""
    case_id: str
    step_results: List[StepTestResult] = Field(default_factory=list)


class SuiteTestResult(TestResult):
    """テストスイートの実行結果"""
    suite_id: str
    test_case_results: List[CaseTestResult] = Field(default_factory=list)
    success: bool = False


class TestRunner(Generic[ResultT], abc.ABC):
    """テスト実行の抽象基底クラス"""
    
    def __init__(self, session: Optional[Session] = None, storage_path: Optional[str] = None):
        """
        テスト実行クラスの初期化
        
        Args:
            session: データベースセッション
            storage_path: 変数の永続化に使用するファイルパス
        """
        self.session = session
        self.variable_manager = VariableManager(storage_path)
        self._setup_hooks = []
        self._teardown_hooks = []
        self._before_test_hooks = []
        self._after_test_hooks = []
        self._before_step_hooks = []
        self._after_step_hooks = []
    
    @abc.abstractmethod
    async def run(self, *args, **kwargs) -> ResultT:
        """
        テストを実行する抽象メソッド
        
        Returns:
            テスト実行結果
        """
        pass
    
    def add_setup_hook(self, hook: Callable[[], None]) -> None:
        """
        セットアップフックを追加する
        
        Args:
            hook: セットアップ処理を行う関数
        """
        self._setup_hooks.append(hook)
    
    def add_teardown_hook(self, hook: Callable[[], None]) -> None:
        """
        ティアダウンフックを追加する
        
        Args:
            hook: ティアダウン処理を行う関数
        """
        self._teardown_hooks.append(hook)
    
    def add_before_test_hook(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """
        テスト実行前フックを追加する
        
        Args:
            hook: テスト実行前処理を行う関数
        """
        self._before_test_hooks.append(hook)
    
    def add_after_test_hook(self, hook: Callable[[Dict[str, Any], ResultT], None]) -> None:
        """
        テスト実行後フックを追加する
        
        Args:
            hook: テスト実行後処理を行う関数
        """
        self._after_test_hooks.append(hook)
    
    def add_before_step_hook(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """
        ステップ実行前フックを追加する
        
        Args:
            hook: ステップ実行前処理を行う関数
        """
        self._before_step_hooks.append(hook)
    
    def add_after_step_hook(self, hook: Callable[[Dict[str, Any], Any], None]) -> None:
        """
        ステップ実行後フックを追加する
        
        Args:
            hook: ステップ実行後処理を行う関数
        """
        self._after_step_hooks.append(hook)
    
    async def _run_setup_hooks(self) -> None:
        """セットアップフックを実行する"""
        for hook in self._setup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Error in setup hook: {e}", exc_info=True)
                raise TestRunnerError(f"セットアップフックでエラーが発生しました: {str(e)}")
    
    async def _run_teardown_hooks(self) -> None:
        """ティアダウンフックを実行する"""
        for hook in self._teardown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Error in teardown hook: {e}", exc_info=True)
    
    async def _run_before_test_hooks(self, test_data: Dict[str, Any]) -> None:
        """
        テスト実行前フックを実行する
        
        Args:
            test_data: テストデータ
        """
        for hook in self._before_test_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(test_data)
                else:
                    hook(test_data)
            except Exception as e:
                logger.error(f"Error in before test hook: {e}", exc_info=True)
                raise TestRunnerError(f"テスト実行前フックでエラーが発生しました: {str(e)}")
    
    async def _run_after_test_hooks(self, test_data: Dict[str, Any], result: ResultT) -> None:
        """
        テスト実行後フックを実行する
        
        Args:
            test_data: テストデータ
            result: テスト結果
        """
        for hook in self._after_test_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(test_data, result)
                else:
                    hook(test_data, result)
            except Exception as e:
                logger.error(f"Error in after test hook: {e}", exc_info=True)
    
    async def _run_before_step_hooks(self, step_data: Dict[str, Any]) -> None:
        """
        ステップ実行前フックを実行する
        
        Args:
            step_data: ステップデータ
        """
        for hook in self._before_step_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(step_data)
                else:
                    hook(step_data)
            except Exception as e:
                logger.error(f"Error in before step hook: {e}", exc_info=True)
                raise TestRunnerError(f"ステップ実行前フックでエラーが発生しました: {str(e)}")
    
    async def _run_after_step_hooks(self, step_data: Dict[str, Any], result: Any) -> None:
        """
        ステップ実行後フックを実行する
        
        Args:
            step_data: ステップデータ
            result: ステップ結果
        """
        for hook in self._after_step_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(step_data, result)
                else:
                    hook(step_data, result)
            except Exception as e:
                logger.error(f"Error in after step hook: {e}", exc_info=True)
    
    def _extract_values(self, response_body: Any, extract_rules: Dict[str, str]) -> Dict[str, Any]:
        """
        レスポンスから値を抽出する
        
        Args:
            response_body: レスポンスボディ
            extract_rules: 抽出ルール（キー: 変数名, 値: JSONPath式）
            
        Returns:
            抽出した値の辞書
        """
        extracted = {}
        
        if not response_body or not extract_rules:
            return extracted
        
        for key, path in extract_rules.items():
            try:
                if path.startswith("$."):
                    import jsonpath_ng
                    jsonpath_expr = jsonpath_ng.parse(path)
                    matches = jsonpath_expr.find(response_body)
                    if matches:
                        extracted[key] = matches[0].value
                        logger.debug(f"Extracted value for {key}: {extracted[key]}")
            except Exception as e:
                logger.error(f"Error extracting value for {key} with path {path}: {e}")
        
        return extracted
    
    def save_test_result(self, result: ResultT) -> None:
        """
        テスト結果を保存する
        
        Args:
            result: テスト結果
        """
        logger.info(f"Test result: {result}")


class APITestRunner(TestRunner[StepTestResult]):
    """API単体テスト実行クラス"""
    
    def __init__(
        self,
        session: Optional[Session] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        storage_path: Optional[str] = None
    ):
        """
        API単体テスト実行クラスの初期化
        
        Args:
            session: データベースセッション
            base_url: APIのベースURL
            timeout: HTTPリクエストのタイムアウト時間（秒）
            storage_path: 変数の永続化に使用するファイルパス
        """
        super().__init__(session, storage_path)
        self.base_url = base_url or settings.TEST_TARGET_URL
        self.timeout = timeout or settings.TIMEOUT_HTTP_REQUEST
        self.client = None
    
    async def setup(self) -> None:
        """テスト実行前の準備"""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        await self._run_setup_hooks()
    
    async def teardown(self) -> None:
        """テスト実行後の後処理"""
        if self.client:
            await self.client.aclose()
        await self._run_teardown_hooks()
    
    @async_timeout(timeout_key="HTTP_REQUEST")
    async def run(self, test_data: Dict[str, Any]) -> StepTestResult:
        """
        APIテストを実行する
        
        Args:
            test_data: テストデータ
            
        Returns:
            テスト実行結果
        """
        try:
            await self.setup()
            await self._run_before_test_hooks(test_data)
            
            result = StepTestResult(
                name=test_data.get("name", "Unnamed API Test"),
                sequence=test_data.get("sequence", 1),
                method=test_data.get("method", "GET"),
                path=test_data.get("path", "/"),
                status=TestStatus.RUNNING
            )
            
            method = test_data.get("method", "GET")
            path = await self.variable_manager.replace_variables_in_string_async(test_data.get("path", "/"))
            
            request = test_data.get("request", {})
            headers = await self.variable_manager.replace_variables_in_object_async(request.get("headers", {}))
            body = test_data.get("request_body")
            params = await self.variable_manager.replace_variables_in_object_async(request.get("params", {}))
            
            if body:
                body = await self.variable_manager.replace_variables_in_object_async(body)
            
            logger.info(f"Executing request: {method} {path} with headers={headers}, params={params}, body={body}")
            
            @async_retry(
                retry_key="API_CALL",
                retry_exceptions=[httpx.RequestError, httpx.HTTPStatusError, ConnectionError, TimeoutError],
                retry_strategy=RetryStrategy.EXPONENTIAL
            )
            async def execute_request_with_retry():
                return await self.client.request(
                    method=method,
                    url=path,
                    headers=headers,
                    json=body,
                    params=params
                )
            
            start_time = datetime.now(timezone.utc)
            response = await execute_request_with_retry()
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result.status_code = response.status_code
            result.response_time = response_time
            
            try:
                response_body = response.json()
                result.response_body = response_body
            except json.JSONDecodeError:
                result.response_body = response.text
            
            expected_status = test_data.get("expected_status")
            if expected_status:
                result.passed = response.status_code == expected_status
            else:
                result.passed = 200 <= response.status_code < 300
            
            extract_rules = test_data.get("extract_rules", {})
            if extract_rules:
                extracted_values = self._extract_values(result.response_body, extract_rules)
                result.extracted_values = extracted_values
                
                for key, value in extracted_values.items():
                    self.variable_manager.set_variable(key, value, VariableScope.STEP)
            
            if result.passed:
                result.complete(TestStatus.PASSED)
            else:
                result.complete(TestStatus.FAILED, f"Expected status code {expected_status}, got {result.status_code}")
            
            await self._run_after_test_hooks(test_data, result)
            return result
            
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            result = StepTestResult(
                name=test_data.get("name", "Unnamed API Test"),
                sequence=test_data.get("sequence", 1),
                method=test_data.get("method", "GET"),
                path=test_data.get("path", "/"),
                status=TestStatus.ERROR,
                error_message=f"Request error: {str(e)}"
            )
            result.complete(TestStatus.ERROR, f"Request error: {str(e)}")
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            result = StepTestResult(
                name=test_data.get("name", "Unnamed API Test"),
                sequence=test_data.get("sequence", 1),
                method=test_data.get("method", "GET"),
                path=test_data.get("path", "/"),
                status=TestStatus.ERROR,
                error_message=f"Unexpected error: {str(e)}"
            )
            result.complete(TestStatus.ERROR, f"Unexpected error: {str(e)}")


class ChainTestRunner(TestRunner[SuiteTestResult]):
    """テストチェーン実行クラス"""
    
    def __init__(
        self,
        session: Session,
        test_suite: TestSuite,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        storage_path: Optional[str] = None
    ):
        """
        テストチェーン実行クラスの初期化
        
        Args:
            session: データベースセッション
            test_suite: 実行するテストスイート
            base_url: APIのベースURL
            timeout: HTTPリクエストのタイムアウト時間（秒）
            storage_path: 変数の永続化に使用するファイルパス
        """
        super().__init__(session, storage_path)
        self.test_suite = test_suite
        self.base_url = base_url or settings.TEST_TARGET_URL
        self.timeout = timeout or settings.TIMEOUT_HTTP_REQUEST
        self.client = None
    
    async def setup(self) -> None:
        """テスト実行前の準備"""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        await self._run_setup_hooks()
    
    async def teardown(self) -> None:
        """テスト実行後の後処理"""
        if self.client:
            await self.client.aclose()
        await self._run_teardown_hooks()
    
    @async_timeout(timeout_key="TEST_SUITE")
    async def run(self, test_suite_data: Dict[str, Any]) -> SuiteTestResult:
        """
        テストスイートを実行する
        
        Args:
            test_suite_data: テストスイートデータ
            
        Returns:
            テスト実行結果
        """
        try:
            await self.setup()
            await self._run_before_test_hooks(test_suite_data)
            
            suite_result = SuiteTestResult(
                name=test_suite_data.get("name", "Unnamed TestSuite"),
                suite_id=test_suite_data.get("id", str(uuid.uuid4())),
                status=TestStatus.RUNNING
            )
            
            for case_data in test_suite_data.get("test_cases", []):
                case_result = await self._run_test_case(case_data)
                suite_result.test_case_results.append(case_result)
                
                if case_result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                    suite_result.status = TestStatus.FAILED
                    break
            
            if all(case.status == TestStatus.PASSED for case in suite_result.test_case_results):
                suite_result.complete(TestStatus.COMPLETED)
                suite_result.success = True
            else:
                suite_result.complete(TestStatus.FAILED)
                suite_result.success = False
            
            await self._run_after_test_hooks(test_suite_data, suite_result)
            return suite_result
            
        except TimeoutException as e:
            logger.error(f"Timeout error: {e}")
            suite_result = SuiteTestResult(
                name=test_suite_data.get("name", "Unnamed TestSuite"),
                suite_id=test_suite_data.get("id", str(uuid.uuid4())),
                status=TestStatus.TIMEOUT,
                error_message=f"Timeout error: {str(e)}"
            )
            suite_result.complete(TestStatus.TIMEOUT, f"Timeout error: {str(e)}")
            return suite_result
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            suite_result = SuiteTestResult(
                name=test_suite_data.get("name", "Unnamed TestSuite"),
                suite_id=test_suite_data.get("id", str(uuid.uuid4())),
                status=TestStatus.ERROR,
                error_message=f"Unexpected error: {str(e)}"
            )
            suite_result.complete(TestStatus.ERROR, f"Unexpected error: {str(e)}")
            return suite_result
            
        finally:
            await self.teardown()
    
    async def _run_test_case(self, case_data: Dict[str, Any]) -> CaseTestResult:
        """
        テストケースを実行する
        
        Args:
            case_data: テストケースデータ
            
        Returns:
            テストケース実行結果
        """
        case_result = CaseTestResult(
            name=case_data.get("name", "Unnamed TestCase"),
            case_id=case_data.get("case_id", str(uuid.uuid4())),
            status=TestStatus.RUNNING
        )
        
        self.variable_manager.clear_scope(VariableScope.STEP)
        self.variable_manager.clear_scope(VariableScope.CASE)
        
        try:
            for step_data in case_data.get("test_steps", []):
                step_result = await self._execute_step(step_data)
                case_result.step_results.append(step_result)
                
                if not step_result.passed:
                    case_result.complete(TestStatus.FAILED, step_result.error_message)
                    break
                
                for key, value in step_result.extracted_values.items():
                    self.variable_manager.set_variable(key, value, VariableScope.CASE)
            
            if case_result.status != TestStatus.FAILED:
                if case_data.get("error_type") is not None:
                    case_result.complete(TestStatus.PASSED)
                else:
                    case_result.complete(TestStatus.PASSED)
        
        except Exception as e:
            logger.error(f"Error running test case {case_result.case_id}: {e}", exc_info=True)
            case_result.complete(TestStatus.ERROR, f"Unexpected error: {str(e)}")
        
        return case_result
    
    @async_timeout(timeout_key="HTTP_REQUEST")
    async def _execute_step(self, step_data: Dict[str, Any]) -> StepTestResult:
        """
        テストステップを実行する
        
        Args:
            step_data: テストステップデータ
            
        Returns:
            テストステップ実行結果
        """
        self.variable_manager.clear_scope(VariableScope.STEP)
        
        await self._run_before_step_hooks(step_data)
        
        step_result = StepTestResult(
            name=step_data.get("name", "Unnamed Step"),
            sequence=step_data.get("sequence", 0),
            method=step_data.get("method"),
            path=step_data.get("path"),
            status=TestStatus.RUNNING
        )
        
        try:
            path = await self.variable_manager.replace_variables_in_string_async(step_data["path"])
            
            request = step_data.get("request", {})
            headers = await self.variable_manager.replace_variables_in_object_async(request.get("headers", {}))
            body = step_data.get("request_body")
            params = await self.variable_manager.replace_variables_in_object_async(request.get("params", {}))
            
            if body:
                body = await self.variable_manager.replace_variables_in_object_async(body)
            
            logger.info(f"Executing request: {step_data['method']} {path} with headers={headers}, params={params}, body={body}")
            
            @async_retry(
                retry_key="API_CALL",
                retry_exceptions=[httpx.RequestError, httpx.HTTPStatusError, ConnectionError, TimeoutError],
                retry_strategy=RetryStrategy.EXPONENTIAL
            )
            async def execute_request_with_retry():
                return await self.client.request(
                    method=step_data["method"],
                    url=path,
                    headers=headers,
                    json=body,
                    params=params
                )
            
            start_time = datetime.now(timezone.utc)
            response = await execute_request_with_retry()
            end_time = datetime.now(timezone.utc)
            response_time = (end_time - start_time).total_seconds() * 1000
            
            step_result.status_code = response.status_code
            step_result.response_time = response_time
            
            try:
                response_body = response.json()
                step_result.response_body = response_body
            except json.JSONDecodeError:
                step_result.response_body = response.text
            
            expected_status = step_data.get("expected_status")
            if expected_status:
                step_result.passed = response.status_code == expected_status
            else:
                step_result.passed = 200 <= response.status_code < 300
            
            extract_rules = step_data.get("extract_rules", {})
            if extract_rules:
                extracted_values = self._extract_values(step_result.response_body, extract_rules)
                step_result.extracted_values = extracted_values
                
                for key, value in extracted_values.items():
                    self.variable_manager.set_variable(key, value, VariableScope.STEP)
            
            if step_result.passed:
                step_result.complete(TestStatus.PASSED)
            else:
                step_result.complete(TestStatus.FAILED, f"Expected status code {expected_status}, got {step_result.status_code}")
            
            await self._run_after_step_hooks(step_data, step_result)
            return step_result
            
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            step_result.complete(TestStatus.ERROR, f"Request error: {str(e)}")
            return step_result
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            step_result.complete(TestStatus.ERROR, f"Unexpected error: {str(e)}")
            return step_result            
        finally:
            await self.teardown()


class TestRunnerFactory:
    """テスト実行クラスのファクトリークラス"""
    
    @staticmethod
    def create_runner(
        runner_type: str,
        session: Optional[Session] = None,
        test_suite: Optional[TestSuite] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        storage_path: Optional[str] = None
    ) -> TestRunner:
        """
        テスト実行クラスのインスタンスを作成する
        
        Args:
            runner_type: 実行クラスの種類（"api", "chain"）
            session: データベースセッション
            test_suite: 実行するテストスイート
            base_url: APIのベースURL
            timeout: HTTPリクエストのタイムアウト時間（秒）
            storage_path: 変数の永続化に使用するファイルパス
            
        Returns:
            テスト実行クラスのインスタンス
            
        Raises:
            ValueError: 不明なrunner_typeが指定された場合
        """
        if runner_type.lower() == "api":
            return APITestRunner(
                session=session,
                base_url=base_url,
                timeout=timeout,
                storage_path=storage_path
            )
        elif runner_type.lower() == "chain":
            if not test_suite:
                raise ValueError("test_suite is required for ChainTestRunner")
            if not session:
                raise ValueError("session is required for ChainTestRunner")
            return ChainTestRunner(
                session=session,
                test_suite=test_suite,
                base_url=base_url,
                timeout=timeout,
                storage_path=storage_path
            )
        else:
            raise ValueError(f"Unknown runner type: {runner_type}")
    
    @staticmethod
    async def run_test_suite(
        service_id: str,
        suite_id: Optional[str] = None,
        session: Optional[Session] = None,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        サービスのテストスイートを実行する
        
        Args:
            service_id: サービスID
            suite_id: 特定のテストスイートIDを指定する場合
            session: データベースセッション
            base_url: APIのベースURL
            
        Returns:
            実行結果
        """
        from sqlmodel import Session as SQLModelSession
        from app.models import engine
        
        if session is None:
            session = SQLModelSession(engine)
        
        try:
            chain_store = ChainStore()
            
            if suite_id:
                test_suite_data = chain_store.get_test_suite(service_id, suite_id)
                if not test_suite_data:
                    logger.warning(f"TestSuite not found: {suite_id}")
                    return {"status": "error", "message": f"TestSuite not found: {suite_id}"}
                test_suites_data = [test_suite_data]
            else:
                test_suites_info = chain_store.list_test_suites(service_id)
                test_suites_data = []
                for test_suite_info in test_suites_info:
                    test_suite_data = chain_store.get_test_suite(service_id, test_suite_info["id"])
                    if test_suite_data:
                        test_suites_data.append(test_suite_data)
            
            if not test_suites_data:
                logger.warning(f"No test suites found for service {service_id}")
                return {"status": "error", "message": "No test suites found"}
            
            service_query = select(Service).where(Service.service_id == service_id)
            db_service = session.exec(service_query).first()
            
            if not db_service:
                logger.error(f"Service not found: {service_id}")
                return {"status": "error", "message": f"Service not found: {service_id}"}
            
            results = []
            
            for test_suite_data in test_suites_data:
                suite_id = test_suite_data.get("id")
                if not suite_id:
                    logger.error(f"TestSuite ID not found in test suite data")
                    continue
                
                test_suite_query = select(TestSuite).where(TestSuite.id == suite_id)
                db_test_suite = session.exec(test_suite_query).first()
                
                if not db_test_suite:
                    logger.error(f"TestSuite not found in database: {suite_id}")
                    continue
                
                run_id = str(uuid.uuid4())
                test_run = TestRun(
                    run_id=run_id,
                    suite_id=db_test_suite.id,
                    service_id=db_service.id,
                    status="running",
                    start_time=datetime.now(timezone.utc)
                )
                session.add(test_run)
                session.commit()
                session.refresh(test_run)
                
                runner = TestRunnerFactory.create_runner(
                    runner_type="chain",
                    session=session,
                    test_suite=db_test_suite,
                    base_url=base_url or db_service.base_url
                )
                
                result = await runner.run(test_suite_data)
                results.append(result)
                
                test_run.status = result.status
                test_run.end_time = datetime.now(timezone.utc)
                
                for case_result in result.test_case_results:
                    case_query = select(TestCase).where(
                        TestCase.suite_id == db_test_suite.id,
                        TestCase.id == case_result.case_id
                    )
                    db_case = session.exec(case_query).first()
                    
                    if not db_case:
                        logger.error(f"TestCase not found for test suite {db_test_suite.id}, case_id {case_result.case_id}")
                        continue
                    
                    test_case_result_obj = TestCaseResult(
                        test_run_id=test_run.id,
                        case_id=db_case.id,
                        status=case_result.status,
                        error_message=case_result.error_message
                    )
                    session.add(test_case_result_obj)
                    session.flush()
                    
                    for step_result in case_result.step_results:
                        step_query = select(TestStep).where(
                            TestStep.case_id == db_case.id,
                            TestStep.sequence == step_result.sequence
                        )
                        db_step = session.exec(step_query).first()
                        
                        if not db_step:
                            logger.error(f"Step not found for test case {db_case.id}, sequence {step_result.sequence}")
                            continue
                        
                        step_result_obj = StepResult(
                            test_case_result_id=test_case_result_obj.id,
                            step_id=db_step.id,
                            sequence=step_result.sequence,
                            status_code=step_result.status_code,
                            passed=step_result.passed,
                            response_time=step_result.response_time,
                            error_message=step_result.error_message,
                            response_body=step_result.response_body
                        )
                        session.add(step_result_obj)
                
                session.commit()
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            log_path = f"{settings.LOG_DIR}/{service_id}"
            os.makedirs(log_path, exist_ok=True)
            
            with open(f"{log_path}/{timestamp}.json", "w") as f:
                json.dump([result.dict() for result in results], f, default=str, indent=2)
            
            return {
                "status": "completed",
                "message": f"Executed {len(results)} test suites",
                "results": [result.dict() for result in results]
            }
            
        except Exception as e:
            logger.error(f"Error running test suites for service {service_id}: {e}", exc_info=True)
            return {"status": "error", "message": f"Failed to run test suites: {str(e)}"}
