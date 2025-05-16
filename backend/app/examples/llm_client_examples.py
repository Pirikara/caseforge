"""
LLMクライアントの使用例

このモジュールでは、LLMクライアントの基本的な使い方を示します。
同期処理と非同期処理の両方の例を含みます。
"""

import asyncio
import json
import time
from typing import Dict, Any, List

from app.services.llm.client import (
    LLMClientFactory,
    LLMProviderType,
    Message,
    MessageRole,
    LLMException,
    LLMResponseFormatException
)
from app.services.llm.prompts import get_prompt_template, register_prompt_template
from app.logging_config import logger


def basic_llm_call_example():
    """基本的なLLM呼び出しの例"""
    print("\n=== 基本的なLLM呼び出しの例 ===")
    
    # デフォルト設定でLLMクライアントを作成
    llm_client = LLMClientFactory.create_default()
    
    # メッセージを作成
    messages = [
        Message(MessageRole.SYSTEM, "あなたは役立つAIアシスタントです。"),
        Message(MessageRole.USER, "こんにちは、自己紹介をお願いします。")
    ]
    
    try:
        # LLMを呼び出す
        start_time = time.time()
        response = llm_client.call(messages)
        elapsed_time = time.time() - start_time
        
        print(f"応答: {response}")
        print(f"処理時間: {elapsed_time:.2f}秒")
    
    except LLMException as e:
        print(f"エラー: {e}")
        if hasattr(e, "details") and e.details:
            print(f"詳細: {e.details}")


async def async_llm_call_example():
    """非同期LLM呼び出しの例"""
    print("\n=== 非同期LLM呼び出しの例 ===")
    
    # OpenAIクライアントを作成
    llm_client = LLMClientFactory.create(
        provider_type=LLMProviderType.OPENAI,
        temperature=0.7
    )
    
    # メッセージを作成
    messages = [
        Message(MessageRole.SYSTEM, "あなたは役立つAIアシスタントです。"),
        Message(MessageRole.USER, "Pythonで簡単な「Hello, World!」プログラムを書いてください。")
    ]
    
    try:
        # LLMを非同期で呼び出す
        start_time = time.time()
        response = await llm_client.acall(messages)
        elapsed_time = time.time() - start_time
        
        print(f"応答: {response}")
        print(f"処理時間: {elapsed_time:.2f}秒")
    
    except LLMException as e:
        print(f"エラー: {e}")
        if hasattr(e, "details") and e.details:
            print(f"詳細: {e.details}")


def prompt_template_example():
    """プロンプトテンプレートを使用したLLM呼び出しの例"""
    print("\n=== プロンプトテンプレートを使用したLLM呼び出しの例 ===")
    
    # カスタムプロンプトテンプレートを登録
    register_prompt_template(
        name="simple_qa",
        template="""以下の質問に対して、簡潔に回答してください。

質問: {question}

回答:""",
        metadata={"description": "簡単な質問応答用のプロンプト"}
    )
    
    # LLMクライアントを作成
    llm_client = LLMClientFactory.create_default()
    
    try:
        # プロンプトテンプレートを取得
        prompt_template = get_prompt_template("simple_qa")
        
        # テンプレートを使用してLLMを呼び出す
        response = llm_client.call_with_prompt(
            prompt_template.template,
            question="Pythonとは何ですか？"
        )
        
        print(f"応答: {response}")
    
    except (KeyError, LLMException) as e:
        print(f"エラー: {e}")


