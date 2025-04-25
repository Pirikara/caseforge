import pytest
from app.services.chain_runner import ChainRunner, run_chains, list_chain_runs, get_chain_run
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime, timezone
import httpx
from sqlmodel import select

# テスト用のサンプルチェーン
SAMPLE_CHAIN = {
    "name": "ユーザー作成と取得",
    "steps": [
        {
            "method": "POST",
            "path": "/users",
            "request": {
                "body": {"name": "Test User", "email": "test@example.com"}
            },
            "response": {
                "extract": {"user_id": "$.id"}
            }
        },
        {
            "method": "GET",
            "path": "/users/{user_id}",
            "request": {},
            "response": {}
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
    )
}

@pytest.mark.asyncio
async def test_execute_step():
    """ステップ実行のテスト"""
    # httpx.AsyncClientをモック
    mock_client = MagicMock()
    mock_client.request = AsyncMock()
    mock_client.request.return_value = SAMPLE_RESPONSES["POST /users"]
    
    # テスト実行
    runner = ChainRunner()
    step = SAMPLE_CHAIN["steps"][0]
    result = await runner._execute_step(mock_client, step, {})
    
    # 検証
    assert result["success"] is True
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
    # テスト実行
    runner = ChainRunner()
    response_body = {"id": "123", "name": "Test User"}
    extract_rules = {"user_id": "$.id", "user_name": "$.name"}
    
    extracted = runner._extract_values(response_body, extract_rules)
    
    # 検証
    assert extracted["user_id"] == "123"
    assert extracted["user_name"] == "Test User"

@pytest.mark.asyncio
async def test_replace_path_params():
    """パスパラメータ置換のテスト"""
    # テスト実行
    runner = ChainRunner()
    path = "/users/{user_id}/posts/{post_id}"
    values = {"user_id": "123", "post_id": "456"}
    
    result = runner._replace_path_params(path, values)
    
    # 検証
    assert result == "/users/123/posts/456"

@pytest.mark.asyncio
async def test_replace_values_in_body():
    """リクエストボディ内の値置換のテスト"""
    # テスト実行
    runner = ChainRunner()
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
async def test_run_chain():
    """チェーン実行のテスト"""
    # httpx.AsyncClientをモック
    mock_client = MagicMock()
    mock_client.request = AsyncMock()
    mock_client.request.side_effect = lambda **kwargs: SAMPLE_RESPONSES[f"{kwargs['method']} {kwargs['url']}"]
    
    # AsyncClientのコンテキストマネージャをモック
    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        # テスト実行
        runner = ChainRunner()
        result = await runner.run_chain(SAMPLE_CHAIN)
        
        # 検証
        assert result["status"] == "completed"
        assert result["success"] is True
        assert len(result["steps"]) == 2
        assert result["steps"][0]["success"] is True
        assert result["steps"][1]["success"] is True
        assert "user_id" in result["extracted_values"]
        assert result["extracted_values"]["user_id"] == "123"

@pytest.mark.asyncio
async def test_run_chains(session, test_project, monkeypatch):
    """チェーン実行関数のテスト"""
    # ChainStoreをモック
    mock_chain_store = MagicMock()
    mock_chain_store.get_chain.return_value = SAMPLE_CHAIN
    mock_chain_store.list_chains.return_value = [{"id": "test-chain-1"}]
    monkeypatch.setattr("app.services.chain_runner.ChainStore", lambda: mock_chain_store)
    
    # ChainRunnerをモック
    mock_runner = MagicMock()
    mock_runner.run_chain = AsyncMock(return_value={
        "status": "completed",
        "success": True,
        "steps": [
            {"success": True, "status_code": 201, "response_body": {"id": "123"}},
            {"success": True, "status_code": 200, "response_body": {"id": "123", "name": "Test User"}}
        ],
        "extracted_values": {"user_id": "123"}
    })
    monkeypatch.setattr("app.services.chain_runner.ChainRunner", lambda: mock_runner)
    
    # ファイル書き込みをモック
    monkeypatch.setattr("os.makedirs", lambda path, exist_ok: None)
    mock_open = MagicMock()
    monkeypatch.setattr("builtins.open", mock_open)
    
    # テスト用のチェーンを事前に作成
    from app.models import TestChain, ChainRun
    
    # テスト用のチェーンを作成
    chain = TestChain(
        chain_id="test-chain-1",
        project_id=test_project.id,
        name="Test Chain"
    )
    session.add(chain)
    session.commit()
    session.refresh(chain)
    
    # テスト実行
    result = await run_chains(test_project.project_id)
    
    # 検証
    assert result["status"] == "completed"
    assert "results" in result
    
    # ChainRunが作成されたことを確認
    runs = session.exec(select(ChainRun).where(ChainRun.project_id == test_project.id)).all()
    assert len(runs) > 0

def test_list_chain_runs(session, test_project):
    """チェーン実行履歴取得のテスト"""
    # テスト用のChainRunを作成
    from app.models import TestChain, ChainRun
    
    # テスト用のチェーンを作成
    chain = TestChain(
        chain_id="test-chain-1",
        project_id=test_project.id,
        name="Test Chain"
    )
    session.add(chain)
    session.flush()
    
    # テスト用のチェーン実行を作成
    run = ChainRun(
        run_id="test-run-1",
        chain_id=chain.id,
        project_id=test_project.id,
        status="completed",
        start_time=datetime.now(timezone.utc)
    )
    session.add(run)
    session.commit()
    
    # テスト実行
    runs = list_chain_runs(test_project.project_id)
    
    # 検証
    assert len(runs) == 1
    assert runs[0]["run_id"] == "test-run-1"
    assert runs[0]["chain_id"] == "test-chain-1"
    assert runs[0]["status"] == "completed"

def test_get_chain_run(session, test_project):
    """特定のチェーン実行取得のテスト"""
    # テスト用のChainRunとStepResultを作成
    from app.models import TestChain, TestChainStep, ChainRun, StepResult
    
    # テスト用のチェーンを作成
    chain = TestChain(
        chain_id="test-chain-1",
        project_id=test_project.id,
        name="Test Chain"
    )
    session.add(chain)
    session.flush()
    
    # テスト用のステップを作成
    step = TestChainStep(
        chain_id=chain.id,
        sequence=0,
        method="POST",
        path="/users"
    )
    session.add(step)
    session.flush()
    
    # テスト用のチェーン実行を作成
    run = ChainRun(
        run_id="test-run-1",
        chain_id=chain.id,
        project_id=test_project.id,
        status="completed",
        start_time=datetime.now(timezone.utc)
    )
    session.add(run)
    session.flush()
    
    # テスト用のステップ結果を作成
    step_result = StepResult(
        chain_run_id=run.id,
        step_id=step.id,
        sequence=0,
        status_code=201,
        passed=True,
        response_time=100.0,
        response_body_str=json.dumps({"id": "123"})
    )
    session.add(step_result)
    session.commit()
    
    # テスト実行
    run_data = get_chain_run(test_project.project_id, "test-run-1")
    
    # 検証
    assert run_data is not None
    assert run_data["run_id"] == "test-run-1"
    assert run_data["chain_id"] == "test-chain-1"
    assert run_data["status"] == "completed"
    assert len(run_data["steps"]) == 1
    assert run_data["steps"][0]["status_code"] == 201
    assert run_data["steps"][0]["passed"] is True