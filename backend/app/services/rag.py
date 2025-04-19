from langchain.document_loaders import OpenAPILoader
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

async def index_schema(project_id: str, path: str):
    loader = OpenAPILoader(path)
    docs = loader.load()
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma(collection_name=project_id, embedding_function=embeddings, persist_directory="/chroma/.chroma")
    vectordb.add_documents(docs)