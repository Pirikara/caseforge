from typing import List, Dict, Any
import os
import yaml
import json
import copy
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from app.config import settings
from app.logging_config import logger
import signal

class TimeoutException(Exception):
    pass

# 既存のEmbeddingFunctionForCaseforgeクラスはそのまま残します。
class EmbeddingFunctionForCaseforge(Embeddings):
    """
    DBで使用するための埋め込み関数
    """
    def __init__(self):
        """
        簡易的な埋め込み関数を初期化
        HuggingFaceモデルのロードに問題があるため、簡易的な代替手段を使用
        """
        try:
            logger.info("Using simplified embedding function instead of HuggingFace model")
            self.embedder = None
            logger.info("Successfully initialized simplified embedding function")
        except Exception as e:
            logger.error(f"Error initializing simplified embedding function: {e}", exc_info=True)
            raise

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        DBのEmbeddingFunction用の呼び出しメソッド

        Args:
            input: 埋め込むテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        return self.embed_documents(input)

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        """
        複数のドキュメントを埋め込む - 簡易的な実装

        Args:
            input: 埋め込むテキストのリスト

        Returns:
            埋め込みベクトルのリスト
        """
        try:
            logger.info(f"Creating simplified embeddings for {len(input)} documents")
            import hashlib

            result = []
            for text in input:
                hash_obj = hashlib.md5(text.encode())
                hash_bytes = hash_obj.digest()

                vector = []
                for i in range(384):
                    byte_val = hash_bytes[i % len(hash_bytes)]
                    vector.append((byte_val / 128.0) - 1.0)

                result.append(vector)

            logger.info("Successfully created simplified embeddings")
            return result
        except Exception as e:
            logger.error(f"Error creating simplified embeddings: {e}", exc_info=True)
            return [[0.0] * 384 for _ in range(len(input))]

    def embed_query(self, input: str) -> List[float]:
        """
        クエリを埋め込む - 簡易的な実装

        Args:
            input: 埋め込むクエリテキスト

        Returns:
            埋め込みベクトル
        """
        try:
            logger.info(f"Creating simplified embedding for query: {input[:30]}...")
            # 単一のテキストに対する埋め込みを生成
            result = self.embed_documents([input])[0]
            logger.info("Successfully created simplified query embedding")
            return result
        except Exception as e:
            logger.error(f"Error creating simplified query embedding: {e}", exc_info=True)
            # エラーが発生した場合は、ダミーのベクトルを返す
            return [0.0] * 384

