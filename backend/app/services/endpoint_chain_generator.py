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
        llm = ChatOpenAI(
            model_name=model_name,
            openai_api_base=api_base,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY,
        )
        
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
                resp = (prompt | llm).invoke(context).content
                chain = json.loads(resp)
                
                # 生成されたチェーンに名前を付ける (例: Test for GET /users/{user_id})
                if not chain.get("name"):
                     chain["name"] = f"Test for {target_endpoint.method.upper()} {target_endpoint.path}"

                generated_chains.append(chain)
                logger.info(f"Successfully generated chain for {target_endpoint.method} {target_endpoint.path} with {len(chain.get('steps', []))} steps")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON for {target_endpoint.method} {target_endpoint.path}: {e}")
                logger.debug(f"Raw response: {resp}")
            except Exception as e:
                logger.error(f"Error generating chain for {target_endpoint.method} {target_endpoint.path}: {e}")
                
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
            # ベクトルDBのロード
            faiss_path = f"/tmp/faiss/{self.project_id}"
            embedding_fn = EmbeddingFunctionForCaseforge()
            
            if not os.path.exists(faiss_path):
                logger.warning(f"FAISS vector DB not found for project {self.project_id} at {faiss_path}. Cannot perform RAG search.")
                return "No relevant schema information found." # ベクトルDBがない場合は空の情報を返す

            vectordb = FAISS.load_local(faiss_path, embedding_fn, allow_dangerous_deserialization=True) # allow_dangerous_deserialization=True を追加

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
            return "Error retrieving relevant schema information."