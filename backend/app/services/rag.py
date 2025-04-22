from typing import List, Dict, Any, Optional
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from chromadb.utils.embedding_functions import EmbeddingFunction
from app.config import settings
from app.logging_config import logger

class OpenAPILoader:
    """
    OpenAPIスキーマファイルをロードするためのローダー
    """
    def __init__(self, path: str):
        """
        Args:
            path: OpenAPIスキーマファイルのパス
        """
        self.path = path

    def load(self) -> List[Document]:
        """
        ファイルを読み込み、Documentオブジェクトのリストを返す
        
        Returns:
            Documentオブジェクトのリスト
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"Loaded OpenAPI schema from {self.path}")
            return [Document(page_content=content, metadata={"source": self.path})]
        except Exception as e:
            logger.error(f"Error loading OpenAPI schema from {self.path}: {e}")
            raise

class ChromaEmbeddingFunction(EmbeddingFunction):
    """
    ChromaDBで使用するための埋め込み関数
    """
    def __init__(self):
        """
        HuggingFaceの埋め込みモデルを初期化
        """
        try:
            self.embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            logger.debug("Initialized HuggingFace embedding model")
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            raise

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        ChromaDBのEmbeddingFunction用の呼び出しメソッド
        
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
            return self.embedder.embed_documents(input)
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise
    
    def embed_query(self, input: str) -> List[float]:
        """
        クエリを埋め込む
        
        Args:
            input: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        try:
            return self.embedder.embed_query(input)
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise

def index_schema(project_id: str, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    
    Args:
        project_id: プロジェクトID
        path: OpenAPIスキーマファイルのパス
    """
    try:
        logger.info(f"Indexing schema for project {project_id}: {path}")
        loader = OpenAPILoader(path)
        docs = loader.load()
        logger.debug(f"Loaded {len(docs)} documents")

        vectordb = Chroma(
            collection_name=project_id,
            embedding_function=ChromaEmbeddingFunction(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )

        vectordb.add_documents(docs)
        vectordb.persist()
        logger.info(f"Successfully indexed schema for project {project_id}")
    except Exception as e:
        logger.error(f"Error indexing schema for project {project_id}: {e}")
        raise