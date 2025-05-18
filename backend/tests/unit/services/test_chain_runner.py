import pytest
from app.services.chain_runner import ChainRunner, run_test_suites, list_test_runs, get_test_run
from unittest.mock import patch, MagicMock, AsyncMock
import json
import uuid
from datetime import datetime, timezone
import httpx
from sqlmodel import select

SAMPLE_TEST_SUITE = {
    "name": "POST /users エンドポイントのテスト",
    "target_method": "POST",
    "target_path": "/users",
    "test_cases": [
        {
            "name": "正常系",
            "description": "正常なユーザー作成と取得",
            "error_type": None,
            "test_steps": [
                {
                    "sequence": 0,
                    "method": "POST",
                    "path": "/users",
                    "request_body": {"name": "Test User", "email": "test@example.com"},
                    "extract_rules": {"user_id": "$.id"},
                    "expected_status": 201
                },
                {
                    "sequence": 1,
                    "method": "GET",
                    "path": "/users/{user_id}",
                    "request_params": {"user_id": "{user_id}"}, # 抽出した値を使用
                    "expected_status": 200
                }
            ]
        },
        {
            "name": "必須フィールド欠落",
            "description": "emailフィールドがない場合",
            "error_type": "missing_field",
            "test_steps": [
                {
                    "sequence": 0,
                    "method": "POST",
                    "path": "/users",
                    "request_body": {"name": "Test User"},
                    "expected_status": 400
                }
            ]
        }
    ]
}

SAMPLE_RESPONSES = {
    "POST /users": httpx.Response(
        status_code=201,
        json={"id": "123", "name": "Test User", "email": "test@example.com"}
    ),
    "GET /users/123": httpx.Response(
        status_code=200,
        json={"id": "123", "name": "Test User", "email": "test@example.com"}
    ),
    "POST /users (missing field)": httpx.Response(
        status_code=400,
        json={"detail": "Missing required field: email"}
    )
}

@pytest.mark.asyncio
async def test_execute_step():
    """ステップ実行のテスト"""
    mock_client = MagicMock()
    mock_client.request = AsyncMock()
    mock_client.request.return_value = SAMPLE_RESPONSES["POST /users"]
    
    mock_session = MagicMock()
    mock_chain = MagicMock()

    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    step = SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"][0]
    result = await runner._execute_step(mock_client, step)
    
    assert result["passed"] is True
    assert result["status_code"] == 201
    assert "response_body" in result
    assert result["response_body"]["id"] == "123"
    
    mock_client.request.assert_called_once_with(
        method="POST",
        url="/users",
        headers={},
        json={"name": "Test User", "email": "test@example.com"},
        params={}
    )

@pytest.mark.asyncio
async def test_extract_values():
    """値抽出のテスト"""
    mock_session = MagicMock()
    mock_chain = MagicMock()

    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    response_body = {"id": "123", "name": "Test User", "email": "test@example.com"}
    extract_rules = {"user_id": "$.id", "user_name": "$.name"}
    
    extracted = runner._extract_values(response_body, extract_rules)
    
    assert extracted["user_id"] == "123"
    assert extracted["user_name"] == "Test User"

@pytest.mark.asyncio
async def test_variable_manager_replace():
    """VariableManagerによる変数置換のテスト"""
    mock_session = MagicMock()
    mock_chain = MagicMock()

    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    
    from app.services.test.variable_manager import VariableScope
    path = "/users/${user_id}/posts/${post_id}"
    runner.variable_manager.set_variable("user_id", "123", VariableScope.CASE)
    runner.variable_manager.set_variable("post_id", "456", VariableScope.CASE)
    
    result = await runner.variable_manager.replace_variables_in_string_async(path)
    
    assert result == "/users/123/posts/456"
    
    body = {
        "user_id": "${user_id}",
        "data": {
            "name": "Test",
            "reference": "${reference_id}"
        },
        "items": ["${item1}", "${item2}"]
    }
    
    runner.variable_manager.set_variable("reference_id", "456", VariableScope.CASE)
    runner.variable_manager.set_variable("item1", "item1", VariableScope.CASE)
    runner.variable_manager.set_variable("item2", "item2", VariableScope.CASE)
    
    result = await runner.variable_manager.replace_variables_in_object_async(body)
    
    assert result["user_id"] == "123"
    assert result["data"]["reference"] == "456"
    assert result["items"][0] == "item1"
    assert result["items"][1] == "item2"

