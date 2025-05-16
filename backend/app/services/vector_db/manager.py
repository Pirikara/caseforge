"""
ベクトルデータベース管理モジュール

このモジュールは、異なるベクトルデータベース（FAISS, ChromaDB等）に対して統一的なインターフェースを提供します。
同期処理と非同期処理の両方に対応し、タイムアウト処理とリトライ機構を組み込んでいます。
"""

import abc
import os
import json
import pickle
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Type, TypeVar, Union, cast, Callable, Tuple
import hashlib

from app.config import settings
from app.exceptions import CaseforgeException, ErrorCode, TimeoutException
from app.utils.path_manager import path_manager
from app.logging_config import logger
from app.utils.retry import retry, async_retry, RetryStrategy, run_with_retry
from app.utils.timeout import timeout, async_timeout, run_with_timeout

# サードパーティライブラリのインポート
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain_core.vectorstores import VectorStore

# 自作モジュールのインポート
from app.services.vector_db.embeddings import (
    EmbeddingModel, 
    EmbeddingModelFactory, 
    EmbeddingModelWrapper,
    EmbeddingException
)

# 型変数の定義
T = TypeVar('T')
VectorDBManagerType = TypeVar('VectorDBManagerType', bound='VectorDBManager')


class VectorDBException(CaseforgeException):
    """ベクトルDB関連の例外"""
    def __init__(
        self,
        message: str = "ベクトルDB操作中にエラーが発生しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.VECTOR_DB_ERROR, details)


class DocumentCache:
    """ドキュメントキャッシュクラス"""
    
    def __init__(self, cache_dir: str = None, ttl: int = 3600):
        """
        キャッシュの初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
            ttl: キャッシュの有効期間（秒）
        """
        self.cache_dir = cache_dir or path_manager.join_path(
            os.environ.get("DATA_DIR", "/app/data"),
            "document_cache"
        )
        self.ttl = ttl
        
        # キャッシュディレクトリの作成
        path_manager.ensure_dir(self.cache_dir)
    
    def _get_cache_key(self, key: str) -> str:
        """
        キャッシュキーのハッシュ値を取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            ハッシュ化されたキャッシュキー
        """
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> str:
        """
        キャッシュファイルのパスを取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            キャッシュファイルのパス
        """
        cache_key = self._get_cache_key(key)
        return path_manager.join_path(self.cache_dir, f"{cache_key}.pkl")
    
    def get(self, key: str) -> Optional[List[Document]]:
        """
        キャッシュからドキュメントを取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            キャッシュされたドキュメント、存在しない場合はNone
        """
        cache_path = self._get_cache_path(key)
        
        if not path_manager.exists(cache_path):
            return None
        
        # キャッシュの有効期限をチェック
        mtime = os.path.getmtime(str(cache_path))
        if datetime.fromtimestamp(mtime) + timedelta(seconds=self.ttl) < datetime.now():
            # キャッシュの有効期限切れ
            os.remove(cache_path)
            return None
        
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading document cache: {e}", exc_info=True)
            # 破損したキャッシュを削除
            os.remove(cache_path)
            return None
    
    def set(self, key: str, documents: List[Document]) -> None:
        """
        ドキュメントをキャッシュに保存
        
        Args:
            key: キャッシュキー
            documents: キャッシュするドキュメント
        """
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(documents, f)
        except Exception as e:
            logger.error(f"Error saving document cache: {e}", exc_info=True)
            # 保存に失敗した場合、部分的に書き込まれたファイルを削除
            if path_manager.exists(cache_path):
                os.remove(str(cache_path))
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        キャッシュをクリア
        
        Args:
            key: クリアするキャッシュキー、Noneの場合は全てのキャッシュをクリア
        """
        if key is None:
            # 全てのキャッシュをクリア
            for file in os.listdir(str(self.cache_dir)):
                if file.endswith(".pkl"):
                    os.remove(path_manager.join_path(self.cache_dir, file))
        else:
            # 特定のキャッシュをクリア
            cache_path = self._get_cache_path(key)
            if path_manager.exists(cache_path):
                os.remove(str(cache_path))
    
    def cleanup_expired(self) -> int:
        """
        期限切れのキャッシュをクリア
        
        Returns:
            削除されたキャッシュの数
        """
        count = 0
class VectorDBManager(abc.ABC):
    """ベクトルDBマネージャーの抽象基底クラス"""
    
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        cache_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        ベクトルDBマネージャーの初期化
        
        Args:
            embedding_model: 埋め込みモデル
            persist_directory: 永続化ディレクトリ
            collection_name: コレクション名
            timeout_seconds: タイムアウト秒数
            retry_config: リトライ設定
            cache_config: キャッシュ設定
            **kwargs: その他のパラメータ
        """
        # 埋め込みモデルの設定
        self.embedding_model = embedding_model or EmbeddingModelFactory.create_default()
        self.embedding_function = EmbeddingModelWrapper(self.embedding_model)
        
        # 永続化ディレクトリの設定
        self.persist_directory = persist_directory
        if self.persist_directory:
            os.makedirs(self.persist_directory, exist_ok=True)
        
        # コレクション名の設定
        self.collection_name = collection_name or "default"
        
        # タイムアウトとリトライの設定
        self.timeout_seconds = timeout_seconds or settings.TIMEOUT_EMBEDDING
        self.retry_config = retry_config or {
            "max_retries": 3,
            "retry_delay": 2.0,
            "max_retry_delay": 10.0,
            "retry_jitter": 0.1,
            "backoff_factor": 2.0,
            "retry_strategy": RetryStrategy.EXPONENTIAL,
            "retry_exceptions": [ConnectionError, TimeoutError, ValueError]
        }
        
        # キャッシュの設定
        cache_config = cache_config or {}
        self.document_cache = DocumentCache(
            cache_dir=cache_config.get("cache_dir"),
            ttl=cache_config.get("ttl", 3600)
        )
        self.use_cache = cache_config.get("use_cache", True)
        
        # その他のパラメータ
        self.extra_params = kwargs
        
        # ベクトルDBの初期化
        self.vectordb = None
        self._setup_vectordb()
    
    @abc.abstractmethod
    def _setup_vectordb(self) -> None:
        """ベクトルDBの設定（サブクラスで実装）"""
        pass
    
    @abc.abstractmethod
    def _add_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをベクトルDBに追加する（サブクラスで実装）
        
        Args:
            documents: 追加するドキュメント
        """
        pass
    
    @abc.abstractmethod
    def _similarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        類似度検索を実行する（サブクラスで実装）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        pass
    
    @abc.abstractmethod
    def _similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        スコア付きの類似度検索を実行する（サブクラスで実装）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        pass
    
    @abc.abstractmethod
    def _save(self) -> None:
        """
        ベクトルDBを保存する（サブクラスで実装）
        """
        pass
    
    @abc.abstractmethod
    async def _aadd_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをベクトルDBに非同期で追加する（サブクラスで実装）
        
        Args:
            documents: 追加するドキュメント
        """
        pass
    
    @abc.abstractmethod
    async def _asimilarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        類似度検索を非同期で実行する（サブクラスで実装）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        pass
    
    @abc.abstractmethod
    async def _asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        スコア付きの類似度検索を非同期で実行する（サブクラスで実装）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        pass
    
    @abc.abstractmethod
    async def _asave(self) -> None:
        """
        ベクトルDBを非同期で保存する（サブクラスで実装）
        """
        pass
    
    def _get_cache_key_for_documents(self, documents: List[Document]) -> str:
        """
        ドキュメントのキャッシュキーを生成
        
        Args:
            documents: キャッシュキーを生成するドキュメント
            
        Returns:
            キャッシュキー
        """
        # ドキュメントの内容とメタデータからハッシュを生成
        content_hash = hashlib.md5()
        for doc in documents:
            content_hash.update(doc.page_content.encode())
            if doc.metadata:
                content_hash.update(json.dumps(doc.metadata, sort_keys=True).encode())
        
        return f"docs_{content_hash.hexdigest()}"
    
    def _get_cache_key_for_query(self, query: str, k: int, filter: Optional[Dict[str, Any]]) -> str:
        """
        クエリのキャッシュキーを生成
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            キャッシュキー
        """
        # クエリとフィルタからハッシュを生成
        query_hash = hashlib.md5()
        query_hash.update(query.encode())
        query_hash.update(str(k).encode())
        if filter:
            query_hash.update(json.dumps(filter, sort_keys=True).encode())
        
        return f"query_{query_hash.hexdigest()}"
    
    @retry(retry_key="VECTOR_DB")
    @timeout(timeout_key="VECTOR_DB")
    def add_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをベクトルDBに追加する（タイムアウトとリトライ付き）
        
        Args:
            documents: 追加するドキュメント
        """
        try:
            logger.info(f"Adding {len(documents)} documents to vector database")
            
            # キャッシュをクリア（ドキュメントが追加されるとキャッシュが無効になるため）
            if self.use_cache:
                self.document_cache.clear()
            
            self._add_documents(documents)
            
            # 変更を保存
            if self.persist_directory:
                self._save()
            
            logger.info(f"Successfully added {len(documents)} documents to vector database")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}", exc_info=True)
            raise VectorDBException(f"ドキュメント追加中にエラーが発生しました: {e}", details={
                "error": str(e)
            })
    
    @retry(retry_key="VECTOR_DB")
    @timeout(timeout_key="VECTOR_DB")
    def similarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        類似度検索を実行する（タイムアウトとリトライ付き）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        try:
            logger.info(f"Performing similarity search for query: {query[:30]}...")
            
            # キャッシュをチェック
            if self.use_cache:
                cache_key = self._get_cache_key_for_query(query, k, filter)
                cached_results = self.document_cache.get(cache_key)
                if cached_results:
                    logger.info(f"Using cached results for query: {query[:30]}...")
                    return cached_results
            
            results = self._similarity_search(query, k, filter)
            
            # 結果をキャッシュ
            if self.use_cache:
                self.document_cache.set(cache_key, results)
            
            logger.info(f"Successfully performed similarity search, found {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}", exc_info=True)
            raise VectorDBException(f"類似度検索中にエラーが発生しました: {e}", details={
                "query": query,
                "error": str(e)
            })
    
    @retry(retry_key="VECTOR_DB")
    @timeout(timeout_key="VECTOR_DB")
    def similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        スコア付きの類似度検索を実行する（タイムアウトとリトライ付き）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        try:
            logger.info(f"Performing similarity search with score for query: {query[:30]}...")
            
            # キャッシュは使用しない（スコアが含まれるため）
            
            results = self._similarity_search_with_score(query, k, filter)
            
            logger.info(f"Successfully performed similarity search with score, found {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error performing similarity search with score: {e}", exc_info=True)
            raise VectorDBException(f"スコア付き類似度検索中にエラーが発生しました: {e}", details={
                "query": query,
                "error": str(e)
            })
    
    @async_retry(retry_key="VECTOR_DB")
    @async_timeout(timeout_key="VECTOR_DB")
    async def aadd_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをベクトルDBに非同期で追加する（タイムアウトとリトライ付き）
        
        Args:
            documents: 追加するドキュメント
        """
        try:
            logger.info(f"Async adding {len(documents)} documents to vector database")
            
            # キャッシュをクリア（ドキュメントが追加されるとキャッシュが無効になるため）
            if self.use_cache:
                self.document_cache.clear()
            
            await self._aadd_documents(documents)
            
            # 変更を保存
            if self.persist_directory:
                await self._asave()
            
            logger.info(f"Successfully async added {len(documents)} documents to vector database")
        except Exception as e:
            logger.error(f"Error async adding documents to vector database: {e}", exc_info=True)
            raise VectorDBException(f"ドキュメント非同期追加中にエラーが発生しました: {e}", details={
                "error": str(e)
            })
    
    @async_retry(retry_key="VECTOR_DB")
    @async_timeout(timeout_key="VECTOR_DB")
    async def asimilarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        類似度検索を非同期で実行する（タイムアウトとリトライ付き）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        try:
            logger.info(f"Async performing similarity search for query: {query[:30]}...")
            
            # キャッシュをチェック
            if self.use_cache:
                cache_key = self._get_cache_key_for_query(query, k, filter)
                cached_results = self.document_cache.get(cache_key)
                if cached_results:
                    logger.info(f"Using cached results for query: {query[:30]}...")
                    return cached_results
            
            results = await self._asimilarity_search(query, k, filter)
            
            # 結果をキャッシュ
            if self.use_cache:
                self.document_cache.set(cache_key, results)
            
            logger.info(f"Successfully async performed similarity search, found {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error async performing similarity search: {e}", exc_info=True)
            raise VectorDBException(f"非同期類似度検索中にエラーが発生しました: {e}", details={
                "query": query,
                "error": str(e)
            })
    
    @async_retry(retry_key="VECTOR_DB")
    @async_timeout(timeout_key="VECTOR_DB")
    async def asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        スコア付きの類似度検索を非同期で実行する（タイムアウトとリトライ付き）
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        try:
            logger.info(f"Async performing similarity search with score for query: {query[:30]}...")
            
            # キャッシュは使用しない（スコアが含まれるため）
            
            results = await self._asimilarity_search_with_score(query, k, filter)
            
            logger.info(f"Successfully async performed similarity search with score, found {len(results)} documents")
            return results
        except Exception as e:
            logger.error(f"Error async performing similarity search with score: {e}", exc_info=True)
            raise VectorDBException(f"非同期スコア付き類似度検索中にエラーが発生しました: {e}", details={
                "query": query,
                "error": str(e)
            })
    
    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        if self.use_cache:
            self.document_cache.clear()
            logger.info("Document cache cleared")
        for file in os.listdir(str(self.cache_dir)):
            if file.endswith(".pkl"):
                file_path = path_manager.join_path(self.cache_dir, file)
                mtime = os.path.getmtime(str(file_path))
                if datetime.fromtimestamp(mtime) + timedelta(seconds=self.ttl) < datetime.now():
                    os.remove(str(file_path))
                    count += 1
        return count
class FAISSManager(VectorDBManager):
    """FAISSベクトルDBマネージャー"""
    
    def _setup_vectordb(self) -> None:
        """FAISSベクトルDBの設定"""
        try:
            if self.persist_directory and path_manager.exists(path_manager.join_path(self.persist_directory, "index.faiss")):
                # 既存のFAISSインデックスをロード
                self.vectordb = FAISS.load_local(
                    self.persist_directory,
                    self.embedding_function,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded FAISS index from {self.persist_directory}")
            else:
                # 新しいFAISSインデックスを作成
                self.vectordb = FAISS(
                    embedding_function=self.embedding_function,
                    **{k: v for k, v in self.extra_params.items() if k != "embedding_function"}
                )
                logger.info("Created new FAISS index")
        except Exception as e:
            logger.error(f"Error setting up FAISS vector database: {e}", exc_info=True)
            raise VectorDBException(f"FAISSベクトルDBの設定に失敗しました: {e}", details={
                "persist_directory": self.persist_directory,
                "error": str(e)
            })
    
    def _add_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをFAISSベクトルDBに追加する
        
        Args:
            documents: 追加するドキュメント
        """
        if self.vectordb is None:
            raise VectorDBException("FAISSベクトルDBが初期化されていません")
        
        self.vectordb.add_documents(documents)
    
    def _similarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        FAISSベクトルDBで類似度検索を実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        if self.vectordb is None:
            raise VectorDBException("FAISSベクトルDBが初期化されていません")
        
        return self.vectordb.similarity_search(query, k=k, filter=filter)
    
    def _similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        FAISSベクトルDBでスコア付きの類似度検索を実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        if self.vectordb is None:
            raise VectorDBException("FAISSベクトルDBが初期化されていません")
        
        return self.vectordb.similarity_search_with_score(query, k=k, filter=filter)
    
    def _save(self) -> None:
        """FAISSベクトルDBを保存する"""
        if self.vectordb is None:
            raise VectorDBException("FAISSベクトルDBが初期化されていません")
        
        if self.persist_directory:
            self.vectordb.save_local(self.persist_directory)
            logger.info(f"Saved FAISS index to {self.persist_directory}")
    
    async def _aadd_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをFAISSベクトルDBに非同期で追加する
        
        Args:
            documents: 追加するドキュメント
        """
        # FAISSは非同期APIを提供していないため、同期メソッドを使用
        await asyncio.to_thread(self._add_documents, documents)
    
    async def _asimilarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        FAISSベクトルDBで類似度検索を非同期で実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        # FAISSは非同期APIを提供していないため、同期メソッドを使用
        return await asyncio.to_thread(self._similarity_search, query, k, filter)
    
    async def _asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        FAISSベクトルDBでスコア付きの類似度検索を非同期で実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        # FAISSは非同期APIを提供していないため、同期メソッドを使用
        return await asyncio.to_thread(self._similarity_search_with_score, query, k, filter)
    
    async def _asave(self) -> None:
        """FAISSベクトルDBを非同期で保存する"""
        # FAISSは非同期APIを提供していないため、同期メソッドを使用
        await asyncio.to_thread(self._save)


class ChromaDBManager(VectorDBManager):
    """ChromaDBベクトルDBマネージャー"""
    
    def _setup_vectordb(self) -> None:
        """ChromaDBベクトルDBの設定"""
        try:
            # ChromaDBのクライアントを設定
            from chromadb.config import Settings as ChromaSettings
            import chromadb
            
            # ChromaDBの設定
            chroma_settings = ChromaSettings(
                anonymized_telemetry=False,
                persist_directory=self.persist_directory
            )
            
            # ChromaDBのクライアントを作成
            client = chromadb.Client(chroma_settings)
            
            # コレクションを取得または作成
            if self.persist_directory:
                # 永続化ディレクトリが指定されている場合、既存のコレクションをロード
                self.vectordb = Chroma(
                    client=client,
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function,
                    persist_directory=self.persist_directory
                )
                logger.info(f"Loaded ChromaDB collection from {self.persist_directory}")
            else:
                # 永続化ディレクトリが指定されていない場合、新しいコレクションを作成
                self.vectordb = Chroma(
                    client=client,
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Created new ChromaDB collection: {self.collection_name}")
        except ImportError:
            logger.error("ChromaDB is not installed. Please install it with 'pip install chromadb'.")
            raise VectorDBException("ChromaDBがインストールされていません。'pip install chromadb'でインストールしてください。")
        except Exception as e:
            logger.error(f"Error setting up ChromaDB vector database: {e}", exc_info=True)
            raise VectorDBException(f"ChromaDBベクトルDBの設定に失敗しました: {e}", details={
                "persist_directory": self.persist_directory,
                "collection_name": self.collection_name,
                "error": str(e)
            })
    
    def _add_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをChromaDBベクトルDBに追加する
        
        Args:
            documents: 追加するドキュメント
        """
        if self.vectordb is None:
            raise VectorDBException("ChromaDBベクトルDBが初期化されていません")
        
        self.vectordb.add_documents(documents)
    
    def _similarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        ChromaDBベクトルDBで類似度検索を実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        if self.vectordb is None:
            raise VectorDBException("ChromaDBベクトルDBが初期化されていません")
        
        # ChromaDBのフィルタ形式に変換
        where = filter if filter else None
        
        return self.vectordb.similarity_search(query, k=k, filter=where)
    
    def _similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        ChromaDBベクトルDBでスコア付きの類似度検索を実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        if self.vectordb is None:
            raise VectorDBException("ChromaDBベクトルDBが初期化されていません")
        
        # ChromaDBのフィルタ形式に変換
        where = filter if filter else None
        
        return self.vectordb.similarity_search_with_score(query, k=k, filter=where)
    
    def _save(self) -> None:
        """ChromaDBベクトルDBを保存する"""
        if self.vectordb is None:
            raise VectorDBException("ChromaDBベクトルDBが初期化されていません")
        
        if self.persist_directory:
            self.vectordb.persist()
            logger.info(f"Saved ChromaDB collection to {self.persist_directory}")
    
    async def _aadd_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをChromaDBベクトルDBに非同期で追加する
        
        Args:
            documents: 追加するドキュメント
        """
        # ChromaDBは非同期APIを提供していないため、同期メソッドを使用
        await asyncio.to_thread(self._add_documents, documents)
    
    async def _asimilarity_search(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        ChromaDBベクトルDBで類似度検索を非同期で実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントのリスト
        """
        # ChromaDBは非同期APIを提供していないため、同期メソッドを使用
        return await asyncio.to_thread(self._similarity_search, query, k, filter)
    
    async def _asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 4, 
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        ChromaDBベクトルDBでスコア付きの類似度検索を非同期で実行する
        
        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ
            
        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        # ChromaDBは非同期APIを提供していないため、同期メソッドを使用
        return await asyncio.to_thread(self._similarity_search_with_score, query, k, filter)
    
    async def _asave(self) -> None:
        """ChromaDBベクトルDBを非同期で保存する"""
        # ChromaDBは非同期APIを提供していないため、同期メソッドを使用
        await asyncio.to_thread(self._save)


class VectorDBManagerFactory:
    """ベクトルDBマネージャーのファクトリークラス"""
    
    @staticmethod
    def create(
        db_type: str = "faiss",
        embedding_model: Optional[EmbeddingModel] = None,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        **kwargs
    ) -> VectorDBManager:
        """
        ベクトルDBマネージャーを作成する
        
        Args:
            db_type: ベクトルDBの種類 ("faiss" または "chroma")
            embedding_model: 埋め込みモデル
            persist_directory: 永続化ディレクトリ
            collection_name: コレクション名
            **kwargs: その他のパラメータ
            
        Returns:
            ベクトルDBマネージャー
        """
        if db_type.lower() == "faiss":
            return FAISSManager(
                embedding_model=embedding_model,
                persist_directory=persist_directory,
                collection_name=collection_name,
                **kwargs
            )
        elif db_type.lower() == "chroma":
            return ChromaDBManager(
                embedding_model=embedding_model,
                persist_directory=persist_directory,
                collection_name=collection_name,
                **kwargs
            )
        else:
            raise ValueError(f"Unsupported vector database type: {db_type}")
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> VectorDBManager:
        """
        設定からベクトルDBマネージャーを作成する
        
        Args:
            config: ベクトルDBマネージャーの設定
            
        Returns:
            ベクトルDBマネージャー
        """
        db_type = config.get("db_type", "faiss")
        persist_directory = config.get("persist_directory")
        collection_name = config.get("collection_name")
        
        # 埋め込みモデルの設定
        embedding_config = config.get("embedding", {})
        embedding_model = None
        if embedding_config:
            embedding_model = EmbeddingModelFactory.create_from_config(embedding_config)
        
        # キャッシュの設定
        cache_config = config.get("cache", {})
        
        # その他のパラメータを抽出
        kwargs = {k: v for k, v in config.items() if k not in ["db_type", "persist_directory", "collection_name", "embedding", "cache"]}
        
        # キャッシュ設定を追加
        kwargs["cache_config"] = cache_config
        
        return VectorDBManagerFactory.create(
            db_type=db_type,
            embedding_model=embedding_model,
            persist_directory=persist_directory,
            collection_name=collection_name,
            **kwargs
        )
    
    @staticmethod
    def create_default(project_id: Optional[str] = None) -> VectorDBManager:
        """
        デフォルトのベクトルDBマネージャーを作成する
        
        Args:
            project_id: プロジェクトID
            
        Returns:
            ベクトルDBマネージャー
        """
        # 環境変数から設定を取得
        db_type = os.environ.get("VECTOR_DB_TYPE", "faiss")
        
        # 永続化ディレクトリの設定
        data_dir = os.environ.get("DATA_DIR", "/app/data")
        persist_directory = None
        if project_id:
            persist_directory = path_manager.join_path(data_dir, db_type, project_id)
        
        # コレクション名の設定
        collection_name = project_id if project_id else "default"
        
        # 埋め込みモデルの作成
        embedding_model = EmbeddingModelFactory.create_default()
        
        return VectorDBManagerFactory.create(
            db_type=db_type,
            embedding_model=embedding_model,
            persist_directory=persist_directory,
            collection_name=collection_name
        )