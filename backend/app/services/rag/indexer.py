import os
from app.logging_config import logger
from .chunker import OpenAPISchemaChunker
from app.utils.path_manager import path_manager

def index_schema(id: int, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    """
    try:

        chunker = OpenAPISchemaChunker(path)
        docs = chunker.get_documents()

        if not docs:
            logger.warning(f"No documents generated for schema {path}. Skipping indexing.")
            return

        from app.services.vector_db.manager import VectorDBManagerFactory
        
        vector_db_manager = VectorDBManagerFactory.create_default(id)
        
        try:
            vector_db_manager.add_documents(docs)
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}", exc_info=True)
            logger.warning("Continuing without vector database indexing")

    except Exception as e:
        logger.error(f"Error in vector database processing: {e}", exc_info=True)
        logger.warning("Attempting to continue without vector database indexing")