@pytest.mark.asyncio
async def test_run_test_suite():
    """テストスイート実行のテスト"""
    with patch("httpx.AsyncClient") as mock_async_client_cls:
        mock_async_client_cls.return_value.request = AsyncMock()
        def side_effect(**kwargs):
            if kwargs["method"] == "POST" and kwargs["url"] == "/users" and kwargs.get("json") and "email" in kwargs["json"]:
                return SAMPLE_RESPONSES["POST /users"]
            elif kwargs["method"] == "POST" and kwargs["url"] == "/users" and (not kwargs.get("json") or "email" not in kwargs["json"]):
                return SAMPLE_RESPONSES["POST /users (missing field)"]
            elif kwargs["method"] == "GET" and kwargs["url"].startswith("/users/"):
                 return SAMPLE_RESPONSES["GET /users/123"]
            raise ValueError(f"Unexpected request: {kwargs['method']} {kwargs['url']}")

        mock_async_client_cls.return_value.request.side_effect = side_effect

        mock_session = MagicMock()
        mock_test_suite = MagicMock()

        runner = ChainRunner(session=mock_session, test_suite=mock_test_suite)
        result = await runner.run_test_suite(SAMPLE_TEST_SUITE)

        assert result["status"] == "completed"
        assert result["success"] is True
        assert len(result["test_case_results"]) == len(SAMPLE_TEST_SUITE["test_cases"])
        assert result["test_case_results"][0]["status"] == "passed"
        assert result["test_case_results"][1]["status"] == "passed"
        assert "user_id" in result["test_case_results"][0]["step_results"][0]["extracted_values"]
        assert result["test_case_results"][0]["step_results"][0]["extracted_values"]["user_id"] == "123"

@pytest.mark.asyncio
async def test_run_test_suite_with_base_url():
    with patch("httpx.AsyncClient") as mock_async_client_cls:
        mock_client_instance = AsyncMock()

        def side_effect(method, url, **kwargs):
            print(f"REQ: {method} {url} | json={kwargs.get('json')}")
            if method == "POST" and url.endswith("/users") and kwargs.get("json", {}).get("email"):
                return httpx.Response(
                    status_code=201,
                    content=json.dumps({"id": "123"}).encode(),
                    headers={"Content-Type": "application/json"}
                )
            elif method == "POST" and url.endswith("/users"):
                return httpx.Response(
                    status_code=400,
                    content=json.dumps({"detail": "Missing required field: email"}).encode(),
                    headers={"Content-Type": "application/json"}
                )
            elif method == "GET" and "/users/" in url:
                return httpx.Response(
                    status_code=200,
                    content=json.dumps({"id": "123", "name": "Test User"}).encode(),
                    headers={"Content-Type": "application/json"}
                )
            raise Exception(f"Unexpected request: {method} {url}")

        mock_client_instance.request.side_effect = side_effect
        mock_async_client_cls.return_value = mock_client_instance
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_test_suite = MagicMock()
        test_base_url = "http://test.api.com"

        runner = ChainRunner(session=mock_session, test_suite=mock_test_suite, base_url=test_base_url)
        result = await runner.run_test_suite(SAMPLE_TEST_SUITE)

        assert result["status"] == "completed"
        assert result["success"] is True
        assert len(result["test_case_results"]) == 2
        assert result["test_case_results"][0]["status"] == "passed"
        assert result["test_case_results"][1]["status"] == "passed"
        assert "user_id" in result["test_case_results"][0]["step_results"][0]["extracted_values"]
        assert result["test_case_results"][0]["step_results"][0]["extracted_values"]["user_id"] == "123"

        mock_async_client_cls.assert_called_once_with(base_url=test_base_url, timeout=30.0)


