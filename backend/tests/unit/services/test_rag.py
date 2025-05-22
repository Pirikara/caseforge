import pytest
from app.services.rag.chunker import OpenAPISchemaChunker
from app.services.rag.indexer import index_schema
from tests.unit.services.mock_modules import MockDocument
from unittest.mock import patch, MagicMock

Document = MockDocument

@pytest.fixture
def dummy_openapi_schema(tmp_path):
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    post:
      summary: Create a new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
      responses:
        '201':
          description: User created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserId'
    get:
      summary: Get list of users
      parameters:
        - $ref: '#/components/parameters/LimitParam'
      responses:
        '200':
          description: List of users
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
  /users/{userId}:
    get:
      summary: Get user by ID
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: User details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'

components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
    UserId:
      type: object
      properties:
        id:
          type: string
  parameters:
    LimitParam:
      name: limit
      in: query
      required: false
      schema:
        type: integer
        format: int32
        default: 10
"""
    schema_file = tmp_path / "openapi.yaml"
    schema_file.write_text(schema_content)
    return str(schema_file)

def test_openapi_schema_chunker_loads_schema(dummy_openapi_schema):
    """OpenAPISchemaChunkerがスキーマファイルを正しく読み込むかテスト"""
    chunker = OpenAPISchemaChunker(dummy_openapi_schema)
    assert isinstance(chunker.schema, dict)
    assert "openapi" in chunker.schema
    assert chunker.schema["info"]["title"] == "Test API"

def test_openapi_schema_chunker_resolves_references(dummy_openapi_schema):
    """OpenAPISchemaChunkerが$refを正しく解決するかテスト"""
    chunker = OpenAPISchemaChunker(dummy_openapi_schema)
    # Access the resolved schema directly from the chunker instance
    resolved_schema = chunker.resolved_schema

    # Assert that resolved_schema exists and is a dictionary
    assert resolved_schema is not None
    assert isinstance(resolved_schema, dict)

    # Further detailed assertions about the resolved structure are handled in test_endpoint_parser.py
    # This test primarily confirms that OpenAPISchemaChunker uses the parser correctly
    # You could add basic checks here if needed, e.g., checking for the presence of 'paths'
    assert "paths" in resolved_schema
    assert "/users" in resolved_schema["paths"]
    assert "post" in resolved_schema["paths"]["/users"]


@patch('langchain_core.documents.Document', MockDocument)
def test_openapi_schema_chunker_generates_documents(dummy_openapi_schema):
    """OpenAPISchemaChunkerがDocumentリストを正しく生成するかテスト"""
    chunker = OpenAPISchemaChunker(dummy_openapi_schema)
    documents = chunker.get_documents()

    assert len(documents) == 3

    for doc in documents:
        assert hasattr(doc, 'page_content')
        assert hasattr(doc, 'metadata')
        assert isinstance(doc.metadata, dict)


@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
def test_index_schema_success(mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数がスキーマを正しくインデックス化し、保存するかテスト"""
    service_id = "test_service"
    schema_path = dummy_openapi_schema

    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance

    dummy_docs = [
        MockDocument(page_content="chunk1", metadata={"source": "file::path1::method1", "type": "path-method"}),
        MockDocument(page_content="chunk2", metadata={"source": "file::path2::method2", "type": "path-method"}),
    ]
    mock_chunker_instance.get_documents.return_value = dummy_docs

    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager

    index_schema(service_id, schema_path)

    mock_chunker_cls.assert_called_once_with(schema_path)
    mock_factory_cls.create_default.assert_called_once_with(service_id, db_type='pgvector')
    mock_vector_db_manager.add_documents.assert_called_once()

@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
@patch('app.services.rag.indexer.logger')
def test_index_schema_save_error(mock_logger, mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数でベクトルDB保存エラーが発生した場合のテスト"""
    service_id = "test_service"
    schema_path = dummy_openapi_schema

    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [MockDocument(page_content="chunk", metadata={})]
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager
    
    mock_vector_db_manager.add_documents.side_effect = Exception("Vector DB save error")

    index_schema(service_id, schema_path)

    mock_logger.error.assert_any_call(mock_logger.error.call_args_list[0][0][0], exc_info=True)

@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
@patch('app.services.rag.indexer.logger')
def test_index_schema_symlink_error(mock_logger, mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数でシンボリックリンク作成エラーが発生した場合のテスト"""
    service_id = "test_service"
    schema_path = dummy_openapi_schema

    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [MockDocument(page_content="chunk", metadata={})]
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager
    
    def side_effect(*args, **kwargs):
        raise Exception("Symlink error")
    
    mock_vector_db_manager.add_documents.side_effect = side_effect

    index_schema(service_id, schema_path)

    mock_logger.error.assert_any_call(mock_logger.error.call_args_list[0][0][0], exc_info=True)

@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
@patch('app.services.rag.indexer.logger')
def test_index_schema_timeout(mock_logger, mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数でタイムアウトが発生した場合のテスト"""
    service_id = "test_service"
    schema_path = dummy_openapi_schema

    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [MockDocument(page_content="chunk", metadata={})]
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager
    
    from app.exceptions import TimeoutException
    mock_vector_db_manager.add_documents.side_effect = TimeoutException("Vector DB processing timed out")

    index_schema(service_id, schema_path)

    mock_logger.error.assert_any_call(mock_logger.error.call_args_list[0][0][0], exc_info=True)
  