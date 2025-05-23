import os
from app.logging_config import logger
from .chunker import OpenAPISchemaChunker
from app.utils.path_manager import path_manager

def index_schema(service_id: str, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    """
    try:
        logger.info(f"Indexing schema for service {service_id}: {path}")

        logger.info("Step 1: Loading, parsing, and chunking OpenAPI schema file")
        chunker = OpenAPISchemaChunker(path)
        docs = chunker.get_documents()
        logger.info(f"Successfully chunked schema file into {len(docs)} documents")

        if not docs:
            logger.warning(f"No documents generated for schema {path}. Skipping indexing.")
            return

        logger.info("Step 2: Initializing vector database manager")
        from app.services.vector_db.manager import VectorDBManagerFactory
        
        vector_db_manager = VectorDBManagerFactory.create_default(service_id)
        
        logger.info("Step 3: Adding documents to vector database")
        try:
            vector_db_manager.add_documents(docs)
            logger.info(f"Successfully added {len(docs)} documents to vector database")
            
            logger.info(f"Successfully indexed schema for service {service_id}")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}", exc_info=True)
            logger.warning("Continuing without vector database indexing")

    except Exception as e:
        logger.error(f"Error in vector database processing: {e}", exc_info=True)
        logger.warning("Attempting to continue without vector database indexing")
