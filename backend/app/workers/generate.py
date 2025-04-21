import os
import json
from celery import shared_task
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from app.services.rag import ChromaEmbeddingFunction

@shared_task
def generate_tests_task(project_id: str):
    # 1. RAG — 最も関連するチャンクを取得
    vectordb = Chroma(
        collection_name=project_id,
        embedding_function=ChromaEmbeddingFunction(),
        persist_directory="/chroma/.chroma",
    )

    retriever = vectordb.as_retriever()
    prompt = PromptTemplate.from_template("""
You are an automated QA engineer. Based on the following OpenAPI schema context, generate a list of test cases (in JSON) that test both functional and security aspects.

Context:
{context}

Return JSON format:
[
  {{"description": "...", "method": "GET", "path": "/api/...", "expected_status": 200}},
  ...
]
""")

    qa_chain = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(
            base_url="http://192.168.2.101:1234/v1",
            api_key="not-needed",
            model_name="Hermes-3-Llama-3.1-8B-GGUF",
            temperature=0.2,
        ),
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt},
    )

    result = qa_chain.run("テストケースを出力して")

    os.makedirs(f"/code/data/tests/{project_id}", exist_ok=True)
    with open(f"/code/data/tests/{project_id}/tests.json", "w") as f:
        json.dump(result, f, indent=2)