from typing import List
from langchain_core.embeddings import Embeddings
from app.logging_config import logger

class EmbeddingFunctionForCaseforge(Embeddings):
    """
    DBで使用するための埋め込み関数（互換性のために残す）
    内部では新しい埋め込みモデルを使用します。
    """
    def __init__(self):
        """
        簡易的な埋め込み関数を初期化
        """
        try:
            logger.info("Using simplified embedding function from new implementation")
            from app.services.vector_db.embeddings import EmbeddingModelFactory
            self.model = EmbeddingModelFactory.create(model_type="simplified")
            logger.info("Successfully initialized simplified embedding function")
        except Exception as e:
            logger.error(f"Error initializing simplified embedding function: {e}", exc_info=True)
            raise

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        DBのEmbeddingFunction用の呼び出しメソッド

        Args:
            input: 埋め込むテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        return self.embed_documents(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        """
        複数のドキュメントを埋め込む

        Args:
            input: 埋め込むテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        try:
            return self.model.embed_documents(input)
        except Exception as e:
            logger.error(f"Error creating embeddings: {e}", exc_info=True)
            return [[0.0] * 384 for _ in range(len(input))]

    def embed_query(self, input: str) -> List[float]:
        """
        クエリを埋め込む

        Args:
            input: 埋め込むクエリテキスト

        Returns:
            埋め込みベクトル
        """
        try:
            return self.model.embed_query(input)
        except Exception as e:
            logger.error(f"Error creating query embedding: {e}", exc_info=True)
            return [0.0] * 384