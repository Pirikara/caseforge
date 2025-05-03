from typing import List
import os
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
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

class EmbeddingFunctionForCaseforge(Embeddings):
    """
    DBで使用するための埋め込み関数
    """
    def __init__(self):
        """
        簡易的な埋め込み関数を初期化
        HuggingFaceモデルのロードに問題があるため、簡易的な代替手段を使用
        """
        try:
            logger.info("Using simplified embedding function instead of HuggingFace model")
            self.embedder = None
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
        複数のドキュメントを埋め込む - 簡易的な実装
        
        Args:
            input: 埋め込むテキストのリスト
            
        Returns:
            埋め込みベクトルのリスト
        """
        try:
            logger.info(f"Creating simplified embeddings for {len(input)} documents")
            import hashlib
            
            result = []
            for text in input:
                hash_obj = hashlib.md5(text.encode())
                hash_bytes = hash_obj.digest()
                
                vector = []
                for i in range(384):
                    byte_val = hash_bytes[i % len(hash_bytes)]
                    vector.append((byte_val / 128.0) - 1.0)
                
                result.append(vector)
            
            logger.info("Successfully created simplified embeddings")
            return result
        except Exception as e:
            logger.error(f"Error creating simplified embeddings: {e}", exc_info=True)
            return [[0.0] * 384 for _ in range(len(input))]
    
    def embed_query(self, input: str) -> List[float]:
        """
        クエリを埋め込む - 簡易的な実装
        
        Args:
            input: 埋め込むクエリテキスト
            
        Returns:
            埋め込みベクトル
        """
        try:
            logger.info(f"Creating simplified embedding for query: {input[:30]}...")
            # 単一のテキストに対する埋め込みを生成
            result = self.embed_documents([input])[0]
            logger.info("Successfully created simplified query embedding")
            return result
        except Exception as e:
            logger.error(f"Error creating simplified query embedding: {e}", exc_info=True)
            # エラーが発生した場合は、ダミーのベクトルを返す
            return [0.0] * 384

def index_schema(project_id: str, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    """
    try:
        logger.info(f"Indexing schema for project {project_id}: {path}")
        
        # 1. スキーマファイルのロード
        logger.info("Step 1: Loading OpenAPI schema file")
        loader = OpenAPILoader(path)
        docs = loader.load()
        logger.info(f"Successfully loaded schema file with {len(docs)} documents")
        
        # 2. 埋め込み関数の初期化
        logger.info("Step 2: Initializing embedding function")
        embedding_function = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info("Successfully initialized embedding function")
        
        # 3. FAISSへのドキュメント埋め込み
        logger.info("Step 3: Embedding documents into FAISS")
        try:
            # タイムアウト処理を追加
            import signal
            
            class TimeoutException(Exception):
                pass
            
            def timeout_handler(signum, frame):
                raise TimeoutException("FAISS processing timed out")
            
            # 30秒のタイムアウトを設定
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            try:
                vectordb = FAISS.from_documents(docs, embedding_function)
                # タイムアウトを解除
                signal.alarm(0)
                logger.info("Successfully embedded documents into FAISS")
                
                # 4. ベクトルDBの保存
                logger.info("Step 4: Saving vector database")
                
                # 永続化されるディレクトリにベクトルDBを保存
                data_dir = os.environ.get("DATA_DIR", "/app/data")
                save_dir = f"{data_dir}/faiss/{project_id}"
                
                logger.info(f"Saving vector database to {save_dir}")
                os.makedirs(save_dir, exist_ok=True)  # プロジェクトIDを含むディレクトリを作成
                logger.info(f"Created directory: {save_dir}")
                
                try:
                    vectordb.save_local(save_dir)
                    logger.info(f"Successfully saved vector database to {save_dir}")
                    
                    # 互換性のために/tmpにもシンボリックリンクを作成
                    tmp_dir = f"/tmp/faiss/{project_id}"
                    os.makedirs(os.path.dirname(tmp_dir), exist_ok=True)
                    
                    # 既存のシンボリックリンクや古いディレクトリを削除
                    if os.path.exists(tmp_dir):
                        if os.path.islink(tmp_dir):
                            os.unlink(tmp_dir)
                        else:
                            import shutil
                            shutil.rmtree(tmp_dir)
                    
                    # 新しいシンボリックリンクを作成
                    os.symlink(save_dir, tmp_dir)
                    logger.info(f"Created symbolic link from {tmp_dir} to {save_dir}")
                except Exception as save_error:
                    logger.error(f"Error saving vector database to {save_dir}: {save_error}", exc_info=True)
                    raise
                
                logger.info(f"Successfully indexed schema for project {project_id}")
            except TimeoutException:
                logger.warning("FAISS processing timed out after 30 seconds")
                # タイムアウトした場合は、処理を続行
                logger.warning("Continuing without FAISS indexing")
            finally:
                # 念のため、タイムアウトを解除
                signal.alarm(0)
                
        except Exception as e:
            logger.error(f"Error in FAISS processing: {e}", exc_info=True)
            # FAISSの処理でエラーが発生した場合、代替処理を実行
            logger.warning("Attempting to continue without FAISS indexing")
            
    except Exception as e:
        logger.error(f"Error indexing schema for project {project_id}: {e}", exc_info=True)
        # エラーを記録するが、処理は続行する（スキーマのインデックス作成に失敗しても、他の処理は続行できるようにする）
        logger.warning("Schema indexing failed, but continuing with other operations")
