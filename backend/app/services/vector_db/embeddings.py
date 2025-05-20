"""
埋め込みモデルの管理モジュール

このモジュールは、異なる埋め込みモデルに対して統一的なインターフェースを提供します。
同期処理と非同期処理の両方に対応し、タイムアウト処理とリトライ機構を組み込んでいます。
"""

import abc
import hashlib
from typing import List, Dict, Any, Optional, TypeVar
import os

from app.config import settings
from app.exceptions import CaseforgeException, ErrorCode
from app.logging_config import logger
from app.utils.retry import retry, async_retry, RetryStrategy
from app.utils.timeout import timeout, async_timeout

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

T = TypeVar('T')
EmbeddingModelType = TypeVar('EmbeddingModelType', bound='EmbeddingModel')


class EmbeddingException(CaseforgeException):
    """埋め込み処理関連の例外"""
    def __init__(
        self,
        message: str = "埋め込み処理中にエラーが発生しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.EMBEDDING_ERROR, details)


class EmbeddingModel(abc.ABC):
    """埋め込みモデルの抽象基底クラス"""
    
    def __init__(
        self,
        model_name: str,
        dimension: int = 384,
        timeout_seconds: Optional[float] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        埋め込みモデルの初期化
        
        Args:
            model_name: モデル名
            dimension: 埋め込みベクトルの次元数
            timeout_seconds: タイムアウト秒数
            retry_config: リトライ設定
            **kwargs: その他のパラメータ
        """
        self.model_name = model_name
        self.dimension = dimension
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
        self.extra_params = kwargs
        
        # 初期化時に埋め込みモデルを設定
        self._setup_model()
    
    @abc.abstractmethod
    def _setup_model(self) -> None:
        """埋め込みモデルの設定（サブクラスで実装）"""
        pass
    
    @abc.abstractmethod
    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを埋め込む（サブクラスで実装）
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        pass
    
    @abc.abstractmethod
    def _embed_query(self, text: str) -> List[float]:
        """
        クエリテキストを埋め込む（サブクラスで実装）
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        pass
    
    @abc.abstractmethod
    async def _aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを非同期で埋め込む（サブクラスで実装）
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        pass
    
    @abc.abstractmethod
    async def _aembed_query(self, text: str) -> List[float]:
        """
        クエリテキストを非同期で埋め込む（サブクラスで実装）
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        pass
    
    @retry(retry_key="EMBEDDING")
    @timeout(timeout_key="EMBEDDING")
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを埋め込む（タイムアウトとリトライ付き）
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        try:
            logger.info(f"Embedding {len(texts)} documents with {self.model_name}")
            embeddings = self._embed_documents(texts)
            logger.info(f"Successfully embedded {len(texts)} documents")
            return embeddings
        except Exception as e:
            logger.error(f"Error embedding documents: {e}", exc_info=True)
            raise EmbeddingException(f"ドキュメント埋め込み中にエラーが発生しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })
    
    @retry(retry_key="EMBEDDING")
    @timeout(timeout_key="EMBEDDING")
    def embed_query(self, text: str) -> List[float]:
        """
        クエリテキストを埋め込む（タイムアウトとリトライ付き）
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        try:
            logger.info(f"Embedding query with {self.model_name}: {text[:30]}...")
            embedding = self._embed_query(text)
            logger.info("Successfully embedded query")
            return embedding
        except Exception as e:
            logger.error(f"Error embedding query: {e}", exc_info=True)
            raise EmbeddingException(f"クエリ埋め込み中にエラーが発生しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })
    
    @async_retry(retry_key="EMBEDDING")
    @async_timeout(timeout_key="EMBEDDING")
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを非同期で埋め込む（タイムアウトとリトライ付き）
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        try:
            logger.info(f"Async embedding {len(texts)} documents with {self.model_name}")
            embeddings = await self._aembed_documents(texts)
            logger.info(f"Successfully async embedded {len(texts)} documents")
            return embeddings
        except Exception as e:
            logger.error(f"Error async embedding documents: {e}", exc_info=True)
            raise EmbeddingException(f"ドキュメント非同期埋め込み中にエラーが発生しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })
    
    @async_retry(retry_key="EMBEDDING")
    @async_timeout(timeout_key="EMBEDDING")
    async def aembed_query(self, text: str) -> List[float]:
        """
        クエリテキストを非同期で埋め込む（タイムアウトとリトライ付き）
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        try:
            logger.info(f"Async embedding query with {self.model_name}: {text[:30]}...")
            embedding = await self._aembed_query(text)
            logger.info("Successfully async embedded query")
            return embedding
        except Exception as e:
            logger.error(f"Error async embedding query: {e}", exc_info=True)
            raise EmbeddingException(f"クエリ非同期埋め込み中にエラーが発生しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })


class HuggingFaceEmbeddingModel(EmbeddingModel):
    """HuggingFace埋め込みモデル"""
    
    def _setup_model(self) -> None:
        """HuggingFace埋め込みモデルの設定"""
        try:
            self.model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                **self.extra_params
            )
            logger.info(f"Successfully initialized HuggingFace embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error initializing HuggingFace embedding model: {e}", exc_info=True)
            self.model = None
            raise EmbeddingException(f"HuggingFace埋め込みモデルの初期化に失敗しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })
    
    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        HuggingFace埋め込みモデルを使用して複数のテキストを埋め込む
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        if self.model is None:
            raise EmbeddingException("HuggingFace埋め込みモデルが初期化されていません")
        
        return self.model.embed_documents(texts)
    
    def _embed_query(self, text: str) -> List[float]:
        """
        HuggingFace埋め込みモデルを使用してクエリテキストを埋め込む
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        if self.model is None:
            raise EmbeddingException("HuggingFace埋め込みモデルが初期化されていません")
        
        return self.model.embed_query(text)
    
    async def _aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        HuggingFace埋め込みモデルを使用して複数のテキストを非同期で埋め込む
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        if self.model is None:
            raise EmbeddingException("HuggingFace埋め込みモデルが初期化されていません")
        
        # HuggingFaceEmbeddingsは非同期メソッドを提供していないため、同期メソッドを使用
        # 実際の非同期実装では、別スレッドで実行するなどの工夫が必要
        import asyncio
        return await asyncio.to_thread(self.model.embed_documents, texts)
    
    async def _aembed_query(self, text: str) -> List[float]:
        """
        HuggingFace埋め込みモデルを使用してクエリテキストを非同期で埋め込む
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        if self.model is None:
            raise EmbeddingException("HuggingFace埋め込みモデルが初期化されていません")
        
        # HuggingFaceEmbeddingsは非同期メソッドを提供していないため、同期メソッドを使用
        import asyncio
        return await asyncio.to_thread(self.model.embed_query, text)


class SimplifiedEmbeddingModel(EmbeddingModel):
    """簡易的な埋め込みモデル（フォールバック用）"""
    
    def _setup_model(self) -> None:
        """簡易的な埋め込みモデルの設定"""
        # 特に初期化は必要ない
        self.model = None
        logger.info("Successfully initialized simplified embedding model")
    
    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        簡易的な方法で複数のテキストを埋め込む
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        try:
            logger.info(f"Creating simplified embeddings for {len(texts)} documents")
            
            result = []
            for text in texts:
                hash_obj = hashlib.md5(text.encode())
                hash_bytes = hash_obj.digest()
                
                vector = []
                for i in range(self.dimension):
                    byte_val = hash_bytes[i % len(hash_bytes)]
                    vector.append((byte_val / 128.0) - 1.0)
                
                result.append(vector)
            
            logger.info("Successfully created simplified embeddings")
            return result
        except Exception as e:
            logger.error(f"Error creating simplified embeddings: {e}", exc_info=True)
            return [[0.0] * self.dimension for _ in range(len(texts))]
    
    def _embed_query(self, text: str) -> List[float]:
        """
        簡易的な方法でクエリテキストを埋め込む
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        try:
            logger.info(f"Creating simplified embedding for query: {text[:30]}...")
            # 単一のテキストに対する埋め込みを生成
            result = self._embed_documents([text])[0]
            logger.info("Successfully created simplified query embedding")
            return result
        except Exception as e:
            logger.error(f"Error creating simplified query embedding: {e}", exc_info=True)
            # エラーが発生した場合は、ダミーのベクトルを返す
            return [0.0] * self.dimension
    
    async def _aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        簡易的な方法で複数のテキストを非同期で埋め込む
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        # 簡易的な実装では同期メソッドを使用
        import asyncio
        return await asyncio.to_thread(self._embed_documents, texts)
    
    async def _aembed_query(self, text: str) -> List[float]:
        """
        簡易的な方法でクエリテキストを非同期で埋め込む
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        # 簡易的な実装では同期メソッドを使用
        import asyncio
        return await asyncio.to_thread(self._embed_query, text)


class EmbeddingModelFactory:
    """埋め込みモデルのファクトリークラス"""
    
    @staticmethod
    def create(
        model_type: str = "huggingface",
        model_name: Optional[str] = None,
        dimension: int = 384,
        **kwargs
    ) -> EmbeddingModel:
        """
        埋め込みモデルを作成する
        
        Args:
            model_type: モデルの種類 ("huggingface" または "simplified")
            model_name: モデル名
            dimension: 埋め込みベクトルの次元数
            **kwargs: その他のパラメータ
            
        Returns:
            埋め込みモデル
        """
        if model_type.lower() == "huggingface":
            model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"
            try:
                return HuggingFaceEmbeddingModel(model_name, dimension, **kwargs)
            except Exception as e:
                logger.warning(f"Failed to initialize HuggingFace embedding model: {e}. Falling back to simplified model.")
                return SimplifiedEmbeddingModel("simplified", dimension, **kwargs)
        elif model_type.lower() == "simplified":
            return SimplifiedEmbeddingModel("simplified", dimension, **kwargs)
        else:
            raise ValueError(f"Unsupported embedding model type: {model_type}")
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> EmbeddingModel:
        """
        設定から埋め込みモデルを作成する
        
        Args:
            config: 埋め込みモデルの設定
            
        Returns:
            埋め込みモデル
        """
        model_type = config.get("model_type", "huggingface")
        model_name = config.get("model_name")
        dimension = config.get("dimension", 384)
        
        # その他のパラメータを抽出
        kwargs = {k: v for k, v in config.items() if k not in ["model_type", "model_name", "dimension"]}
        
        return EmbeddingModelFactory.create(model_type, model_name, dimension, **kwargs)
    
    @staticmethod
    def create_default() -> EmbeddingModel:
        """
        デフォルトの埋め込みモデルを作成する
        
        Returns:
            埋め込みモデル
        """
        # 環境変数から設定を取得
        model_type = os.environ.get("EMBEDDING_MODEL_TYPE", "huggingface")
        model_name = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        dimension = int(os.environ.get("EMBEDDING_DIMENSION", "384"))
        
        return EmbeddingModelFactory.create(model_type, model_name, dimension)


# LangChain Embeddings互換のラッパークラス
class EmbeddingModelWrapper(Embeddings):
    """LangChain Embeddings互換のラッパークラス"""
    
    def __init__(self, model: EmbeddingModel):
        """
        ラッパークラスの初期化
        
        Args:
            model: 埋め込みモデル
        """
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを埋め込む
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        return self.model.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """
        クエリテキストを埋め込む
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        return self.model.embed_query(text)
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        複数のテキストを非同期で埋め込む
        
        Args:
            texts: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        return await self.model.aembed_documents(texts)
    
    async def aembed_query(self, text: str) -> List[float]:
        """
        クエリテキストを非同期で埋め込む
        
        Args:
            text: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        return await self.model.aembed_query(text)
