"""
ベクトルデータベース管理モジュール

このモジュールは、異なるベクトルデータベース（FAISS, ChromaDB等）に対して統一的なインターフェースを提供します。
同期処理と非同期処理の両方に対応し、タイムアウト処理とリトライ機構を組み込んでいます。
"""

import abc
import os
import json
import pickle
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, TypeVar, Tuple
import hashlib

from app.config import settings
from app.exceptions import CaseforgeException, ErrorCode
from app.utils.path_manager import path_manager
from app.logging_config import logger
from app.utils.retry import retry, async_retry, RetryStrategy
from app.utils.timeout import timeout, async_timeout

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS, Chroma, PGVector
from faiss import IndexFlatL2
from langchain_community.docstore.in_memory import InMemoryDocstore

from app.services.vector_db.embeddings import (
    EmbeddingModel,
    EmbeddingModelFactory,
    EmbeddingModelWrapper,
    EmbeddingException
)

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
        
        mtime = os.path.getmtime(str(cache_path))
        if datetime.fromtimestamp(mtime) + timedelta(seconds=self.ttl) < datetime.now():
            os.remove(cache_path)
            return None
        
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading document cache: {e}", exc_info=True)
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
            if path_manager.exists(cache_path):
                os.remove(str(cache_path))
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        キャッシュをクリア
        
        Args:
            key: クリアするキャッシュキー、Noneの場合は全てのキャッシュをクリア
        """
        if key is None:
            for file in os.listdir(str(self.cache_dir)):
                if file.endswith(".pkl"):
                    os.remove(path_manager.join_path(self.cache_dir, file))
        else:
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
        self.embedding_model = embedding_model or EmbeddingModelFactory.create_default()
        self.embedding_function = EmbeddingModelWrapper(self.embedding_model)
        
        self.persist_directory = persist_directory
        if self.persist_directory:
            os.makedirs(self.persist_directory, exist_ok=True)
        
        self.collection_name = collection_name or "default"
        
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
        
        cache_config = cache_config or {}
        self.document_cache = DocumentCache(
            cache_dir=cache_config.get("cache_dir"),
            ttl=cache_config.get("ttl", 3600)
        )
        self.use_cache = cache_config.get("use_cache", True)
        self.extra_params = kwargs
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
            
            if self.use_cache:
                self.document_cache.clear()
            
            self._add_documents(documents)
            
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
            
            if self.use_cache:
                cache_key = self._get_cache_key_for_query(query, k, filter)
                cached_results = self.document_cache.get(cache_key)
                if cached_results:
                    logger.info(f"Using cached results for query: {query[:30]}...")
                    return cached_results
            
            results = self._similarity_search(query, k, filter)
            
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
            if self.use_cache:
                self.document_cache.clear()
            
            await self._aadd_documents(documents)
            
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
            if self.use_cache:
                cache_key = self._get_cache_key_for_query(query, k, filter)
                cached_results = self.document_cache.get(cache_key)
                if cached_results:
                    logger.info(f"Using cached results for query: {query[:30]}...")
                    return cached_results
            
            results = await self._asimilarity_search(query, k, filter)
            
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
                self.vectordb = FAISS.load_local(
                    self.persist_directory,
                    self.embedding_function,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"Loaded FAISS index from {self.persist_directory}")
            else:
                embedding_dim = 384
                index = IndexFlatL2(embedding_dim)
                docstore = InMemoryDocstore()
                index_to_docstore_id = {}

                self.vectordb = FAISS(
                    index=index,
                    docstore=docstore,
                    index_to_docstore_id=index_to_docstore_id,
                    embedding_function=self.embedding_function,
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
        return await asyncio.to_thread(self._similarity_search_with_score, query, k, filter)
    
    async def _asave(self) -> None:
        """FAISSベクトルDBを非同期で保存する"""
        await asyncio.to_thread(self._save)


class ChromaDBManager(VectorDBManager):
    """ChromaDBベクトルDBマネージャー"""
    
    def _setup_vectordb(self) -> None:
        """ChromaDBベクトルDBの設定"""
        try:
            from chromadb.config import Settings as ChromaSettings
            import chromadb
            
            chroma_settings = ChromaSettings(
                anonymized_telemetry=False,
                persist_directory=self.persist_directory
            )
            
            client = chromadb.Client(chroma_settings)
            
            if self.persist_directory:
                self.vectordb = Chroma(
                    client=client,
                    collection_name=self.collection_name,
                    embedding_function=self.embedding_function,
                    persist_directory=self.persist_directory
                )
                logger.info(f"Loaded ChromaDB collection from {self.persist_directory}")
            else:
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
        return await asyncio.to_thread(self._similarity_search_with_score, query, k, filter)
    
    async def _asave(self) -> None:
        """ChromaDBベクトルDBを非同期で保存する"""
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
        
        embedding_config = config.get("embedding", {})
        embedding_model = None
        if embedding_config:
            embedding_model = EmbeddingModelFactory.create_from_config(embedding_config)
        
        cache_config = config.get("cache", {})
        
        kwargs = {k: v for k, v in config.items() if k not in ["db_type", "persist_directory", "collection_name", "embedding", "cache"]}
        
        kwargs["cache_config"] = cache_config
        
        return VectorDBManagerFactory.create(
            db_type=db_type,
            embedding_model=embedding_model,
            persist_directory=persist_directory,
            collection_name=collection_name,
            **kwargs
        )
    
    @staticmethod
    def create_default(service_id: Optional[str] = None) -> VectorDBManager:
        """
        デフォルトのベクトルDBマネージャーを作成する
        
        Args:
            service_id: サービスID
            
        Returns:
            ベクトルDBマネージャー
        """
        db_type = os.environ.get("VECTOR_DB_TYPE", "faiss")
        logger.info(f"📌 VECTOR_DB_TYPE = {db_type}")
        
        data_dir = os.environ.get("DATA_DIR", "/app/data")
        persist_directory = path_manager.join_path(data_dir, db_type, service_id) if service_id else None
        logger.info(f"📂 persist_directory = {persist_directory}")
        
        collection_name = service_id if service_id else "default"
        logger.info(f"📁 collection_name = {collection_name}")

        logger.info("🧠 Creating embedding model...")
        embedding_model = EmbeddingModelFactory.create_default()
        logger.info("✅ Embedding model created")

        logger.info("🧱 Creating vector DB manager...")
        
        if db_type == "pgvector":
            # PGVectorManager の初期化パラメータを設定
            return PGVectorManager(
                embedding_model=embedding_model,
                collection_name=collection_name, # service_id が設定される
                timeout_seconds=settings.TIMEOUT_EMBEDDING,
                retry_config=None, # 必要に応じて設定
                cache_config=None, # 必要に応じて設定
                service_id=service_id # service_id は必須
            )
        
        return VectorDBManagerFactory.create(
            db_type=db_type,
            embedding_model=embedding_model,
            persist_directory=persist_directory,
            collection_name=collection_name
        )

import os
from typing import List, Dict, Any, Optional, Tuple

from sqlmodel import SQLModel, Field, create_engine, Session, select
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column

from langchain_core.documents import Document

from app.config import settings
from app.models.schema_chunk import SchemaChunk
from app.services.vector_db.embeddings import EmbeddingModelWrapper
from app.logging_config import logger

DATABASE_URL = settings.DATABASE_URL

class PGVectorManager(VectorDBManager):
    """PGVectorベクトルDBマネージャー"""

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModelWrapper] = None,
        collection_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        cache_config: Optional[Dict[str, Any]] = None,
        service_id: Optional[int] = None,
        **kwargs
    ):
        """
        PGVectorマネージャーの初期化

        Args:
            embedding_model: 埋め込みモデルラッパー
            collection_name: コレクション名（ここではservice_idを使用）
            timeout_seconds: タイムアウト秒数
            retry_config: リトライ設定
            cache_config: キャッシュ設定
            service_id: サービスID (必須)
            **kwargs: その他のパラメータ
        """
        if service_id is None:
            raise ValueError("service_id must be provided for PGVectorManager")

        self.service_id = service_id
        # collection_name は service_id を使用する
        collection_name = str(service_id)

        super().__init__(
            embedding_model=embedding_model,
            collection_name=collection_name,
            timeout_seconds=timeout_seconds,
            retry_config=retry_config,
            cache_config=cache_config,
            **kwargs
        )

        self.engine = create_engine(DATABASE_URL)
        SQLModel.metadata.create_all(self.engine) # テーブルが存在しない場合は作成

    def _setup_vectordb(self) -> None:
        """PGVectorの設定"""
        # PGVectorはデータベース自体がベクトルDBとして機能するため、特別なセットアップは不要
        # テーブルの存在確認や作成は__init__で行う
        logger.info(f"PGVectorManager setup complete for service_id: {self.service_id}")
        pass

    def _add_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをPGVectorに追加する

        Args:
            documents: 追加するドキュメント
        """
        logger.info(f"Adding {len(documents)} documents to PGVector for service_id: {self.service_id}")
        schema_chunks = []
        for doc in documents:
            # Documentのmetadataからpathとmethodを取得することを想定
            path = doc.metadata.get("path")
            method = doc.metadata.get("method")
            if not path or not method:
                logger.warning(f"Skipping document due to missing path or method in metadata: {doc.metadata}")
                continue

            try:
                # embedding_functionはVectorDBManagerの__init__で初期化済み
                embedding = self.embedding_function.embed_query(doc.page_content)
                schema_chunk = SchemaChunk(
                    service_id=self.service_id,
                    path=path,
                    method=method,
                    content=doc.page_content,
                    embedding=embedding
                )
                schema_chunks.append(schema_chunk)
            except Exception as e:
                logger.error(f"Error creating SchemaChunk for document: {doc.metadata}. Error: {e}", exc_info=True)
                # エラーが発生したドキュメントはスキップし、処理を続行

        if not schema_chunks:
            logger.warning("No valid schema chunks to add.")
            return

        with Session(self.engine) as session:
            try:
                session.add_all(schema_chunks)
                session.commit()
                logger.info(f"Successfully added {len(schema_chunks)} schema chunks to PGVector.")
            except Exception as e:
                session.rollback()
                logger.error(f"Error adding schema chunks to database: {e}", exc_info=True)
                raise VectorDBException(f"スキーマチャンクのデータベース追加中にエラーが発生しました: {e}", details={
                    "service_id": self.service_id,
                    "error": str(e)
                })

    def _similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        PGVectorで類似度検索を実行する

        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ (service_idでのフィルタリングを想定)

        Returns:
            類似度の高いドキュメントのリスト
        """
        logger.info(f"Performing PGVector similarity search for query: {query[:30]}... with k={k} and filter={filter}")
        try:
            # クエリのembeddingを生成
            query_embedding = self.embedding_function.embed_query(query)

            with Session(self.engine) as session:
                # 類似度検索クエリの構築
                # service_id でフィルタリングし、embedding の類似度でソート
                # 類似度演算子 '<->' はL2距離（ユークリッド距離）
                # 距離が小さいほど類似度が高いので、昇順でソート
                statement = select(SchemaChunk).where(
                    SchemaChunk.service_id == self.service_id
                ).order_by(
                    SchemaChunk.embedding.l2_distance(query_embedding)
                ).limit(k)

                results = session.exec(statement).all()

                # 結果をLangChainのDocumentオブジェクトに変換
                documents = []
                for chunk in results:
                    metadata = {
                        "service_id": chunk.service_id,
                        "path": chunk.path,
                        "method": chunk.method,
                        # embedding はメタデータに含めない
                    }
                    documents.append(Document(page_content=chunk.content, metadata=metadata))

                logger.info(f"PGVector similarity search found {len(documents)} documents.")
                return documents

        except Exception as e:
            logger.error(f"Error performing PGVector similarity search: {e}", exc_info=True)
            raise VectorDBException(f"PGVector類似度検索中にエラーが発生しました: {e}", details={
                "query": query,
                "k": k,
                "filter": filter,
                "error": str(e)
            })

    def _similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        PGVectorでスコア付きの類似度検索を実行する

        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ (service_idでのフィルタリングを想定)

        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        logger.info(f"Performing PGVector similarity search with score for query: {query[:30]}... with k={k} and filter={filter}")
        try:
            # クエリのembeddingを生成
            query_embedding = self.embedding_function.embed_query(query)

            with Session(self.engine) as session:
                # 類似度検索クエリの構築（スコア付き）
                # スコアはL2距離の逆数や、1 - 距離/最大距離などで正規化することも考えられるが、
                # ここではL2距離そのものをスコアとして返す（距離が小さいほど類似度が高い）
                statement = select(SchemaChunk, SchemaChunk.embedding.l2_distance(query_embedding)).where(
                     SchemaChunk.service_id == self.service_id
                ).order_by(
                    SchemaChunk.embedding.l2_distance(query_embedding)
                ).limit(k)

                results = session.exec(statement).all()

                # 結果をLangChainのDocumentオブジェクトとスコアのタプルに変換
                documents_with_score = []
                for chunk, score in results:
                    metadata = {
                        "service_id": chunk.service_id,
                        "path": chunk.path,
                        "method": chunk.method,
                    }
                    documents_with_score.append((Document(page_content=chunk.content, metadata=metadata), score))

                logger.info(f"PGVector similarity search with score found {len(documents_with_score)} documents.")
                return documents_with_score

        except Exception as e:
            logger.error(f"Error performing PGVector similarity search with score: {e}", exc_info=True)
            raise VectorDBException(f"PGVectorスコア付き類似度検索中にエラーが発生しました: {e}", details={
                "query": query,
                "k": k,
                "filter": filter,
                "error": str(e)
            })


    def _save(self) -> None:
        """
        PGVectorはデータベースに永続化されるため、特別な保存処理は不要
        """
        logger.info("PGVector does not require explicit save operation.")
        pass

    async def _aadd_documents(self, documents: List[Document]) -> None:
        """
        ドキュメントをPGVectorに非同期で追加する

        Args:
            documents: 追加するドキュメント
        """
        logger.warning("Asynchronous add_documents not fully implemented for PGVectorManager, falling back to sync.")
        self._add_documents(documents)

    async def _asimilarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        PGVectorで類似度検索を非同期で実行する

        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ

        Returns:
            類似度の高いドキュメントのリスト
        """
        logger.warning("Asynchronous similarity_search not fully implemented for PGVectorManager, falling back to sync.")
        return self._similarity_search(query, k, filter)

    async def _asimilarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        PGVectorでスコア付きの類似度検索を非同期で実行する

        Args:
            query: 検索クエリ
            k: 取得するドキュメント数
            filter: 検索フィルタ

        Returns:
            類似度の高いドキュメントとスコアのタプルのリスト
        """
        logger.warning("Asynchronous similarity_search_with_score not fully implemented for PGVectorManager, falling back to sync.")
        return self._similarity_search_with_score(query, k, filter)
