import pytest
from app.services.chain_runner import ChainRunner, run_test_suites, list_test_runs, get_test_run
from unittest.mock import patch, MagicMock, AsyncMock
import json
import uuid
from datetime import datetime, timezone
import httpx
from sqlmodel import select

# テスト用のサンプルテストスイート
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

# テスト用のレスポンス
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
    # httpx.AsyncClientをモック
    mock_client = MagicMock()
    mock_client.request = AsyncMock()
    mock_client.request.return_value = SAMPLE_RESPONSES["POST /users"]
    
    # ダミーのsessionとchainを作成
    mock_session = MagicMock()
    mock_chain = MagicMock()

    # テスト実行
    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    step = SAMPLE_TEST_SUITE["test_cases"][0]["test_steps"][0]
    result = await runner._execute_step(mock_client, step, {})
    
    # 検証
    assert result["passed"] is True # success を passed に変更
    assert result["status_code"] == 201
    assert "response_body" in result
    assert result["response_body"]["id"] == "123"
    
    # httpx.AsyncClient.requestが正しく呼ばれたことを確認
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
    # ダミーのsessionとchainを作成
    mock_session = MagicMock()
    mock_chain = MagicMock()

    # テスト実行
    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    response_body = {"id": "123", "name": "Test User", "email": "test@example.com"} # レスポンスボディを修正
    extract_rules = {"user_id": "$.id", "user_name": "$.name"}
    
    extracted = runner._extract_values(response_body, extract_rules)
    
    # 検証
    assert extracted["user_id"] == "123"
    assert extracted["user_name"] == "Test User"

@pytest.mark.asyncio
async def test_replace_path_params():
    """パスパラメータ置換のテスト"""
    # ダミーのsessionとchainを作成
    mock_session = MagicMock()
    mock_chain = MagicMock()

    # テスト実行
    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    path = "/users/{user_id}/posts/{post_id}"
    values = {"user_id": "123", "post_id": "456"}
    
    result = runner._replace_path_params(path, values)
    
    # 検証
    assert result == "/users/123/posts/456"

@pytest.mark.asyncio
async def test_replace_values_in_body():
    """リクエストボディ内の値置換のテスト"""
    # ダミーのsessionとchainを作成
    mock_session = MagicMock()
    mock_chain = MagicMock()

    # テスト実行
    runner = ChainRunner(session=mock_session, test_suite=mock_chain)
    body = {
        "user_id": "${user_id}",
        "data": {
            "name": "Test",
            "reference": "${reference_id}"
        },
        "items": ["${item1}", "${item2}"]
    }
    values = {"user_id": "123", "reference_id": "456", "item1": "item1", "item2": "item2"}
    
    result = runner._replace_values_in_body(body, values)
    
    # 検証
    assert result["user_id"] == "123"
    assert result["data"]["reference"] == "456"
    assert result["items"][0] == "item1"
    assert result["items"][1] == "item2"

@pytest.mark.asyncio
async def test_run_test_suite():
    """テストスイート実行のテスト"""
    # httpx.AsyncClientクラスをモック
    with patch("httpx.AsyncClient") as mock_async_client_cls:
        # インスタンスのrequestメソッドをAsyncMockに設定
        mock_async_client_cls.return_value.request = AsyncMock()
        def side_effect(**kwargs):
            if kwargs["method"] == "POST" and kwargs["url"] == "/users" and kwargs.get("json") and "email" in kwargs["json"]:
                return SAMPLE_RESPONSES["POST /users"]
            elif kwargs["method"] == "POST" and kwargs["url"] == "/users" and (not kwargs.get("json") or "email" not in kwargs["json"]):
                return SAMPLE_RESPONSES["POST /users (missing field)"]
            elif kwargs["method"] == "GET" and kwargs["url"].startswith("/users/"):
                 return SAMPLE_RESPONSES["GET /users/123"]
            # 他のケースが必要であればここに追加
            raise ValueError(f"Unexpected request: {kwargs['method']} {kwargs['url']}")

        mock_async_client_cls.return_value.request.side_effect = side_effect

        # ダミーのsessionとtest_suiteを作成
        mock_session = MagicMock()
        mock_test_suite = MagicMock()

        # テスト実行
        runner = ChainRunner(session=mock_session, test_suite=mock_test_suite)
        result = await runner.run_test_suite(SAMPLE_TEST_SUITE)

        # 検証
        assert result["status"] == "completed"
        assert result["success"] is True
        assert len(result["test_case_results"]) == len(SAMPLE_TEST_SUITE["test_cases"])
        assert result["test_case_results"][0]["status"] == "passed"
        assert result["test_case_results"][1]["status"] == "passed" # AssertionError を修正
        assert "user_id" in result["test_case_results"][0]["step_results"][0]["extracted_values"] # ステップレベルの extracted_values にアクセス
        assert result["test_case_results"][0]["step_results"][0]["extracted_values"]["user_id"] == "123" # ステップレベルの extracted_values にアクセス

