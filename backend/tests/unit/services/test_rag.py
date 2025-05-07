import pytest
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil # shutilをインポート

# モック化するモジュールやクラスをインポート
from app.services.rag import OpenAPISchemaChunker, index_schema, EmbeddingFunctionForCaseforge
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

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


def test_openapi_schema_chunker_generates_documents(dummy_openapi_schema):
    """OpenAPISchemaChunkerがDocumentリストを正しく生成するかテスト"""
    chunker = OpenAPISchemaChunker(dummy_openapi_schema)
    documents = chunker.get_documents()

    # 期待されるドキュメント数を確認 (POST /users, GET /users, GET /users/{userId})
    assert len(documents) == 3

    # 各ドキュメントの形式と内容を確認
    for doc in documents:
        assert isinstance(doc.page_content, str)
        assert isinstance(doc.metadata, dict)
        assert "source" in doc.metadata
        assert "type" in doc.metadata
        assert doc.metadata["type"] == "path-method"
        assert "path" in doc.metadata
        assert "method" in doc.metadata

        # page_contentがYAMLとしてパース可能か確認
        chunk_data = yaml.safe_load(doc.page_content)
        assert isinstance(chunk_data, dict)
        assert "method" in chunk_data
        assert "path" in chunk_data

        # $refが解決されているか（簡易的なチェック）
        # Userスキーマが含まれているか確認
        if chunk_data["path"] == "/users" and chunk_data["method"] == "POST":
            assert "requestBody" in chunk_data
            assert "properties" in chunk_data["requestBody"]["content"]["application/json"]["schema"]
            assert "name" in chunk_data["requestBody"]["content"]["application/json"]["schema"]["properties"]
            assert "responses" in chunk_data
            assert "201" in chunk_data["responses"]
            assert "properties" in chunk_data["responses"]["201"]["content"]["application/json"]["schema"]
            assert "id" in chunk_data["responses"]["201"]["content"]["application/json"]["schema"]["properties"]

        if chunk_data["path"] == "/users" and chunk_data["method"] == "GET":
            assert "parameters" in chunk_data
            assert any(p.get("name") == "limit" for p in chunk_data["parameters"])
            assert "responses" in chunk_data
            assert "200" in chunk_data["responses"]
            assert "type" in chunk_data["responses"]["200"]["content"]["application/json"]["schema"]
            assert chunk_data["responses"]["200"]["content"]["application/json"]["schema"]["type"] == "array"
            assert "$ref" not in str(chunk_data["responses"]["200"]["content"]["application/json"]["schema"]) # 埋め込まれていることを確認

        if chunk_data["path"] == "/users/{userId}" and chunk_data["method"] == "GET":
            assert "parameters" in chunk_data
            assert any(p.get("name") == "userId" for p in chunk_data["parameters"])
            assert "responses" in chunk_data
            assert "200" in chunk_data["responses"]
            assert "properties" in chunk_data["responses"]["200"]["content"]["application/json"]["schema"]
            assert "name" in chunk_data["responses"]["200"]["content"]["application/json"]["schema"]["properties"]


