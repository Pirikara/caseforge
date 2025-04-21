from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

class OpenAPILoader:
    def __init__(self, path: str):
        self.path = path

    def load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": self.path})]

class ChromaEmbeddingFunction:
    def __init__(self):
        self.embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(input)
    
    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(input)

def index_schema(project_id: str, path: str):
    loader = OpenAPILoader(path)
    docs = loader.load()

    vectordb = Chroma(
        collection_name=project_id,
        embedding_function=ChromaEmbeddingFunction(),
        persist_directory="/chroma/.chroma",
    )

    vectordb.add_documents(docs)
    vectordb.persist()