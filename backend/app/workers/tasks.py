from app.workers import celery_app
from app.services.teststore import save_testcases
from app.services.rag import ChromaEmbeddingFunction
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
import os
import logging
from app.config import settings

logger = logging.getLogger(__name__)

@celery_app.task
def generate_tests_task(project_id: str):
    """
    OpenAPIスキーマからテストケースを生成するCeleryタスク
    
    Args:
        project_id: プロジェクトID
        
    Returns:
        dict: 生成結果の情報
    """
    logger.info(f"Generating tests for project {project_id}")
    
    try:
        vectordb = Chroma(
            collection_name=project_id,
            embedding_function=ChromaEmbeddingFunction(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        
        context_docs = vectordb.as_retriever(search_kwargs={"k": 10}).invoke("Generate test cases")
        context = "".join(d.page_content[:800] for d in context_docs)
        
        # LLMの設定
        model_name = settings.LLM_MODEL_NAME
        api_base = settings.OPENAI_API_BASE
        
        llm = ChatOpenAI(
            model_name=model_name,
            openai_api_base=api_base,
            temperature=0.2,
        )
        
        prompt = ChatPromptTemplate.from_template(
            """You are an API QA expert. Using the following OpenAPI snippet:
{context}
Generate EXACTLY 3 diverse test cases in JSON array with keys: id, title, request (method, path, body?), expected (status), purpose (functional|boundary|authZ|fuzz). Return ONLY JSON."""
        )
        
        resp = (prompt | llm).invoke({"context": context}).content
        
        try:
            cases = json.loads(resp)
            logger.info(f"Successfully generated {len(cases)} test cases")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {resp}")
            cases = []
        
        save_testcases(project_id, cases)
        return {"status": "completed", "count": len(cases)}
        
    except Exception as e:
        logger.error(f"Error generating tests: {e}")
        return {"status": "error", "message": str(e)}