# index_schema関数のテスト
@patch('app.services.rag.signal')
@patch('app.services.rag.logger')
@patch('app.services.rag.OpenAPISchemaChunker')
@patch('app.services.rag.HuggingFaceEmbeddings')
@patch('app.services.rag.FAISS')
@patch('shutil.rmtree')
@patch('app.services.rag.os.path.islink')
@patch('app.services.rag.os.unlink')
@patch('app.services.rag.os.path.exists')
@patch('app.services.rag.os.symlink')
@patch('app.services.rag.os.makedirs')
@patch('app.services.rag.os.environ')
def test_index_schema_success(mock_environ, mock_makedirs, mock_symlink, mock_exists, mock_unlink, mock_islink, mock_rmtree, mock_faiss_cls, mock_embedding_cls, mock_chunker_cls, mock_logger, mock_signal, dummy_openapi_schema, tmp_path):
    """index_schema関数がスキーマを正しくインデックス化し、保存するかテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # os.environ.get('DATA_DIR', '/app/data') が一時ディレクトリを返すようにモック
    mock_environ.get.return_value = str(tmp_path / "data")

    # モックの設定
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance

    # ダミーのDocumentオブジェクトリスト
    dummy_docs = [
        Document(page_content="chunk1", metadata={"source": "file::path1::method1", "type": "path-method"}),
        Document(page_content="chunk2", metadata={"source": "file::path2::method2", "type": "path-method"}),
    ]
    mock_chunker_instance.get_documents.return_value = dummy_docs

    mock_embedding_instance = MagicMock()
    mock_embedding_cls.return_value = mock_embedding_instance

    mock_faiss_instance = MagicMock()
    mock_faiss_cls.from_documents.return_value = mock_faiss_instance

    # os.path.existsのデフォルトの振る舞いを設定
    # /tmp/faiss/{project_id} が最初は存在し、削除後に存在しないように設定
    exists_calls = {}
    def exists_side_effect(path):
        if path == f"/tmp/faiss/{project_id}":
            # 最初の呼び出しではTrueを返し、それ以降はFalseを返す
            if path not in exists_calls:
                exists_calls[path] = 0
            exists_calls[path] += 1
            return exists_calls[path] == 1
        # 他のパスは常に存在すると仮定
        return True
    mock_exists.side_effect = exists_side_effect

    # signalモックの挙動を設定
    mock_signal.signal.return_value = None
    mock_signal.alarm.return_value = None

    # /tmp/faiss/{project_id} がシンボリックリンクであると仮定
    mock_islink.return_value = True

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # OpenAPISchemaChunkerが正しいパスでインスタンス化されたか確認
    mock_chunker_cls.assert_called_once_with(schema_path)
    # get_documentsが呼び出されたか確認
    mock_chunker_instance.get_documents.assert_called_once()

    # HuggingFaceEmbeddingsがインスタンス化されたか確認
    mock_embedding_cls.assert_called_once_with(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # FAISS.from_documentsが正しい引数で呼び出されたか確認
    mock_faiss_cls.from_documents.assert_called_once_with(dummy_docs, mock_embedding_instance)

    # 保存ディレクトリが作成されたか確認
    expected_save_dir = str(tmp_path / "data" / "faiss" / project_id)
    mock_makedirs.assert_any_call(expected_save_dir, exist_ok=True)

    # FAISS.save_localが正しいパスで呼び出されたか確認
    mock_faiss_instance.save_local.assert_called_once_with(expected_save_dir)

    # /tmpディレクトリの親ディレクトリが作成されたか確認
    expected_tmp_dir = f"/tmp/faiss/{project_id}"
    mock_makedirs.assert_any_call(os.path.dirname(expected_tmp_dir), exist_ok=True)

    # 既存の/tmpシンボリックリンクが存在するため、islinkとunlinkが呼ばれることを確認
    mock_exists.assert_any_call(expected_tmp_dir) # 存在チェックは行われる
    mock_islink.assert_called_once_with(expected_tmp_dir)
    os.unlink.assert_called_once_with(expected_tmp_dir)
    mock_rmtree.assert_not_called() # rmtreeは呼ばれない

    # signal.signalとsignal.alarmが呼ばれたことを確認
    mock_signal.signal.assert_called_once()
    mock_signal.alarm.assert_any_call(30)
    mock_signal.alarm.assert_any_call(0)

    # シンボリックリンクが正しく作成されたか確認
    mock_symlink.assert_called_once_with(expected_save_dir, expected_tmp_dir)


@patch('app.services.rag.os.environ')
@patch('app.services.rag.os.makedirs')
@patch('app.services.rag.os.symlink')
@patch('app.services.rag.os.path.exists')
@patch('app.services.rag.os.path.islink')
@patch('shutil.rmtree')
@patch('app.services.rag.FAISS')
@patch('app.services.rag.HuggingFaceEmbeddings')
@patch('app.services.rag.OpenAPISchemaChunker')
@patch('app.services.rag.logger')
@patch('app.services.rag.signal')
def test_index_schema_save_error(mock_signal, mock_logger, mock_chunker_cls, mock_embedding_cls, mock_faiss_cls, mock_rmtree, mock_islink, mock_exists, mock_symlink, mock_makedirs, mock_environ, dummy_openapi_schema, tmp_path):
    """index_schema関数でFAISS保存エラーが発生した場合のテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # os.environ.get('DATA_DIR', '/app/data') が一時ディレクトリを返すようにモック
    mock_environ.get.return_value = str(tmp_path / "data")

    # OpenAPISchemaChunkerとHuggingFaceEmbeddingsは正常に動作するようにモック
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [Document(page_content="chunk", metadata={})]
    mock_embedding_cls.return_value = MagicMock()

    mock_faiss_instance = MagicMock()
    mock_faiss_cls.from_documents.return_value = mock_faiss_instance

    # save_localで例外を発生させるようにモック
    mock_faiss_instance.save_local.side_effect = Exception("FAISS save error")

    # os.path.existsのデフォルトの振る舞いを設定
    mock_exists.side_effect = lambda path: path != f"/tmp/faiss/{project_id}"

    # signalモックの挙動を設定
    mock_signal.signal.return_value = None
    mock_signal.alarm.return_value = None

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # 保存エラーのログが出力されたことを確認
    # 外側のtry-exceptで捕捉されるため、ログメッセージが変わる
    mock_logger.error.assert_called_with('Error in FAISS processing: FAISS save error', exc_info=True) # Actualのログメッセージに合わせる
    # 最終的なエラーログは外側のtry-exceptで捕捉されたものになる
    # mock_logger.error.assert_called_with(f"Error indexing schema for project {project_id}: FAISS save error", exc_info=True) # この行は不要
    # 最終的な警告ログが出力されたことを確認
    mock_logger.warning.assert_called_with("Attempting to continue without FAISS indexing") # Actualのログメッセージに合わせる
    # signal.alarm(0) が呼ばれたことを確認 (finallyブロックの実行)
    mock_signal.alarm.assert_called_with(0)