def json_response_example():
    """JSONレスポンスを取得する例"""
    print("\n=== JSONレスポンスを取得する例 ===")
    
    # LLMクライアントを作成
    llm_client = LLMClientFactory.create_default()
    
    # メッセージを作成
    messages = [
        Message(MessageRole.SYSTEM, "あなたはJSON形式でのみ応答するAPIです。"),
        Message(MessageRole.USER, """以下の形式でJSONを返してください:
{
  "name": "あなたの名前",
  "skills": ["スキル1", "スキル2", "スキル3"],
  "experience": {
    "years": 数値,
    "level": "初級" または "中級" または "上級"
  }
}""")
    ]
    
    try:
        # LLMを呼び出し、JSONレスポンスを取得
        response_json = llm_client.call_with_json_response(messages)
        
        print(f"応答JSON: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
        
        # JSONの内容にアクセス
        name = response_json.get("name", "不明")
        skills = response_json.get("skills", [])
        experience = response_json.get("experience", {})
        
        print(f"名前: {name}")
        print(f"スキル: {', '.join(skills)}")
        print(f"経験年数: {experience.get('years')}年")
        print(f"レベル: {experience.get('level')}")
    
    except LLMResponseFormatException as e:
        print(f"JSONパースエラー: {e}")
        if hasattr(e, "details") and e.details:
            print(f"生のレスポンス: {e.details.get('response', '')[:100]}...")
    
    except LLMException as e:
        print(f"LLMエラー: {e}")


def different_providers_example():
    """異なるプロバイダーの使用例"""
    print("\n=== 異なるプロバイダーの使用例 ===")
    
    # OpenAIクライアント
    openai_client = LLMClientFactory.create(
        provider_type=LLMProviderType.OPENAI,
        model_name="gpt-3.5-turbo"
    )
    
    # ローカルモデルクライアント
    local_client = LLMClientFactory.create(
        provider_type=LLMProviderType.LOCAL,
        model_name="Hermes-3-Llama-3.1-8B",
        api_base="http://localhost:1234/v1"
    )
    
    # 設定からクライアントを作成
    config_client = LLMClientFactory.create_from_config({
        "provider": "openai",
        "model_name": "gpt-4",
        "temperature": 0.5,
        "max_tokens": 1000
    })
    
    # メッセージを作成
    messages = [
        Message(MessageRole.USER, "こんにちは、簡単な自己紹介をお願いします。")
    ]
    
    # 各クライアントで呼び出し（実際の呼び出しはコメントアウト）
    clients = {
        "OpenAI": openai_client,
        "ローカルモデル": local_client,
        "設定から作成": config_client
    }
    
    for name, client in clients.items():
        print(f"\n--- {name} クライアント ---")
        print(f"モデル名: {client.model_name}")
        print(f"温度: {client.temperature}")
        print(f"最大トークン数: {client.max_tokens}")
        
        # 実際の呼び出しはコメントアウト（デモのため）
        # try:
        #     response = client.call(messages)
        #     print(f"応答: {response}")
        # except LLMException as e:
        #     print(f"エラー: {e}")


def error_handling_example():
    """エラーハンドリングの例"""
    print("\n=== エラーハンドリングの例 ===")
    
    # 存在しないAPIベースを指定してクライアントを作成
    invalid_client = LLMClientFactory.create(
        provider_type=LLMProviderType.OPENAI,
        api_base="http://invalid-api-base.example.com"
    )
    
    messages = [
        Message(MessageRole.USER, "こんにちは")
    ]
    
    try:
        # タイムアウトするはず
        response = invalid_client.call(messages)
        print(f"応答: {response}")  # ここには到達しないはず
    
    except LLMException as e:
        print(f"予期されたエラー: {e}")
        if hasattr(e, "details") and e.details:
            print(f"エラー詳細: {e.details}")


async def main_async():
    """非同期メイン関数"""
    await async_llm_call_example()


def main():
    """メイン関数"""
    print("LLMクライアント使用例の実行を開始します...")
    
    # 基本的な例
    basic_llm_call_example()
    
    # 非同期の例
    asyncio.run(main_async())
    
    # プロンプトテンプレートの例
    prompt_template_example()
    
    # JSONレスポンスの例
    json_response_example()
    
    # 異なるプロバイダーの例
    different_providers_example()
    
    # エラーハンドリングの例
    error_handling_example()
    
    print("\nLLMクライアント使用例の実行が完了しました。")


if __name__ == "__main__":
    main()