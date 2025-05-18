import os
from langchain_community.vectorstores import FAISS
from app.logging_config import logger
from .chunker import OpenAPISchemaChunker
from app.utils.path_manager import path_manager

def index_schema(project_id: str, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    """
    try:
        logger.info(f"Indexing schema for project {project_id}: {path}")

        # 1. スキーマファイルのロードとチャンク化
        logger.info("Step 1: Loading, parsing, and chunking OpenAPI schema file")
        chunker = OpenAPISchemaChunker(path)
        docs = chunker.get_documents()
        logger.info(f"Successfully chunked schema file into {len(docs)} documents")

        if not docs:
            logger.warning(f"No documents generated for schema {path}. Skipping indexing.")
            return

        # 2. ベクトルDBマネージャーの初期化
        logger.info("Step 2: Initializing vector database manager")
        from app.services.vector_db.manager import VectorDBManagerFactory
        
        # プロジェクト固有のベクトルDBマネージャーを作成
        vector_db_manager = VectorDBManagerFactory.create_default(project_id)
        
        # 3. ドキュメントをベクトルDBに追加
        logger.info("Step 3: Adding documents to vector database")
        try:
            # ドキュメントを追加（タイムアウトとリトライ機構は内部で処理）
            vector_db_manager.add_documents(docs)
            logger.info(f"Successfully added {len(docs)} documents to vector database")
            
            # 4. 互換性のために/tmpにもシンボリックリンクを作成（FAISSの場合）
            if isinstance(vector_db_manager.vectordb, FAISS) and vector_db_manager.persist_directory:
                save_dir = vector_db_manager.persist_directory
                tmp_dir = path_manager.get_faiss_dir(project_id, temp=True)
                
                path_manager.ensure_dir(os.path.dirname(str(tmp_dir)))
                
                # 既存のシンボリックリンクや古いディレクトリを削除
                if path_manager.exists(tmp_dir):
                    if os.path.islink(str(tmp_dir)):
                        os.unlink(str(tmp_dir))
                    else:
                        import shutil
                        shutil.rmtree(str(tmp_dir))
                
                # 新しいシンボリックリンクを作成
                os.symlink(save_dir, str(tmp_dir))
                logger.info(f"Created symbolic link from {tmp_dir} to {save_dir}")
            
            logger.info(f"Successfully indexed schema for project {project_id}")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}", exc_info=True)
            logger.warning("Continuing without vector database indexing")

    except Exception as e:
        logger.error(f"Error in vector database processing: {e}", exc_info=True)
        logger.warning("Attempting to continue without vector database indexing")