@pytest.mark.asyncio
async def test_run_test_suites_function(session, test_project, monkeypatch):
    mock_chain_store = MagicMock()
    mock_chain_store.list_test_suites.return_value = [{"id": "test-suite-1"}]
    mock_chain_store.get_test_suite.return_value = SAMPLE_TEST_SUITE
    monkeypatch.setattr("app.services.chain_runner.ChainStore", lambda: mock_chain_store)
    
    with patch("httpx.AsyncClient") as mock_async_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = lambda **kwargs: SAMPLE_RESPONSES[f"{kwargs['method']} {kwargs['url']}"]
        mock_async_client_cls.return_value = mock_client_instance
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient") as mock_async_client_cls, \
             patch("app.services.chain_runner.Session") as mock_session_cls:

            mock_client_instance = AsyncMock()
            mock_client_instance.request.side_effect = lambda **kwargs: SAMPLE_RESPONSES[f"{kwargs['method']} {kwargs['url']}"]
            mock_async_client_cls.return_value = mock_client_instance
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value.__enter__.return_value = session
            mock_session_cls.return_value.__exit__.return_value = None

            monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
            mock_open = MagicMock()
            monkeypatch.setattr("builtins.open", mock_open)

            from app.models import TestSuite, TestRun

            test_suite = TestSuite(
                id="test-suite-1",
                project_id=test_project.project_id,
                name="Test TestSuite",
                target_method="POST",
                target_path="/users"
            )
            session.add(test_suite)
            session.commit()
            session.refresh(test_suite)
        
            result = await run_test_suites(test_project.project_id)

            session.refresh(test_project)

            assert result["status"] == "completed"
            assert "results" in result

            session.commit()

            runs = session.exec(select(TestRun).where(TestRun.project_id == test_project.id)).all()
            assert len(runs) > 0

def test_list_test_runs(session, test_project):
    from app.models import TestSuite, TestRun
    
    test_suite = TestSuite(
        id="test-suite-1",
        project_id=test_project.id,
        name="Test TestSuite",
        target_method="GET",
        target_path="/items"
    )
    session.add(test_suite)
    session.flush()
    
    test_run = TestRun(
        run_id=str(uuid.uuid4()),
        suite_id=test_suite.id,
        project_id=test_project.id,
        status="completed",
        start_time=datetime.now(timezone.utc)
    )
    session.add(test_run)
    session.commit()
    session.refresh(test_run)

    with patch("app.services.chain_runner.Session", return_value=session) as mock_session:
        test_runs = list_test_runs(test_project.project_id)
    
    assert len(test_runs) == 1
    assert test_runs[0]["run_id"] == test_run.run_id
    assert test_runs[0]["suite_id"] == "test-suite-1"
    assert test_runs[0]["status"] == "completed"

def test_get_test_run(session, test_project):
    from app.models.test import TestSuite, TestCase, TestStep, TestRun, TestCaseResult, StepResult
    
    test_suite = TestSuite(
        id="test-suite-1",
        project_id=test_project.id,
        name="Test TestSuite",
        target_method="POST",
        target_path="/users"
    )
    session.add(test_suite)
    session.flush()
    
    test_case = TestCase(
        id="test-case-1",
        suite_id=test_suite.id,
        name="Normal Case",
        description="Normal user creation",
        error_type=None
    )
    session.add(test_case)
    session.flush()
    
    test_step = TestStep(
        id="test-step-1",
        case_id=test_case.id,
        sequence=0,
        method="POST",
        path="/users"
    )
    session.add(test_step)
    session.flush()
    
    test_run = TestRun(
        run_id=str(uuid.uuid4()),
        suite_id=test_suite.id,
        project_id=test_project.id,
        status="completed",
        start_time=datetime.now(timezone.utc)
    )
    session.add(test_run)
    session.flush()
    
    test_case_result = TestCaseResult(
        test_run_id=test_run.id,
        case_id=test_case.id,
        status="passed"
    )
    session.add(test_case_result)
    session.flush()
    
    step_result = StepResult(
        test_case_result_id=test_case_result.id,
        step_id=test_step.id,
        sequence=0,
        status_code=201,
        passed=True,
        response_time=100.0,
        response_body_str=json.dumps({"id": "123"})
    )
    session.add(step_result)
    session.commit()
    with patch("app.services.chain_runner.Session", return_value=session):
        test_run_data = get_test_run(test_project.project_id, test_run.run_id)
    
    assert test_run_data is not None
    assert test_run_data["run_id"] == test_run.run_id
    assert test_run_data["suite_id"] == "test-suite-1"
    assert test_run_data["status"] == "completed"
    assert len(test_run_data["test_case_results"]) == 1
    assert test_run_data["test_case_results"][0]["id"] == test_case_result.id
    assert test_run_data["test_case_results"][0]["case_id"] == "test-case-1"
    assert test_run_data["test_case_results"][0]["status"] == "passed"
    assert len(test_run_data["test_case_results"][0]["step_results"]) == 1
    assert test_run_data["test_case_results"][0]["step_results"][0]["id"] == step_result.id
    assert test_run_data["test_case_results"][0]["step_results"][0]["status_code"] == 201
    assert test_run_data["test_case_results"][0]["step_results"][0]["passed"] is True
