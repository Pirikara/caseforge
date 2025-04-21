from app.workers import celery_app
from app.services.teststore import save_testcases
from app.services.rag import ChromaEmbeddingFunction
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.llms import LlamaCpp
import json

@celery_app.task
def generate_tests_task(project_id: str):
    vectordb = Chroma(
        collection_name=project_id,
        embedding_function=ChromaEmbeddingFunction(),
        persist_directory="/chroma/.chroma",
    )
    context_docs = vectordb.as_retriever(search_kwargs={"k": 10}).invoke("Generate test cases")
    context = "".join(d.page_content[:800] for d in context_docs)

    # llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.2)
    llm = ChatOpenAI(
        model_name="Hermes-3-Llama-3.1-8B-GGUF",
        openai_api_base="http://192.168.2.101:1234/v1",
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
    except json.JSONDecodeError:
        cases = []

    save_testcases(project_id, cases)
    return {"status": "completed", "count": len(cases)}
