from typing import List, Dict, Any, Optional
import json
import os
from app.models import Endpoint
from app.services.rag import EmbeddingFunctionForCaseforge
from app.config import settings
from app.logging_config import logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS

class EndpointChainGenerator:
    """選択されたエンドポイントからテストチェーンを生成するクラス"""
    
    def __init__(self, project_id: str, endpoints: List[Endpoint], schema: Dict = None):
        """
        Args:
            project_id: プロジェクトID
            endpoints: 選択されたエンドポイントのリスト
            schema: OpenAPIスキーマ（オプション）
        """
        self.project_id = project_id
        self.endpoints = endpoints
        self.schema = schema
    
    def generate_chains(self) -> List[Dict]:
        """
        選択されたエンドポイントからテストチェーンを生成する (TO-BE: エンドポイントごとに生成)
        
        Returns:
            生成されたテストチェーンのリスト
        """
        generated_chains = []
        
        # LLMの設定 (ループの外で一度だけ行う)
        model_name = settings.LLM_MODEL_NAME
        api_base = settings.OPENAI_API_BASE
        
        # LLMの設定をログに出力
        logger.info(f"Using LLM model: {model_name}, API base: {api_base}")
        
        try:
            llm = ChatOpenAI(
                model_name=model_name,
                openai_api_base=api_base,
                temperature=0.2,
                api_key=settings.OPENAI_API_KEY,
            )
            logger.info("LLM initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}", exc_info=True)
            raise
        
        # プロンプトの設定 (ループの外で一度だけ行う)
        prompt = ChatPromptTemplate.from_template(
            """あなたはAPIテストの専門家です。以下のターゲットエンドポイントと、関連するOpenAPIスキーマ情報を元に、そのターゲットエンドポイントを正常に実行するために必要な前提リクエストを含むテストチェーンを生成してください。

ターゲットエンドポイント:
{target_endpoint_info}

関連スキーマ情報:
{relevant_schema_info}

テストチェーンは、環境構築や必要なリソース作成のための前提リクエストから始まり、最後にターゲットエンドポイントへのリクエストで終わるようにしてください。エンドポイント間の依存関係を考慮し、例えばターゲットエンドポイントがパスパラメータにリソースIDを必要とする場合、そのリソースを作成しIDを抽出する先行リクエストを含めてください。

以下の構造を持つJSONオブジェクトのみを返してください。

```json
{{
  "name": "チェーンの分かりやすい名前 (例: POST /users のテスト)",
  "steps": [
    {{
      "method": "HTTPメソッド (GET, POST, PUT, DELETE)",
      "path": "パラメータのプレースホルダーを含むAPIパス (例: /users/{{user_id}})",
      "request": {{
        "headers": {{"ヘッダー名": "値"}},
        "body": {{"キー": "値"}}
      }},
      "response": {{
        "extract": {{"変数名": "$.jsonpath.to.value"}}
      }}
    }},
    // ... 他のステップ ...
    {{
      // これはターゲットエンドポイントへのリクエストである必要があります
      "method": "HTTPメソッド (GET, POST, PUT, DELETE)",
      "path": "パラメータのプレースホルダーを含むAPIパス",
      "request": {{
        "headers": {{"ヘッダー名": "値"}},
        "body": {{"キー": "値"}}
      }},
      "response": {{
        "extract": {{"変数名": "$.jsonpath.to.value"}}
      }}
    }}
  ]
}}
```

以下の点を確認してください：
1. レスポンスから値を抽出するために、"extract"に適切なJSONPath式を含めること。
2. 抽出した値を、後続のリクエストのパスパラメータやリクエストボディで使用すること。
3. チェーンの最後のステップが必ずターゲットエンドポイントへのリクエストであること。
4. 必要なリソースのセットアップを含め、ターゲットエンドポイントを徹底的にテストするための論理的なフローを作成すること。
5. JSONオブジェクトのみを返し、説明や他のテキストを含めないこと。
6. 各ターゲットエンドポイントに対して個別のテストチェーンを生成すること。
7. テストチェーンの名前には、ターゲットエンドポイントのメソッドとパスを含めること。
"""
        )
        
        for target_endpoint in self.endpoints:
            logger.info(f"Generating chain for endpoint: {target_endpoint.method} {target_endpoint.path}")
            
            try:
                # 1. ターゲットエンドポイント情報からコンテキストを構築
                target_endpoint_info = self._build_endpoint_context(target_endpoint)
                
                # 2. RAGを活用して関連スキーマ情報を取得
                relevant_schema_info = self._get_relevant_schema_info(target_endpoint)
                
                # 3. LLMに渡すコンテキストを構築
                context = {
                    "target_endpoint_info": target_endpoint_info,
                    "relevant_schema_info": relevant_schema_info
                }
                
                # 4. LLMを呼び出してチェーンを生成
                logger.info(f"Invoking LLM for endpoint {target_endpoint.method} {target_endpoint.path}")
                try:
                    resp = (prompt | llm).invoke(context).content
                    logger.info(f"Raw LLM response for {target_endpoint.method} {target_endpoint.path}: {resp[:200]}...")
                except Exception as llm_error:
                    logger.error(f"Error invoking LLM for endpoint {target_endpoint.method} {target_endpoint.path}: {llm_error}", exc_info=True)
                    # LLM呼び出しエラーの場合は、シンプルなテストチェーンを生成
                    logger.info(f"Generating fallback test chain for {target_endpoint.method} {target_endpoint.path}")
                    chain = self._generate_fallback_chain(target_endpoint)
                    generated_chains.append(chain)
                    logger.info(f"Added fallback chain for {target_endpoint.method} {target_endpoint.path}")
                    continue
                
                try:
                    chain = json.loads(resp)
                    
                    # 生成されたチェーンに名前を付ける (例: Test for GET /users/{user_id})
                    if not chain.get("name"):
                         chain["name"] = f"Test for {target_endpoint.method.upper()} {target_endpoint.path}"
    
                    generated_chains.append(chain)
                    logger.info(f"Successfully generated chain for {target_endpoint.method} {target_endpoint.path} with {len(chain.get('steps', []))} steps")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON for {target_endpoint.method} {target_endpoint.path}: {e}")
                    logger.error(f"Raw response: {resp}")
                    # JSONのパースに失敗した場合、レスポンスから JSON 部分を抽出してみる
                    try:
                        import re
                        json_match = re.search(r'```json\s*(.*?)\s*```', resp, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            chain = json.loads(json_str)
                            if not chain.get("name"):
                                chain["name"] = f"Test for {target_endpoint.method.upper()} {target_endpoint.path}"
                            generated_chains.append(chain)
                            logger.info(f"Successfully extracted and parsed JSON from markdown code block for {target_endpoint.method} {target_endpoint.path}")
                        else:
                            logger.error(f"Could not find JSON code block in response for {target_endpoint.method} {target_endpoint.path}")
                    except Exception as extract_error:
                        logger.error(f"Error extracting JSON from response: {extract_error}")
                
            except Exception as e:
                logger.error(f"Error generating chain for {target_endpoint.method} {target_endpoint.path}: {e}", exc_info=True)
                
        return generated_chains # 複数のチェーンを返す

    def _build_endpoint_context(self, endpoint: Endpoint) -> str:
        """単一のエンドポイント情報からLLMのためのコンテキストを構築する"""
        endpoint_info = f"Endpoint: {endpoint.method} {endpoint.path}\n"
        
        if endpoint.summary:
            endpoint_info += f"Summary: {endpoint.summary}\n"
        
        if endpoint.description:
            endpoint_info += f"Description: {endpoint.description}\n"
        
        # リクエストボディ情報
        if endpoint.request_body:
            endpoint_info += "Request Body:\n"
            endpoint_info += f"```json\n{json.dumps(endpoint.request_body, indent=2)}\n```\n"
        
        # リクエストヘッダー情報
        if endpoint.request_headers:
            endpoint_info += "Request Headers:\n"
            for header_name, header_info in endpoint.request_headers.items():
                required = "required" if header_info.get("required", False) else "optional"
                endpoint_info += f"- {header_name} (in header, {required})\n" # in header を追加
        
        # クエリパラメータ情報
        if endpoint.request_query_params:
            endpoint_info += "Query Parameters:\n"
            for param_name, param_info in endpoint.request_query_params.items():
                required = "required" if param_info.get("required", False) else "optional"
                endpoint_info += f"- {param_name} (in query, {required})\n" # in query を追加
        
        # パスパラメータ情報
        path_parameters = []
        
        # スキーマが利用可能な場合のみパラメータを取得
        if self.schema:
            # パスレベルのパラメータを取得
            if endpoint.path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][endpoint.path]
                if "parameters" in path_item:
                    path_parameters.extend(path_item["parameters"])
            
            # 操作レベルのパラメータを取得
            if endpoint.path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][endpoint.path]
                if endpoint.method.lower() in path_item:
                    operation = path_item[endpoint.method.lower()]
                    if "parameters" in operation:
                        path_parameters.extend(operation["parameters"])

        # 重複を除去 (パラメータ名とinで判断)
        unique_path_parameters = {}
        for param in path_parameters:
            key = (param.get("name"), param.get("in"))
            if key not in unique_path_parameters:
                unique_path_parameters[key] = param
        
        if unique_path_parameters:
            endpoint_info += "Path Parameters:\n"
            for param in unique_path_parameters.values():
                param_name = param.get("name", "unknown")
                required = "required" if param.get("required", False) else "optional"
                param_schema = param.get("schema", {})
                param_type = param_schema.get("type", "any")
                endpoint_info += f"- {param_name} (in path, {required}, type: {param_type})\n"

        # レスポンス情報
        if endpoint.responses:
            endpoint_info += "Responses:\n"
            for status, response in endpoint.responses.items():
                endpoint_info += f"- Status: {status}\n"
                if "description" in response:
                    endpoint_info += f"  Description: {response['description']}\n"
                if "content" in response:
                    for media_type, content in response["content"].items():
                        if "schema" in content:
                            endpoint_info += f"  Content Type: {media_type}\n"
                            endpoint_info += f"  Schema:\n```json\n{json.dumps(content['schema'], indent=2)}\n```\n"
        
        return endpoint_info

    def _get_relevant_schema_info(self, target_endpoint: Endpoint) -> str:
        """
        RAGを活用してターゲットエンドポイントに関連するスキーマ情報を取得する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            関連スキーマ情報のテキスト表現
        """
        try:
            # 永続化されるディレクトリからベクトルDBをロード
            data_dir = os.environ.get("DATA_DIR", "/app/data")
            faiss_path = f"{data_dir}/faiss/{self.project_id}"
            
            # 永続化ディレクトリにベクトルDBがない場合は、/tmpも確認
            if not os.path.exists(faiss_path):
                tmp_faiss_path = f"/tmp/faiss/{self.project_id}"
                if os.path.exists(tmp_faiss_path):
                    logger.info(f"FAISS vector DB found in temporary directory: {tmp_faiss_path}")
                    faiss_path = tmp_faiss_path
                else:
                    logger.warning(f"FAISS vector DB not found for project {self.project_id} at {faiss_path} or {tmp_faiss_path}. Cannot perform RAG search.")
                    
                    # ベクトルDBがない場合は、スキーマ全体から関連情報を抽出する
                    if self.schema:
                        logger.info(f"Using schema directly for endpoint {target_endpoint.method} {target_endpoint.path}")
                        return self._extract_schema_info_directly(target_endpoint)
                    else:
                        return "No relevant schema information found."
            
            # ベクトルDBが存在する場合は通常通りRAG検索を行う
            logger.info(f"Loading FAISS vector DB from {faiss_path}")
            embedding_fn = EmbeddingFunctionForCaseforge()
            
            try:
                vectordb = FAISS.load_local(faiss_path, embedding_fn, allow_dangerous_deserialization=True)
                logger.info(f"Successfully loaded FAISS vector DB from {faiss_path}")
            except Exception as load_error:
                logger.error(f"Error loading FAISS vector DB from {faiss_path}: {load_error}", exc_info=True)
                
                # ベクトルDBのロードに失敗した場合は、スキーマ全体から関連情報を抽出する
                if self.schema:
                    logger.info(f"Falling back to direct schema extraction due to FAISS load error")
                    return self._extract_schema_info_directly(target_endpoint)
                else:
                    return "Error loading vector database. No relevant schema information found."

            # クエリの生成 (ターゲットエンドポイントの情報を使用)
            query = f"{target_endpoint.method.upper()} {target_endpoint.path} {target_endpoint.summary or ''} {target_endpoint.description or ''}"
            if target_endpoint.request_body:
                 query += f" Request Body: {json.dumps(target_endpoint.request_body)}"
            if target_endpoint.request_headers:
                 query += f" Request Headers: {json.dumps(target_endpoint.request_headers)}"
            if target_endpoint.request_query_params:
                 query += f" Query Parameters: {json.dumps(target_endpoint.request_query_params)}"
            if target_endpoint.responses:
                 query += f" Responses: {json.dumps(target_endpoint.responses)}"

            # ベクトルDB検索
            # k=5 で上位5件の関連情報を取得
            docs = vectordb.similarity_search(query, k=5)

            # 取得したスキーマチャンクをテキスト形式に整形（ソース情報を含める）
            relevant_info_parts = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "unknown")
                relevant_info_parts.append(f"## Source {i+1}: {source}\n```\n{doc.page_content}\n```")

            relevant_info = "\n\n".join(relevant_info_parts)

            if not relevant_info.strip():
                return "No relevant schema information found."

            return f"""
# Relevant Schema Information for {target_endpoint.method.upper()} {target_endpoint.path}

{relevant_info}
"""

        except Exception as e:
            logger.error(f"Error during RAG search for endpoint {target_endpoint.method} {target_endpoint.path}: {e}", exc_info=True)
            
            # エラーが発生した場合は、スキーマから直接情報を抽出する
            if self.schema:
                logger.info(f"Falling back to direct schema extraction for endpoint {target_endpoint.method} {target_endpoint.path}")
                return self._extract_schema_info_directly(target_endpoint)
            else:
                return "Error retrieving relevant schema information."
    
    def _extract_schema_info_directly(self, target_endpoint: Endpoint) -> str:
        """
        スキーマから直接ターゲットエンドポイントに関連する情報を抽出する
        （ベクトルDBが利用できない場合のフォールバック）
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            関連スキーマ情報のテキスト表現
        """
        if not self.schema:
            return "No schema available for direct extraction."
        
        relevant_info_parts = []
        
        try:
            # 1. ターゲットエンドポイントのパス情報を抽出
            if target_endpoint.path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][target_endpoint.path]
                relevant_info_parts.append(f"## Path: {target_endpoint.path}")
                relevant_info_parts.append(f"```json\n{json.dumps(path_item, indent=2)}\n```\n")
            
            # 2. リクエストボディのスキーマ参照を解決
            if target_endpoint.request_body:
                for content_type, content in target_endpoint.request_body.get("content", {}).items():
                    if "schema" in content:
                        schema = content["schema"]
                        if "$ref" in schema:
                            ref_path = schema["$ref"]
                            if ref_path.startswith("#/"):
                                ref_parts = ref_path.lstrip("#/").split("/")
                                ref_value = self.schema
                                for part in ref_parts:
                                    if part in ref_value:
                                        ref_value = ref_value[part]
                                
                                relevant_info_parts.append(f"## Request Body Schema Reference: {ref_path}")
                                relevant_info_parts.append(f"```json\n{json.dumps(ref_value, indent=2)}\n```\n")
            
            # 3. レスポンススキーマの参照を解決
            if target_endpoint.responses:
                for status, response in target_endpoint.responses.items():
                    if "content" in response:
                        for content_type, content in response["content"].items():
                            if "schema" in content:
                                schema = content["schema"]
                                if "$ref" in schema:
                                    ref_path = schema["$ref"]
                                    if ref_path.startswith("#/"):
                                        ref_parts = ref_path.lstrip("#/").split("/")
                                        ref_value = self.schema
                                        for part in ref_parts:
                                            if part in ref_value:
                                                ref_value = ref_value[part]
                                        
                                        relevant_info_parts.append(f"## Response Schema Reference for status {status}: {ref_path}")
                                        relevant_info_parts.append(f"```json\n{json.dumps(ref_value, indent=2)}\n```\n")
            
            # 4. 関連するコンポーネントスキーマを抽出
            if "components" in self.schema and "schemas" in self.schema["components"]:
                # パスからリソース名を抽出（例: /users/{user_id} -> users）
                path_parts = target_endpoint.path.strip("/").split("/")
                resource_name = path_parts[0] if path_parts else ""
                
                # リソース名に関連するスキーマを探す
                for schema_name, schema in self.schema["components"]["schemas"].items():
                    if resource_name.lower() in schema_name.lower():
                        relevant_info_parts.append(f"## Related Component Schema: {schema_name}")
                        relevant_info_parts.append(f"```json\n{json.dumps(schema, indent=2)}\n```\n")
            
            relevant_info = "\n".join(relevant_info_parts)
            
            if not relevant_info.strip():
                return "No relevant schema information found through direct extraction."
            
            return f"""
# Relevant Schema Information for {target_endpoint.method.upper()} {target_endpoint.path} (Direct Extraction)

{relevant_info}
"""
        except Exception as e:
            logger.error(f"Error during direct schema extraction for endpoint {target_endpoint.method} {target_endpoint.path}: {e}", exc_info=True)
            return "Error during direct schema extraction."
            
    def _generate_fallback_chain(self, target_endpoint: Endpoint) -> Dict:
        """
        LLM呼び出しエラーの場合のフォールバックとして、シンプルなテストチェーンを生成する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            シンプルなテストチェーン
        """
        method = target_endpoint.method.upper()
        path = target_endpoint.path
        
        # チェーン名
        chain_name = f"Test for {method} {path}"
        
        # ステップの初期化
        steps = []
        
        # パスパラメータの抽出
        path_params = []
        param_pattern = r'\{([^}]+)\}'
        import re
        path_params = re.findall(param_pattern, path)
        
        # 前提ステップの追加（パスパラメータがある場合）
        for param in path_params:
            # パラメータの種類を推測
            param_type = "id"
            resource_name = "resource"
            
            # パスからリソース名を推測
            path_parts = path.strip('/').split('/')
            if len(path_parts) > 0:
                resource_name = path_parts[0]
                # 複数形を単数形に変換（簡易的な処理）
                if resource_name.endswith('s'):
                    resource_name = resource_name[:-1]
            
            # パラメータ名からリソース名を推測
            if param.endswith('_id') or param == 'id':
                param_parts = param.split('_')
                if len(param_parts) > 1 and param_parts[-1] == 'id':
                    resource_name = '_'.join(param_parts[:-1])
            
            # リソース作成ステップ（POSTリクエスト）
            create_step = {
                "method": "POST",
                "path": f"/{resource_name}s",
                "request": {
                    "headers": {"Content-Type": "application/json"},
                    "body": {"name": f"Test {resource_name}", "description": f"Test {resource_name} description"}
                },
                "response": {
                    "extract": {param: f"$.id"}
                }
            }
            steps.append(create_step)
        
        # ターゲットエンドポイントのステップ
        target_step = {
            "method": method,
            "path": path,
            "request": {}
        }
        
        # リクエストボディの追加（POSTまたはPUTの場合）
        if method in ["POST", "PUT", "PATCH"]:
            # リクエストボディのスキーマがある場合は、それを基にサンプルを生成
            if target_endpoint.request_body and "content" in target_endpoint.request_body:
                for content_type, content in target_endpoint.request_body["content"].items():
                    if "application/json" in content_type and "schema" in content:
                        target_step["request"]["headers"] = {"Content-Type": "application/json"}
                        # スキーマからサンプルボディを生成（簡易的な実装）
                        sample_body = self._generate_sample_body_from_schema(content["schema"])
                        target_step["request"]["body"] = sample_body
                        break
            else:
                # スキーマがない場合は、シンプルなJSONを設定
                target_step["request"]["headers"] = {"Content-Type": "application/json"}
                target_step["request"]["body"] = {"name": "Test name", "description": "Test description"}
        
        # ステップの追加
        steps.append(target_step)
        
        # チェーンの構築
        chain = {
            "name": chain_name,
            "steps": steps
        }
        
        return chain
    
    def _generate_sample_body_from_schema(self, schema: Dict) -> Dict:
        """
        スキーマからサンプルリクエストボディを生成する
        
        Args:
            schema: JSONスキーマ
            
        Returns:
            サンプルリクエストボディ
        """
        sample_body = {}
        
        # $refの解決
        if "$ref" in schema:
            # $refの解決は複雑なので、ここではシンプルなボディを返す
            return {"name": "Test name", "description": "Test description"}
        
        # プロパティの処理
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                prop_type = prop_schema.get("type", "string")
                
                if prop_type == "string":
                    sample_body[prop_name] = f"Test {prop_name}"
                elif prop_type == "integer" or prop_type == "number":
                    sample_body[prop_name] = 1
                elif prop_type == "boolean":
                    sample_body[prop_name] = True
                elif prop_type == "array":
                    sample_body[prop_name] = []
                elif prop_type == "object":
                    sample_body[prop_name] = {}
        
        # サンプルボディが空の場合は、デフォルト値を設定
        if not sample_body:
            sample_body = {"name": "Test name", "description": "Test description"}
        
        return sample_body