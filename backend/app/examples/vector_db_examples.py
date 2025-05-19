"""
ベクトルDBマネージャーの使用例

このモジュールは、ベクトルDBマネージャーの使用方法を示すサンプルコードを提供します。
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import json

from langchain_core.documents import Document

from app.logging_config import logger
from app.services.vector_db.manager import (
    VectorDBManagerFactory,
    VectorDBManager,
    VectorDBException
)
from app.services.vector_db.embeddings import (
    EmbeddingModelFactory,
    EmbeddingModel,
    EmbeddingException
)


def create_sample_documents() -> List[Document]:
    """サンプルドキュメントを作成する"""
    return [
        Document(
            page_content="FastAPIは、Pythonで高速なAPIを構築するためのモダンなフレームワークです。",
            metadata={"source": "tech_docs", "category": "web_framework", "id": "1"}
        ),
        Document(
            page_content="Pythonは、読みやすく書きやすい、汎用プログラミング言語です。",
            metadata={"source": "tech_docs", "category": "programming_language", "id": "2"}
        ),
        Document(
            page_content="LangChainは、LLMを使用したアプリケーションを構築するためのフレームワークです。",
            metadata={"source": "tech_docs", "category": "llm_framework", "id": "3"}
        ),
        Document(
            page_content="FAISSは、Facebookが開発した効率的な類似度検索ライブラリです。",
            metadata={"source": "tech_docs", "category": "vector_db", "id": "4"}
        ),
        Document(
            page_content="ChromaDBは、AIのための埋め込みデータベースです。",
            metadata={"source": "tech_docs", "category": "vector_db", "id": "5"}
        )
    ]


def example_faiss_basic_usage():
    """FAISSベクトルDBマネージャーの基本的な使用例"""
    try:
        logger.info("=== FAISSベクトルDBマネージャーの基本的な使用例 ===")
        
        # 一時的な永続化ディレクトリを作成
        persist_dir = "/tmp/faiss_example"
        os.makedirs(persist_dir, exist_ok=True)
        
        # FAISSベクトルDBマネージャーを作成
        manager = VectorDBManagerFactory.create(
            db_type="faiss",
            persist_directory=persist_dir
        )
        
        # サンプルドキュメントを作成
        documents = create_sample_documents()
        
        # ドキュメントを追加
        manager.add_documents(documents)
        logger.info(f"{len(documents)}個のドキュメントを追加しました")
        
        # 類似度検索を実行
        query = "Pythonプログラミング言語について教えてください"
        results = manager.similarity_search(query, k=2)
        
        logger.info(f"クエリ: {query}")
        logger.info(f"検索結果: {len(results)}件")
        for i, doc in enumerate(results):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        # スコア付き類似度検索を実行
        results_with_score = manager.similarity_search_with_score(query, k=2)
        
        logger.info(f"スコア付き検索結果: {len(results_with_score)}件")
        for i, (doc, score) in enumerate(results_with_score):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"スコア: {score}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        logger.info("=== 例の終了 ===")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)


async def example_faiss_async_usage():
    """FAISSベクトルDBマネージャーの非同期使用例"""
    try:
        logger.info("=== FAISSベクトルDBマネージャーの非同期使用例 ===")
        
        # 一時的な永続化ディレクトリを作成
        persist_dir = "/tmp/faiss_async_example"
        os.makedirs(persist_dir, exist_ok=True)
        
        # FAISSベクトルDBマネージャーを作成
        manager = VectorDBManagerFactory.create(
            db_type="faiss",
            persist_directory=persist_dir
        )
        
        # サンプルドキュメントを作成
        documents = create_sample_documents()
        
        # ドキュメントを非同期で追加
        await manager.aadd_documents(documents)
        logger.info(f"{len(documents)}個のドキュメントを非同期で追加しました")
        
        # 類似度検索を非同期で実行
        query = "ベクトルデータベースについて教えてください"
        results = await manager.asimilarity_search(query, k=2)
        
        logger.info(f"クエリ: {query}")
        logger.info(f"非同期検索結果: {len(results)}件")
        for i, doc in enumerate(results):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        # スコア付き類似度検索を非同期で実行
        results_with_score = await manager.asimilarity_search_with_score(query, k=2)
        
        logger.info(f"非同期スコア付き検索結果: {len(results_with_score)}件")
        for i, (doc, score) in enumerate(results_with_score):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"スコア: {score}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        logger.info("=== 例の終了 ===")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)


def example_chroma_basic_usage():
    """ChromaDBベクトルDBマネージャーの基本的な使用例"""
    try:
        logger.info("=== ChromaDBベクトルDBマネージャーの基本的な使用例 ===")
        
        # 一時的な永続化ディレクトリを作成
        persist_dir = "/tmp/chroma_example"
        os.makedirs(persist_dir, exist_ok=True)
        
        # ChromaDBベクトルDBマネージャーを作成
        manager = VectorDBManagerFactory.create(
            db_type="chroma",
            persist_directory=persist_dir,
            collection_name="sample_collection"
        )
        
        # サンプルドキュメントを作成
        documents = create_sample_documents()
        
        # ドキュメントを追加
        manager.add_documents(documents)
        logger.info(f"{len(documents)}個のドキュメントを追加しました")
        
        # 類似度検索を実行
        query = "AIフレームワークについて教えてください"
        results = manager.similarity_search(query, k=2)
        
        logger.info(f"クエリ: {query}")
        logger.info(f"検索結果: {len(results)}件")
        for i, doc in enumerate(results):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        # フィルタ付き検索を実行
        filter_dict = {"category": "vector_db"}
        filtered_results = manager.similarity_search(query, k=2, filter=filter_dict)
        
        logger.info(f"フィルタ付き検索結果: {len(filtered_results)}件")
        for i, doc in enumerate(filtered_results):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        logger.info("=== 例の終了 ===")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)


def example_embedding_model_usage():
    """埋め込みモデルの使用例"""
    try:
        logger.info("=== 埋め込みモデルの使用例 ===")
        
        # 埋め込みモデルを作成
        model = EmbeddingModelFactory.create(
            model_type="simplified",
            dimension=384
        )
        
        # テキストを埋め込む
        texts = [
            "これは最初のテキストです。",
            "これは2番目のテキストです。"
        ]
        
        embeddings = model.embed_documents(texts)
        
        logger.info(f"{len(texts)}個のテキストを埋め込みました")
        logger.info(f"埋め込みベクトルの次元数: {len(embeddings[0])}")
        
        # クエリを埋め込む
        query = "これはクエリテキストです。"
        query_embedding = model.embed_query(query)
        
        logger.info(f"クエリを埋め込みました")
        logger.info(f"クエリ埋め込みベクトルの次元数: {len(query_embedding)}")
        
        logger.info("=== 例の終了 ===")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)


def example_factory_from_config():
    """設定からベクトルDBマネージャーを作成する例"""
    try:
        logger.info("=== 設定からベクトルDBマネージャーを作成する例 ===")
        
        # 設定を定義
        config = {
            "db_type": "faiss",
            "persist_directory": "/tmp/faiss_config_example",
            "embedding": {
                "model_type": "simplified",
                "dimension": 384
            },
            "cache": {
                "use_cache": True,
                "ttl": 3600
            }
        }
        
        # 設定からベクトルDBマネージャーを作成
        manager = VectorDBManagerFactory.create_from_config(config)
        
        # サンプルドキュメントを作成
        documents = create_sample_documents()
        
        # ドキュメントを追加
        manager.add_documents(documents)
        logger.info(f"{len(documents)}個のドキュメントを追加しました")
        
        # 類似度検索を実行
        query = "Webフレームワークについて教えてください"
        results = manager.similarity_search(query, k=2)
        
        logger.info(f"クエリ: {query}")
        logger.info(f"検索結果: {len(results)}件")
        for i, doc in enumerate(results):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        # キャッシュを使用した2回目の検索（高速）
        cached_results = manager.similarity_search(query, k=2)
        logger.info(f"キャッシュを使用した検索結果: {len(cached_results)}件")
        
        # キャッシュをクリア
        manager.clear_cache()
        logger.info("キャッシュをクリアしました")
        
        logger.info("=== 例の終了 ===")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)


def example_service_specific_usage():
    """サービス固有のベクトルDBマネージャーの使用例"""
    try:
        logger.info("=== サービス固有のベクトルDBマネージャーの使用例 ===")
        
        # サービスIDを指定してベクトルDBマネージャーを作成
        service_id = "example_service"
        manager = VectorDBManagerFactory.create_default(service_id)
        
        # サンプルドキュメントを作成
        documents = create_sample_documents()
        
        # ドキュメントを追加
        manager.add_documents(documents)
        logger.info(f"{len(documents)}個のドキュメントを追加しました")
        
        # 類似度検索を実行
        query = "データベースについて教えてください"
        results = manager.similarity_search(query, k=2)
        
        logger.info(f"クエリ: {query}")
        logger.info(f"検索結果: {len(results)}件")
        for i, doc in enumerate(results):
            logger.info(f"結果{i+1}: {doc.page_content}")
            logger.info(f"メタデータ: {doc.metadata}")
        
        logger.info("=== 例の終了 ===")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)


async def run_all_examples():
    """全ての例を実行する"""
    logger.info("全ての例を実行します...")
    
    # 同期の例
    example_faiss_basic_usage()
    example_embedding_model_usage()
    example_factory_from_config()
    example_service_specific_usage()
    
    try:
        # ChromaDBの例（ChromaDBがインストールされている場合のみ実行）
        import chromadb
        example_chroma_basic_usage()
    except ImportError:
        logger.warning("ChromaDBがインストールされていないため、ChromaDBの例はスキップします")
    
    # 非同期の例
    await example_faiss_async_usage()
    
    logger.info("全ての例の実行が完了しました")


if __name__ == "__main__":
    """メイン関数"""
    # 非同期関数を実行するためのイベントループを取得
    loop = asyncio.get_event_loop()
    
    try:
        # 全ての例を実行
        loop.run_until_complete(run_all_examples())
    finally:
        # イベントループを閉じる
        loop.close()