@pytest.mark.asyncio
async def test_run_test_suite_with_base_url():
    with patch("httpx.AsyncClient") as mock_async_client_cls:
        # AsyncClientのインスタンスとして使用するモックを作成
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

        # モックインスタンスのrequestメソッドにside_effectを設定
        mock_client_instance.request.side_effect = side_effect

        # patchしたクラスのreturn_valueにモックインスタンスを設定
        mock_async_client_cls.return_value = mock_client_instance

        # モックインスタンスを非同期コンテキストマネージャーとして設定
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        # ダミーの session と test_suite を用意
        mock_session = MagicMock()
        mock_test_suite = MagicMock()
        test_base_url = "http://test.api.com"

        # テストスイートの実行
        runner = ChainRunner(session=mock_session, test_suite=mock_test_suite, base_url=test_base_url)
        result = await runner.run_test_suite(SAMPLE_TEST_SUITE)

        # 検証
        assert result["status"] == "completed"
        assert result["success"] is True
        assert len(result["test_case_results"]) == 2
        assert result["test_case_results"][0]["status"] == "passed"
        assert result["test_case_results"][1]["status"] == "passed"
        assert "user_id" in result["test_case_results"][0]["step_results"][0]["extracted_values"]
        assert result["test_case_results"][0]["step_results"][0]["extracted_values"]["user_id"] == "123"

        # base_url を渡して httpx.AsyncClient が生成されたかを確認
        mock_async_client_cls.assert_called_once_with(base_url=test_base_url, timeout=30.0)


@pytest.mark.asyncio
async def test_run_test_suites_function(session, test_project, monkeypatch):
    # ChainStoreをモック
    mock_chain_store = MagicMock()
    mock_chain_store.list_test_suites.return_value = [{"id": "test-suite-1"}]
    mock_chain_store.get_test_suite.return_value = SAMPLE_TEST_SUITE
    monkeypatch.setattr("app.services.chain_runner.ChainStore", lambda: mock_chain_store)
    
    # httpx.AsyncClientをモック
    # httpx.AsyncClientクラスをモック
    with patch("httpx.AsyncClient") as mock_async_client_cls:
        # AsyncClientのインスタンスをモック
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = lambda **kwargs: SAMPLE_RESPONSES[f"{kwargs['method']} {kwargs['url']}"]

        # モッククラスのreturn_value (インスタンス) が mock_client_instance を返すように設定
        mock_async_client_cls.return_value = mock_client_instance

        # AsyncClientのコンテキストマネージャをモック
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient") as mock_async_client_cls, \
             patch("app.services.chain_runner.Session") as mock_session_cls: # Session をモック

            # AsyncClientのインスタンスをモック
            mock_client_instance = AsyncMock()
            mock_client_instance.request.side_effect = lambda **kwargs: SAMPLE_RESPONSES[f"{kwargs['method']} {kwargs['url']}"]

            # モッククラスのreturn_value (インスタンス) が mock_client_instance を返すように設定
            mock_async_client_cls.return_value = mock_client_instance

            # AsyncClientのコンテキストマネージャをモック
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)

            mock_session_cls.return_value.__enter__.return_value = session # モックされたSessionがテストセッションを返すように設定
            mock_session_cls.return_value.__exit__.return_value = None # __exit__ もモック

            # ファイル書き込みをモック
            monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
            mock_open = MagicMock()
            monkeypatch.setattr("builtins.open", mock_open)

            # テスト用のテストスイートを事前に作成
            from app.models import TestSuite, TestRun

            # テスト用のテストスイートを作成
            test_suite = TestSuite(
                id="test-suite-1",
                project_id=test_project.project_id, # project_id を test_project.project_id に変更
                name="Test TestSuite",
                target_method="POST",
                target_path="/users"
            )
            session.add(test_suite)
            session.commit()
            session.refresh(test_suite)
            print(f"test_run_test_suites_function: TestSuite saved: {test_suite}") # デバッグログ追加
        
            # テスト実行
            print(f"test_run_test_suites_function: Calling run_test_suites with project_id: {test_project.project_id}") # デバッグログ追加
            result = await run_test_suites(test_project.project_id)
            print(f"test_run_test_suites_function: run_test_suites result: {result}") # デバッグログ追加

            # run_test_suites内でコミットされたTestRunがテストセッションから見えるか確認
            session.refresh(test_project) # プロジェクトをリフレッシュして関連するTestRunを取得可能にする
            print(f"test_run_test_suites_function: Session refreshed.") # デバッグログ追加

            # 検証
            assert result["status"] == "completed"
            assert "results" in result

            # TestRunが作成されたことを確認
            # run_test_suites内でコミットされたTestRunがテストセッションから見えるように、テストセッションをコミット
            session.commit()
            print(f"test_run_test_suites_function: Test session committed.") # デバッグログ追加

            runs = session.exec(select(TestRun).where(TestRun.project_id == test_project.id)).all()
            print(f"test_run_test_suites_function: Retrieved TestRuns: {runs}") # デバッグログ追加
            assert len(runs) > 0

def test_list_test_runs(session, test_project):
    # テスト用のTestRunを作成
    from app.models import TestSuite, TestRun
    
    # テスト用のテストスイートを作成
    test_suite = TestSuite(
        id="test-suite-1",
        project_id=test_project.id,
        name="Test TestSuite",
        target_method="GET",
        target_path="/items"
    )
    session.add(test_suite)
    session.flush()
    
    # テスト用のテスト実行を作成
    test_run = TestRun(
        run_id=str(uuid.uuid4()), # run_id を明示的に指定
        suite_id=test_suite.id,
        project_id=test_project.id, # project_id を test_project.project_id に変更
        status="completed",
        start_time=datetime.now(timezone.utc)
    )
    session.add(test_run)
    session.commit()
    session.refresh(test_run)

    # テスト実行
    with patch("app.services.chain_runner.Session", return_value=session) as mock_session:
        test_runs = list_test_runs(test_project.project_id)
    
    # 検証
    assert len(test_runs) == 1
    assert test_runs[0]["run_id"] == test_run.run_id # 自動生成された run_id を使用
    assert test_runs[0]["suite_id"] == "test-suite-1"
    assert test_runs[0]["status"] == "completed"

def test_get_test_run(session, test_project):
    from app.models.chain import TestSuite, TestStep
    from app.models.test_models import TestCase, TestCaseResult, StepResult, TestRun
    
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