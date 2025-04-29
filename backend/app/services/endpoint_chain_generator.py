from typing import List, Dict, Any, Optional
import json
from app.models import Endpoint
from app.services.rag import EmbeddingFunctionForCaseforge
from app.config import settings
from app.logging_config import logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class EndpointChainGenerator:
    """選択されたエンドポイントからテストチェーンを生成するクラス"""
    
    def __init__(self, project_id: str, endpoints: List[Endpoint]):
        """
        Args:
            project_id: プロジェクトID
            endpoints: 選択されたエンドポイントのリスト
        """
        self.project_id = project_id
        self.endpoints = endpoints
    
    def generate_chains(self) -> List[Dict]:
        """
        選択されたエンドポイントからテストチェーンを生成する
        
        Returns:
            生成されたテストチェーンのリスト
        """
        # エンドポイント情報からコンテキストを構築
        context = self._build_context()
        
        # LLMの設定
        model_name = settings.LLM_MODEL_NAME
        api_base = settings.OPENAI_API_BASE
        
        llm = ChatOpenAI(
            model_name=model_name,
            openai_api_base=api_base,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY,
        )
        
        # プロンプトの設定
        prompt = ChatPromptTemplate.from_template(
            """You are an API testing expert. Using the following OpenAPI endpoints:
{context}

Generate a request chain that tests these endpoints in sequence. The chain should follow the dependencies between endpoints.
For example, if a POST creates a resource and returns an ID, use that ID in subsequent requests.

Return ONLY a JSON object with the following structure:
{{
  "name": "Descriptive name for the chain",
  "steps": [
    {{
      "method": "HTTP method (GET, POST, PUT, DELETE)",
      "path": "API path with placeholders for parameters",
      "request": {{
        "headers": {{"header-name": "value"}},
        "body": {{"key": "value"}}
      }},
      "response": {{
        "extract": {{"variable_name": "$.jsonpath.to.value"}}
      }}
    }}
  ]
}}

Make sure to:
1. Include proper JSONPath expressions in "extract" to get values from responses
2. Use extracted values in subsequent requests by replacing path parameters or in request bodies
3. Create a logical flow that tests the API endpoints thoroughly
4. Return ONLY the JSON object, no explanations or other text."""
        )
        
        # LLMを呼び出してチェーンを生成
        try:
            resp = (prompt | llm).invoke({"context": context}).content
            chain = json.loads(resp)
            logger.info(f"Successfully generated request chain with {len(chain.get('steps', []))} steps")
            return [chain]  # 単一のチェーンを返す
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {resp}")
            return []
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            return []
    
    def _build_context(self) -> str:
        """エンドポイント情報からLLMのためのコンテキストを構築する"""
        context_parts = []
        
        for endpoint in self.endpoints:
            # エンドポイントの情報を整形
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
                    endpoint_info += f"- {header_name} ({required})\n"
            
            # クエリパラメータ情報
            if endpoint.request_query_params:
                endpoint_info += "Query Parameters:\n"
                for param_name, param_info in endpoint.request_query_params.items():
                    required = "required" if param_info.get("required", False) else "optional"
                    endpoint_info += f"- {param_name} ({required})\n"
            
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
            
            context_parts.append(endpoint_info)
        
        return "\n\n".join(context_parts)