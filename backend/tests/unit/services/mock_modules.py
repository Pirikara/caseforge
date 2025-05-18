"""
テスト用のモックモジュール
"""
import sys
from unittest.mock import MagicMock

class MockEmbeddings:
    pass

class MockDocument:
    def __init__(self, page_content="", metadata=None):
        self.page_content = str(page_content) if page_content is not None else ""
        self.metadata = metadata or {}
        
    def __repr__(self):
        return f"Document(page_content={self.page_content}, metadata={self.metadata})"

class MockVectorStore:
    pass

class MockFAISS(MockVectorStore):
    @classmethod
    def from_documents(cls, documents, embedding):
        mock = cls()
        mock.documents = documents
        mock.embedding = embedding
        return mock
    
    def save_local(self, path):
        pass

sys.modules['langchain'] = MagicMock()
sys.modules['langchain_core'] = MagicMock()
sys.modules['langchain_core.documents'] = MagicMock()
sys.modules['langchain_core.documents'].Document = MockDocument

sys.modules['langchain_core'] = MagicMock()
sys.modules['langchain_core.embeddings'] = MagicMock()
sys.modules['langchain_core.embeddings'].Embeddings = MockEmbeddings
sys.modules['langchain_core.prompts'] = MagicMock()
sys.modules['langchain_core.prompts'].ChatPromptTemplate = MagicMock()
sys.modules['langchain_core.output_parsers'] = MagicMock()
sys.modules['langchain_core.runnables'] = MagicMock()
sys.modules['langchain_core.language_models'] = MagicMock()

sys.modules['langchain_community'] = MagicMock()
sys.modules['langchain_community.vectorstores'] = MagicMock()
sys.modules['langchain_community.vectorstores'].FAISS = MockFAISS
sys.modules['langchain_community.vectorstores.base'] = MagicMock()
sys.modules['langchain_community.vectorstores.base'].VectorStore = MockVectorStore
sys.modules['langchain_community.chat_models'] = MagicMock()
sys.modules['langchain_community.llms'] = MagicMock()

sys.modules['langchain_huggingface'] = MagicMock()
sys.modules['langchain_huggingface.embeddings'] = MagicMock()
sys.modules['langchain_huggingface'].HuggingFaceEmbeddings = MockEmbeddings

sys.modules['langchain_openai'] = MagicMock()
sys.modules['langchain_openai.chat_models'] = MagicMock()
sys.modules['langchain_openai.llms'] = MagicMock()
