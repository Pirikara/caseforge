"""
テスト実行クラスの使用例

このモジュールは、テスト実行クラスの使用方法を示すサンプルコードを提供します。
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlmodel import Session, select

from app.config import settings
from app.models import engine, Service, TestSuite
from app.services.test.test_runner import (
    TestRunnerFactory, APITestRunner, ChainTestRunner,
    TestStatus, StepTestResult, CaseTestResult, SuiteTestResult
)
from app.services.test.variable_manager import VariableManager, VariableScope


async def run_simple_api_test():
    """単純なAPIテストの実行例"""
    print("\n=== 単純なAPIテストの実行例 ===")
    
    # APIテスト実行クラスのインスタンスを作成
    runner = APITestRunner(
        base_url="https://httpbin.org",
        timeout=10.0
    )
    
    # テストデータの準備
    test_data = {
        "name": "HTTPBin GET Test",
        "method": "GET",
        "path": "/get",
        "request": {
            "headers": {
                "X-Test-Header": "test-value"
            },
            "params": {
                "param1": "value1",
                "param2": "value2"
            }
        },
        "expected_status": 200,
        "extract_rules": {
            "url": "$.url",
            "headers": "$.headers"
        }
    }
    
    # テストの実行
    result = await runner.run(test_data)
    
    # 結果の表示
    print(f"テスト名: {result.name}")
    print(f"ステータス: {result.status}")
    print(f"実行時間: {result.duration_ms:.2f}ms")
    print(f"HTTPステータスコード: {result.status_code}")
    print(f"成功: {result.passed}")
    
    if result.error_message:
        print(f"エラーメッセージ: {result.error_message}")
    
    print("抽出された値:")
    for key, value in result.extracted_values.items():
        print(f"  {key}: {value}")
    
    return result


async def run_api_test_with_variables():
    """変数を使用したAPIテストの実行例"""
    print("\n=== 変数を使用したAPIテストの実行例 ===")
    
    # APIテスト実行クラスのインスタンスを作成
    runner = APITestRunner(
        base_url="https://httpbin.org",
        timeout=10.0
    )
    
    # 変数の設定
    runner.variable_manager.set_variable("test_path", "post", VariableScope.GLOBAL)
    runner.variable_manager.set_variable("content_type", "application/json", VariableScope.GLOBAL)
    
    # テストデータの準備
    test_data = {
        "name": "HTTPBin POST Test with Variables",
        "method": "POST",
        "path": "/${test_path}",
        "request": {
            "headers": {
                "Content-Type": "${content_type}"
            }
        },
        "request_body": {
            "name": "Test User",
            "email": "test@example.com"
        },
        "expected_status": 200,
        "extract_rules": {
            "json_data": "$.json"
        }
    }
    
    # テストの実行
    result = await runner.run(test_data)
    
    # 結果の表示
    print(f"テスト名: {result.name}")
    print(f"ステータス: {result.status}")
    print(f"実行時間: {result.duration_ms:.2f}ms")
    print(f"HTTPステータスコード: {result.status_code}")
    print(f"成功: {result.passed}")
    
    if result.error_message:
        print(f"エラーメッセージ: {result.error_message}")
    
    print("抽出された値:")
    for key, value in result.extracted_values.items():
        print(f"  {key}: {value}")
    
    return result


async def run_test_chain():
    """テストチェーンの実行例"""
    print("\n=== テストチェーンの実行例 ===")
    
    # テストスイートデータの準備
    test_suite_data = {
        "id": "test-suite-1",
        "name": "HTTPBin Test Suite",
        "test_cases": [
            {
                "case_id": "case-1",
                "name": "GET Request Test",
                "test_steps": [
                    {
                        "sequence": 1,
                        "name": "Get Request Step",
                        "method": "GET",
                        "path": "/get",
                        "request": {
                            "params": {
                                "param1": "value1"
                            }
                        },
                        "expected_status": 200,
                        "extract_rules": {
                            "url": "$.url"
                        }
                    }
                ]
            },
            {
                "case_id": "case-2",
                "name": "POST Request Test",
                "test_steps": [
                    {
                        "sequence": 1,
                        "name": "Post Request Step",
                        "method": "POST",
                        "path": "/post",
                        "request": {
                            "headers": {
                                "Content-Type": "application/json"
                            }
                        },
                        "request_body": {
                            "name": "Test User",
                            "email": "test@example.com"
                        },
                        "expected_status": 200,
                        "extract_rules": {
                            "json_data": "$.json"
                        }
                    },
                    {
                        "sequence": 2,
                        "name": "Get with Extracted Data",
                        "method": "GET",
                        "path": "/get",
                        "request": {
                            "params": {
                                "email": "${json_data.email}"
                            }
                        },
                        "expected_status": 200
                    }
                ]
            }
        ]
    }
    
    # データベースセッションの作成
    with Session(engine) as session:
        # テスト用のサービスとテストスイートを作成
        service = Service(
            service_id="test-service",
            name="Test Service",
            base_url="https://httpbin.org"
        )
        session.add(service)
        
        test_suite = TestSuite(
            id="test-suite-1",
            service_id=service.id,
            name="HTTPBin Test Suite"
        )
        session.add(test_suite)
        session.commit()
        session.refresh(service)
        session.refresh(test_suite)
        
        # テストチェーン実行クラスのインスタンスを作成
        runner = ChainTestRunner(
            session=session,
            test_suite=test_suite,
            base_url="https://httpbin.org",
            timeout=10.0
        )
        
        # テストの実行
        result = await runner.run(test_suite_data)
        
        # 結果の表示
        print(f"テストスイート名: {result.name}")
        print(f"ステータス: {result.status}")
        print(f"実行時間: {result.duration_ms:.2f}ms")
        print(f"成功: {result.success}")
        
        if result.error_message:
            print(f"エラーメッセージ: {result.error_message}")
        
        print(f"テストケース数: {len(result.test_case_results)}")
        
        for i, case_result in enumerate(result.test_case_results):
            print(f"\nテストケース {i+1}: {case_result.name}")
            print(f"  ステータス: {case_result.status}")
            print(f"  実行時間: {case_result.duration_ms:.2f}ms")
            
            if case_result.error_message:
                print(f"  エラーメッセージ: {case_result.error_message}")
            
            print(f"  ステップ数: {len(case_result.step_results)}")
            
            for j, step_result in enumerate(case_result.step_results):
                print(f"    ステップ {j+1}: {step_result.name}")
                print(f"      ステータス: {step_result.status}")
                print(f"      HTTPステータスコード: {step_result.status_code}")
                print(f"      成功: {step_result.passed}")
                print(f"      実行時間: {step_result.response_time:.2f}ms")
                
                if step_result.error_message:
                    print(f"      エラーメッセージ: {step_result.error_message}")
        
        return result


async def run_test_with_factory():
    """ファクトリークラスを使用したテスト実行例"""
    print("\n=== ファクトリークラスを使用したテスト実行例 ===")
    
    # データベースセッションの作成
    with Session(engine) as session:
        # テスト用のサービスとテストスイートを作成
        service = Service(
            service_id="test-service-2",
            name="Test Service 2",
            base_url="https://httpbin.org"
        )
        session.add(service)
        
        test_suite = TestSuite(
            id="test-suite-2",
            service_id=service.id,
            name="HTTPBin Test Suite 2"
        )
        session.add(test_suite)
        session.commit()
        session.refresh(service)
        session.refresh(test_suite)
        
        # APIテスト実行クラスのインスタンスを作成
        api_runner = TestRunnerFactory.create_runner(
            runner_type="api",
            base_url="https://httpbin.org"
        )
        
        # テストチェーン実行クラスのインスタンスを作成
        chain_runner = TestRunnerFactory.create_runner(
            runner_type="chain",
            session=session,
            test_suite=test_suite,
            base_url="https://httpbin.org"
        )
        
        print("APIテスト実行クラスのインスタンス作成成功")
        print("テストチェーン実行クラスのインスタンス作成成功")
        
        # サービスのテストスイートを実行
        result = await TestRunnerFactory.run_test_suite(
            service_id=service.service_id,
            suite_id=test_suite.id,
            session=session,
            base_url="https://httpbin.org"
        )
        
        print(f"実行結果: {result['status']}")
        print(f"メッセージ: {result['message']}")
        
        return result


async def run_with_hooks():
    """フックを使用したテスト実行例"""
    print("\n=== フックを使用したテスト実行例 ===")
    
    # APIテスト実行クラスのインスタンスを作成
    runner = APITestRunner(
        base_url="https://httpbin.org",
        timeout=10.0
    )
    
    # セットアップフックの追加
    runner.add_setup_hook(lambda: print("セットアップフック実行"))
    
    # ティアダウンフックの追加
    runner.add_teardown_hook(lambda: print("ティアダウンフック実行"))
    
    # テスト実行前フックの追加
    runner.add_before_test_hook(lambda test_data: print(f"テスト実行前フック実行: {test_data['name']}"))
    
    # テスト実行後フックの追加
    runner.add_after_test_hook(lambda test_data, result: print(f"テスト実行後フック実行: {result.status}"))
    
    # テストデータの準備
    test_data = {
        "name": "Hook Test",
        "method": "GET",
        "path": "/get",
        "expected_status": 200
    }
    
    # テストの実行
    result = await runner.run(test_data)
    
    # 結果の表示
    print(f"テスト名: {result.name}")
    print(f"ステータス: {result.status}")
    print(f"成功: {result.passed}")
    
    return result


async def run_with_timeout_and_retry():
    """タイムアウトとリトライを使用したテスト実行例"""
    print("\n=== タイムアウトとリトライを使用したテスト実行例 ===")
    
    # APIテスト実行クラスのインスタンスを作成
    runner = APITestRunner(
        base_url="https://httpbin.org",
        timeout=2.0  # 短いタイムアウトを設定
    )
    
    # テストデータの準備（遅延レスポンスを要求）
    test_data = {
        "name": "Timeout and Retry Test",
        "method": "GET",
        "path": "/delay/1",  # 1秒の遅延
        "expected_status": 200
    }
    
    # テストの実行
    try:
        result = await runner.run(test_data)
        
        # 結果の表示
        print(f"テスト名: {result.name}")
        print(f"ステータス: {result.status}")
        print(f"実行時間: {result.duration_ms:.2f}ms")
        print(f"HTTPステータスコード: {result.status_code}")
        print(f"成功: {result.passed}")
        
        return result
    except Exception as e:
        print(f"エラー発生: {e}")
        return None


async def main():
    """メイン関数"""
    print("=== テスト実行クラスの使用例 ===")
    
    # 単純なAPIテストの実行
    await run_simple_api_test()
    
    # 変数を使用したAPIテストの実行
    await run_api_test_with_variables()
    
    # テストチェーンの実行
    await run_test_chain()
    
    # ファクトリークラスを使用したテスト実行
    await run_test_with_factory()
    
    # フックを使用したテスト実行
    await run_with_hooks()
    
    # タイムアウトとリトライを使用したテスト実行
    await run_with_timeout_and_retry()


if __name__ == "__main__":
    asyncio.run(main())