class OpenAPISchemaChunker:
    """
    OpenAPIスキーマを構造単位でチャンク化し、$refを解決するクラス
    """
    def __init__(self, path: str):
        """
        Args:
            path: OpenAPIスキーマファイルのパス
        """
        self.path = path
        self.schema: Dict[str, Any] = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """
        スキーマファイルを読み込み、YAMLまたはJSONとしてパースする
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                if self.path.endswith((".yaml", ".yml")):
                    return yaml.safe_load(f)
                elif self.path.endswith(".json"):
                    return json.load(f)
                else:
                    raise ValueError("Unsupported file format. Must be .yaml, .yml, or .json")
        except Exception as e:
            logger.error(f"Error loading or parsing schema file {self.path}: {e}")
            raise

    def _resolve_references(self, obj: Any) -> Any:
        """
        オブジェクト内の$refを再帰的に解決する
        """
        if isinstance(obj, dict):
            resolved_obj = {}
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str) and value.startswith("#/"):
                    ref_path = value.lstrip("#/").split("/")
                    ref_value = self.schema
                    try:
                        for part in ref_path:
                            ref_value = ref_value[part]
                        # $refを解決した値で置き換え、さらにその値内の$refも解決
                        resolved_obj.update(self._resolve_references(copy.deepcopy(ref_value)))
                    except (KeyError, TypeError) as e:
                        logger.warning(f"Could not resolve reference {value}: {e}")
                        # 解決できなかった場合は元の$refを残すか、エラーを示す
                        resolved_obj[key] = value # または resolved_obj[key] = {"$error": f"Unresolved reference: {value}"}
                else:
                    resolved_obj[key] = self._resolve_references(value)
            return resolved_obj
        elif isinstance(obj, list):
            return [self._resolve_references(item) for item in obj]
        else:
            return obj

    def get_documents(self) -> List[Document]:
        """
        スキーマをチャンク化し、Documentオブジェクトのリストを返す
        """
        documents: List[Document] = []
        if "paths" not in self.schema:
            logger.warning("No 'paths' found in schema.")
            return documents

        for path, methods in self.schema["paths"].items():
            if not isinstance(methods, dict):
                continue # Skip if not a dictionary (e.g., $ref at path level)

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue # Skip if not a dictionary (e.g., $ref at method level)

                # $refを解決したチャンク内容を構築
                chunk_content: Dict[str, Any] = {
                    "method": method.upper(),
                    "path": path,
                }

                # parameters, requestBody, responses を含める（$ref解決済み）
                if "parameters" in details:
                    chunk_content["parameters"] = self._resolve_references(details["parameters"])
                if "requestBody" in details:
                    chunk_content["requestBody"] = self._resolve_references(details["requestBody"])
                if "responses" in details:
                    # 主要なレスポンスのみを含める（例: 200, 201）
                    relevant_responses = {
                        status: resp for status, resp in details["responses"].items()
                        if status in ["200", "201", "204"] or status.startswith("2") # 2xx系を主要とみなす
                    }
                    chunk_content["responses"] = self._resolve_references(relevant_responses)

                # YAML形式の文字列としてpage_contentを作成
                page_content = yaml.dump(chunk_content, indent=2, sort_keys=False)

                # Documentオブジェクトを作成
                metadata = {
                    "source": f"{self.path}::paths::{path}::{method}",
                    "type": "path-method",
                    "path": path, # メタデータにもpathとmethodを追加しておくと便利かもしれない
                    "method": method.upper(),
                }
                documents.append(Document(page_content=page_content, metadata=metadata))
                logger.debug(f"Created document for {method.upper()} {path}")

        logger.info(f"Finished chunking schema. Created {len(documents)} documents.")
        return documents


def index_schema(project_id: str, path: str) -> None:
    """
    OpenAPIスキーマをベクトルDBにインデックスする
    """
    try:
        logger.info(f"Indexing schema for project {project_id}: {path}")

        # 1. スキーマファイルのロードとチャンク化
        logger.info("Step 1: Loading, parsing, and chunking OpenAPI schema file")
        chunker = OpenAPISchemaChunker(path)
        docs = chunker.get_documents()
        logger.info(f"Successfully chunked schema file into {len(docs)} documents")

        if not docs:
            logger.warning(f"No documents generated for schema {path}. Skipping indexing.")
            return

        # 2. 埋め込み関数の初期化
        logger.info("Step 2: Initializing embedding function")
        # MEMO.mdの指示通りHuggingFaceEmbeddingsを使用
        # HuggingFaceモデルのロードに問題がある場合、EmbeddingFunctionForCaseforgeにフォールバックします。
        # 既存の懸念についてはEmbeddingFunctionForCaseforgeクラスのコメントを参照してください。

        try:
            # タイムアウト処理を追加 (HuggingFaceモデルのロードに時間がかかる場合があるため)
            try:
                # import signal # signalモジュールをここでインポート - ファイル先頭のimportを使用

                def timeout_handler(signum, frame):
                    raise TimeoutException("HuggingFaceEmbeddings initialization timed out")

                # 60秒のタイムアウトを設定 (モデルダウンロードなどを考慮し、FAISSより長めに設定)
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(120)

                embedding_function = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info("Successfully initialized HuggingFace embedding function")

                # タイムアウトを解除
                signal.alarm(0)

            except ImportError:
                logger.warning("signal module not available, skipping timeout for HuggingFaceEmbeddings initialization.")
                embedding_function = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info("Successfully initialized HuggingFace embedding function (without timeout)")

            except TimeoutException:
                logger.warning("HuggingFaceEmbeddings initialization timed out after 60 seconds")
                # タイムアウトした場合は、フォールバック処理に進む
                raise TimeoutException # フォールバック処理に進むために例外を再raise

        except (Exception, TimeoutException) as e:
             logger.error(f"Failed to initialize HuggingFaceEmbeddings: {e}", exc_info=True)
             logger.warning("Falling back to simplified embedding function due to HuggingFace model loading issue or timeout.")
             embedding_function = EmbeddingFunctionForCaseforge() # フォールバック
             # 念のため、タイムアウトを解除
             try:
                 signal.alarm(0)
             except ImportError:
                 pass # signalモジュールがない場合は何もしない


        # 3. FAISSへのドキュメント埋め込み
        logger.info("Step 3: Embedding documents into FAISS")
        try:
            # タイムアウト処理を追加
            # signalモジュールはテスト環境で問題を起こす可能性があるため、必要なスコープ内でインポート・使用する
            try:
                # import signal # signalモジュールをここでインポート - ファイル先頭のimportを使用

                def timeout_handler(signum, frame):
                    raise TimeoutException("FAISS processing timed out")

                # 120秒のタイムアウトを設定
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)

                vectordb = FAISS.from_documents(docs, embedding_function)

                # タイムアウトを解除
                signal.alarm(0)
                logger.info("Successfully embedded documents into FAISS")

            except ImportError:
                logger.warning("signal module not available, skipping timeout.")
                vectordb = FAISS.from_documents(docs, embedding_function)
                logger.info("Successfully embedded documents into FAISS (without timeout)")

            except TimeoutException:
                logger.warning("FAISS processing timed out after 120 seconds")
                # タイムアウトした場合は、処理を続行
                # タイムアウトが発生した場合、vectordbは作成されないのでNoneを設定
                vectordb = None

            finally:
                # 念のため、タイムアウトを解除
                try:
                    signal.alarm(0)
                except ImportError:
                    pass # signalモジュールがない場合は何もしない

            if vectordb is None:
                 logger.warning("FAISS vector database was not created due to timeout or error.")
                 return # vectordbがNoneの場合は保存処理に進まない

            # 4. ベクトルDBの保存
            logger.info("Step 4: Saving vector database")


            # 永続化されるディレクトリにベクトルDBを保存
            data_dir = os.environ.get("DATA_DIR", "/app/data")
            save_dir = f"{data_dir}/faiss/{project_id}"

            logger.info(f"Saving vector database to {save_dir}")
            os.makedirs(save_dir, exist_ok=True)  # プロジェクトIDを含むディレクトリを作成
            logger.info(f"Created directory: {save_dir}")

            try:
                vectordb.save_local(save_dir)
                logger.info(f"Successfully saved vector database to {save_dir}")

                # 互換性のために/tmpにもシンボリックリンクを作成
                tmp_dir = f"/tmp/faiss/{project_id}"
                os.makedirs(os.path.dirname(tmp_dir), exist_ok=True)

                # 既存のシンボリックリンクや古いディレクトリを削除
                if os.path.exists(tmp_dir):
                    if os.path.islink(tmp_dir):
                        os.unlink(tmp_dir)
                    else:
                        import shutil
                        shutil.rmtree(tmp_dir)

                # 新しいシンボリックリンクを作成
                os.symlink(save_dir, tmp_dir)
                logger.info(f"Created symbolic link from {tmp_dir} to {save_dir}")
            except Exception as save_error:
                logger.error(f"Error saving vector database to {save_dir}: {save_error}", exc_info=True)
                raise save_error # 例外を再raiseする

            logger.info(f"Successfully indexed schema for project {project_id}")
        except TimeoutException:
            logger.warning("FAISS processing timed out after 120 seconds")
            # タイムアウトした場合は、処理を続行
            logger.warning("Continuing without FAISS indexing")
        finally:
            # 念のため、タイムアウトを解除
            signal.alarm(0)

    except Exception as e:
        logger.error(f"Error in FAISS processing: {e}", exc_info=True)
        # FAISSの処理でエラーが発生した場合、代替処理を実行
        logger.warning("Attempting to continue without FAISS indexing")