@patch('app.services.rag.os.environ')
@patch('app.services.rag.os.makedirs')
@patch('app.services.rag.os.symlink')
@patch('app.services.rag.os.path.exists')
@patch('app.services.rag.os.path.islink')
@patch('shutil.rmtree')
@patch('app.services.rag.FAISS')
@patch('app.services.rag.HuggingFaceEmbeddings')
@patch('app.services.rag.OpenAPISchemaChunker')
@patch('app.services.rag.logger')
@patch('app.services.rag.signal')
def test_index_schema_symlink_error(mock_signal, mock_logger, mock_chunker_cls, mock_embedding_cls, mock_faiss_cls, mock_rmtree, mock_islink, mock_exists, mock_symlink, mock_makedirs, mock_environ, dummy_openapi_schema, tmp_path):
    """index_schema関数でシンボリックリンク作成エラーが発生した場合のテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # os.environ.get('DATA_DIR', '/app/data') が一時ディレクトリを返すようにモック
    mock_environ.get.return_value = str(tmp_path / "data")

    # OpenAPISchemaChunkerとHuggingFaceEmbeddingsは正常に動作するようにモック
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [Document(page_content="chunk", metadata={})]
    mock_embedding_cls.return_value = MagicMock()

    mock_faiss_instance = MagicMock()
    mock_faiss_cls.from_documents.return_value = mock_faiss_instance

    # save_localは正常に動作するようにモック
    mock_faiss_instance.save_local.return_value = None

    # os.path.existsのデフォルトの振る舞いを設定
    mock_exists.side_effect = lambda path: path != f"/tmp/faiss/{project_id}"

    # signalモックの挙動を設定
    mock_signal.signal.return_value = None
    mock_signal.alarm.return_value = None

    # os.symlinkで例外を発生させるようにモック
    mock_symlink.side_effect = Exception("Symlink error")

    # index_schema関数を実行
    index_schema(project_id, schema_path)

    # シンボリックリンクエラーのログが出力されたことを確認
    # 外側のtry-exceptで捕捉されるため、ログメッセージが変わる
    mock_logger.error.assert_called_with('Error in FAISS processing: Symlink error', exc_info=True) # Actualのログメッセージに合わせる
    # 最終的なエラーログは外側のtry-exceptで捕捉されたものになる
    # mock_logger.error.assert_called_with(f"Error indexing schema for project {project_id}: Symlink error", exc_info=True) # この行は不要
    # 最終的な警告ログが出力されたことを確認
    mock_logger.warning.assert_called_with("Attempting to continue without FAISS indexing") # Actualのログメッセージに合わせる
    # signal.alarm(0) が呼ばれたことを確認 (finallyブロックの実行)
    mock_signal.alarm.assert_called_with(0)

@patch('app.services.rag.os.environ')
@patch('app.services.rag.os.makedirs')
@patch('app.services.rag.os.symlink')
@patch('app.services.rag.os.path.exists')
@patch('app.services.rag.os.path.islink')
@patch('shutil.rmtree')
@patch('app.services.rag.FAISS')
@patch('app.services.rag.HuggingFaceEmbeddings')
@patch('app.services.rag.OpenAPISchemaChunker')
@patch('app.services.rag.logger')
@patch('app.services.rag.signal')
def test_index_schema_timeout(mock_signal, mock_logger, mock_chunker_cls, mock_embedding_cls, mock_faiss_cls, mock_rmtree, mock_islink, mock_exists, mock_symlink, mock_makedirs, mock_environ, dummy_openapi_schema, tmp_path):
    """index_schema関数でタイムアウトが発生した場合のテスト"""
    project_id = "test_project"
    schema_path = dummy_openapi_schema

    # os.environ.get('DATA_DIR', '/app/data') が一時ディレクトリを返すようにモック
    mock_environ.get.return_value = str(tmp_path / "data")

    # OpenAPISchemaChunkerとHuggingFaceEmbeddingsは正常に動作するようにモック
    mock_chunker_instance = MagicMock()
    mock_chunker_cls.return_value = mock_chunker_instance
    mock_chunker_instance.get_documents.return_value = [Document(page_content="chunk", metadata={})]
    mock_embedding_cls.return_value = MagicMock()

    # FAISS.from_documentsでTimeoutExceptionを発生させるようにモック
    # rag.pyで定義されているTimeoutExceptionを使用
    from app.services.rag import TimeoutException
    mock_faiss_cls.from_documents.side_effect = TimeoutException("FAISS processing timed out")

    # signalモックの挙動を設定
    mock_signal.signal.return_value = None
    mock_signal.alarm.return_value = None

    # index_schema関数を実行
    # rag.pyのloggerがモックであることを確認
    from app.services.rag import logger as rag_logger
    assert rag_logger == mock_logger

    index_schema(project_id, schema_path)

    # タイムアウト警告のログが出力されたことを確認
    mock_logger.warning.assert_any_call('FAISS processing timed out after 30 seconds') # Actualのログメッセージに合わせる
    mock_logger.warning.assert_any_call('FAISS vector database was not created due to timeout or error.') # このログも出力される

    # FAISSの保存処理が呼ばれないことを確認
    mock_faiss_cls.from_documents.assert_called_once() # from_documentsは呼ばれる
    mock_faiss_cls.return_value.save_local.assert_not_called() # save_localは呼ばれない

    # シンボリックリンク関連の処理が呼ばれないことを確認
    mock_exists.assert_not_called()
    mock_islink.assert_not_called()
    mock_rmtree.assert_not_called()
    mock_symlink.assert_not_called()

    # signal.alarm(0) が finally ブロックで呼ばれたことを確認
    mock_signal.alarm.assert_called_with(0)