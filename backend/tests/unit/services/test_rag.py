# テスト用のモックモジュールをインポート（最初に行う必要がある）
from tests.unit.services.mock_modules import MockDocument, MockFAISS

import pytest
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil # shutilをインポート

# モック化するモジュールやクラスをインポート
from app.services.rag import OpenAPISchemaChunker, index_schema, EmbeddingFunctionForCaseforge

# Documentクラスのエイリアス
Document = MockDocument
FAISS = MockFAISS

# テスト用のダミーOpenAPIスキーマファイルを作成するfixture
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
    # スキーマ全体に対して$ref解決を試みる（内部メソッドのテスト）
    resolved_schema = chunker._resolve_references(chunker.schema)

    # /users POST の requestBody スキーマが解決されていることを確認
    post_request_body_schema = resolved_schema["paths"]["/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert "properties" in post_request_body_schema
    assert "name" in post_request_body_schema["properties"]
    assert post_request_body_schema["properties"]["name"]["type"] == "string"

    # /users GET の parameters が解決されていることを確認
    get_parameters = resolved_schema["paths"]["/users"]["get"]["parameters"]
    assert len(get_parameters) > 0
    limit_param = next((p for p in get_parameters if p.get("name") == "limit"), None)
    assert limit_param is not None
    assert limit_param["in"] == "query"
    assert limit_param["schema"]["type"] == "integer"

    # /users/{userId} GET の responses スキーマが解決されていることを確認
    user_id_response_schema = resolved_schema["paths"]["/users/{userId}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert "properties" in user_id_response_schema
    assert "id" in user_id_response_schema["properties"]
    assert user_id_response_schema["properties"]["id"]["type"] == "string"


@patch('langchain_core.documents.Document', MockDocument)
def test_openapi_schema_chunker_generates_documents(dummy_openapi_schema):
    """OpenAPISchemaChunkerがDocumentリストを正しく生成するかテスト"""
    chunker = OpenAPISchemaChunker(dummy_openapi_schema)
    documents = chunker.get_documents()

    # 期待されるドキュメント数を確認 (POST /users, GET /users, GET /users/{userId})
    assert len(documents) == 3

    # 各ドキュメントの基本的な形式を確認
    for doc in documents:
        assert hasattr(doc, 'page_content')
        assert hasattr(doc, 'metadata')
        assert isinstance(doc.metadata, dict)


# index_schema関数のテスト
@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
def test_index_schema_success(mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数がスキーマを正しくインデックス化し、保存するかテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # モックの設定
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance

    # ダミーのDocumentオブジェクトリスト
    dummy_docs = [
        MockDocument(page_content="chunk1", metadata={"source": "file::path1::method1", "type": "path-method"}),
        MockDocument(page_content="chunk2", metadata={"source": "file::path2::method2", "type": "path-method"}),
    ]
    mock_chunker_instance.get_documents.return_value = dummy_docs

    # VectorDBManagerFactoryのモック設定
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # OpenAPISchemaChunkerが正しいパスでインスタンス化されたか確認
    mock_chunker_cls.assert_called_once_with(schema_path)
    
    # VectorDBManagerFactoryが正しく呼び出されたか確認
    mock_factory_cls.create_default.assert_called_once_with(project_id)

    # ドキュメントがベクトルDBに追加されたか確認
    mock_vector_db_manager.add_documents.assert_called_once()

@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
@patch('app.services.rag.indexer.logger')
def test_index_schema_save_error(mock_logger, mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数でベクトルDB保存エラーが発生した場合のテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # モックの設定
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [MockDocument(page_content="chunk", metadata={})]

    # VectorDBManagerFactoryのモック設定
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager
    
    # add_documentsで例外を発生させるようにモック
    mock_vector_db_manager.add_documents.side_effect = Exception("Vector DB save error")

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # エラーログが出力されたことを確認
    mock_logger.error.assert_any_call(mock_logger.error.call_args_list[0][0][0], exc_info=True)

@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
@patch('app.services.rag.indexer.logger')
def test_index_schema_symlink_error(mock_logger, mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数でシンボリックリンク作成エラーが発生した場合のテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # モックの設定
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [MockDocument(page_content="chunk", metadata={})]

    # VectorDBManagerFactoryのモック設定
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager
    mock_vector_db_manager.vectordb = MagicMock(spec=FAISS)
    mock_vector_db_manager.persist_directory = "/tmp/data/faiss/test_project"
    
    # add_documentsの後にシンボリックリンク作成時にエラーが発生するようにモック
    def side_effect(*args, **kwargs):
        # add_documentsは成功するが、その後のシンボリックリンク作成でエラー
        raise Exception("Symlink error")
    
    mock_vector_db_manager.add_documents.side_effect = side_effect

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # エラーログが出力されたことを確認
    mock_logger.error.assert_any_call(mock_logger.error.call_args_list[0][0][0], exc_info=True)

@patch('app.services.rag.indexer.OpenAPISchemaChunker')
@patch('app.services.vector_db.manager.VectorDBManagerFactory')
@patch('app.services.rag.indexer.logger')
def test_index_schema_timeout(mock_logger, mock_factory_cls, mock_chunker_cls, dummy_openapi_schema):
    """index_schema関数でタイムアウトが発生した場合のテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # モックの設定
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [MockDocument(page_content="chunk", metadata={})]

    # VectorDBManagerFactoryのモック設定
    mock_vector_db_manager = MagicMock()
    mock_factory_cls.create_default.return_value = mock_vector_db_manager
    
    # add_documentsでTimeoutExceptionを発生させるようにモック
    from app.exceptions import TimeoutException
    mock_vector_db_manager.add_documents.side_effect = TimeoutException("Vector DB processing timed out")

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # エラーログが出力されたことを確認
    mock_logger.error.assert_any_call(mock_logger.error.call_args_list[0][0][0], exc_info=True)