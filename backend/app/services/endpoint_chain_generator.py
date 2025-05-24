from typing import List, Dict, Optional, Tuple, Set
import json
import os
import re
from app.models import Endpoint
from app.schemas.service import Endpoint as EndpointSchema
from app.services.rag.embeddings import EmbeddingFunctionForCaseforge
from app.config import settings
from app.logging_config import logger
from app.utils.path_manager import path_manager
from app.services.vector_db.manager import VectorDBManagerFactory
from app.services.openapi.analyzer import OpenAPIAnalyzer, DependencyAnalyzer
from langchain_core.documents import Document

class EndpointChainGenerator:
    """選択されたエンドポイントからテストチェーンを生成するクラス"""
    
    def __init__(self, service_id: int, endpoints: List[Endpoint], schema: Dict = None, error_types: Optional[List[str]] = None): # error_types 引数を追加
        """
        Args:
            service_id: サービスID (int)
            endpoints: 選択されたエンドポイントのリスト
            schema: OpenAPIスキーマ（オプション）
        """
        self.service_id = service_id
        self.endpoints = endpoints
        self.schema = schema
        self.error_types = error_types
        
        # 依存関係解析器の初期化
        self.dependency_analyzer = None
        self.dependencies = []
        if self.schema:
            self._initialize_dependency_analysis()
    
    def _initialize_dependency_analysis(self):
        """依存関係解析器を初期化し、依存関係を抽出する"""
        try:
            openapi_analyzer = OpenAPIAnalyzer(self.schema)
            self.dependencies = openapi_analyzer.extract_dependencies()
            self.dependency_analyzer = DependencyAnalyzer(self.schema)
            logger.info(f"Extracted {len(self.dependencies)} dependencies from schema")
        except Exception as e:
            logger.error(f"Error initializing dependency analysis: {e}", exc_info=True)
            self.dependencies = []
    
    def generate_chains(self) -> List[Dict]:
        """
        選択されたエンドポイントからテストチェーンを生成する (TO-BE: エンドポイントごとに生成)
        
        Returns:
            生成されたテストチェーンのリスト
        """
        generated_chains = []
        
        model_name = settings.LLM_MODEL_NAME
        api_base = settings.OPENAI_API_BASE
        
        from app.services.llm.client import LLMClientFactory, LLMProviderType, Message, MessageRole, LLMException, LLMResponseFormatException
        from app.services.llm.prompts import get_prompt_template
        
        
        try:
            llm_client = LLMClientFactory.create(
                provider_type=LLMProviderType.LOCAL,
                model_name=model_name,
                temperature=0.2,
            )
        except Exception as e:
            logger.error(f"Error initializing LLM client: {e}", exc_info=True)
            raise
        
        # 依存関係対応プロンプトテンプレートの使用を試行
        prompt_template = None
        use_dependency_aware_prompt = False
        
        try:
            if self.dependencies:
                # 依存関係が検出された場合は依存関係対応プロンプトを使用
                prompt_template = get_prompt_template("dependency_aware_rag")
                use_dependency_aware_prompt = True
                logger.info("Using dependency-aware prompt template")
            else:
                # 依存関係が検出されない場合は従来のプロンプトを使用
                prompt_template = get_prompt_template("endpoint_test_generation")
                logger.info("Using standard endpoint test generation prompt")
        except KeyError as e:
            logger.warning(f"Prompt template not found: {e}, using hardcoded prompt")
            prompt_template_str = """You are an expert in API testing. Based on the following target endpoint and related OpenAPI schema information, generate a complete test suite (TestSuite) in strict JSON format.

Target endpoint:
{target_endpoint_info}

Related OpenAPI schema:
{relevant_schema_info}

The test suite must include the following test cases:
1. **Normal case**: A request that successfully triggers the expected behavior. Include any necessary setup steps (e.g. creating required resources).
2. **Error cases**: Generate multiple test cases according to the following instruction:
{error_types_instruction}

Each test case must include both setup steps and a final step that sends a request to the **target endpoint**. Consider endpoint dependencies: if the target path, query parameter or body includes resource IDs, insert appropriate setup steps that create and extract them.

Return only a single valid JSON object matching the following format. **Do not include any explanations, markdown formatting, or non-JSON text.**

```json
{{
  "name": "Name of the test suite (e.g., PUT /users Test Suite)",
  "target_method": "HTTP method (e.g., PUT)",
  "target_path": "Path of the target endpoint (e.g., /users/{{id}})",
  "test_cases": [
    {{
      "name": "Test case name (e.g., Normal case)",
      "description": "What this test case is verifying",
      "error_type": null,  // For error cases: e.g., "invalid_input", "missing_field", etc.
      "test_steps": [
        {{
          "method": "HTTP method (e.g., POST)",
          "path": "API path (e.g., /users)",
          "request_headers": {{
            "Content-Type": "application/json"
          }},
          "request_body": {{
            "name": "John Doe"
          }},
          "request_params": {{}},
          "extract_rules": {{
            "user_id": "$.id"
          }},
          "expected_status": 201
        }},
        {{
          "method": "HTTP method (e.g., PUT)",
          "path": "API path (e.g., /users)",
          "request_headers": {{
            "Content-Type": "application/json"
          }},
          "request_body": {{
            "name": "Jane Doe",
            "user_id": {{user_id}}
          }},
          "request_params": {{}},
          "extract_rules": {{}}
          "expected_status": 201
        }}
      ]
    }}
  ]
}}
````

**Instructions (MUST FOLLOW STRICTLY):**
1. Strict requirement: Every single step object in `test_steps` MUST include ALL of the following keys:
    - `method`
    - `path`
    - `request_headers`
    - `request_body`
    - `request_params`
    - `extract_rules`
    - `expected_status`

   This rule applies to **every step**, including setup and error test steps.
   Do not omit `expected_status` even in intermediate or setup steps.
   If no specific status is expected, use 200 or 201 depending on the HTTP method.

2. Use appropriate JSONPath expressions in `extract_rules` to capture IDs or other values from previous responses.
3. Use the extracted values in subsequent steps (e.g., in path parameters or request body).
4. The **final step of each test case must always be the target endpoint call**.
5. Ensure logical, realistic sequences of steps (e.g., create resource → update → assert).
6. The output must be **a single valid JSON object**, and **nothing else** (no comments, no explanation).
7. Generate one test suite **per target endpoint**.
8. Include both the HTTP method and path in the test suite's `"name"` field.
9. For each test case, the `"name"` field should indicate the case type (e.g., "Normal case", "Invalid input").
10. Use the appropriate `error_type` for abnormal cases: `"missing_field"`, `"invalid_input"`, `"unauthorized"`, `"not_found"`, etc. Use `null` for normal cases.
"""
            prompt_template = prompt_template_str

        error_types_instruction = "以下の異常系の種類（missing_field, invalid_input, unauthorized, not_found など）"
        if self.error_types and len(self.error_types) > 0:
            error_types_instruction = f"以下の異常系の種類（{', '.join(self.error_types)}）"
        
        for target_endpoint in self.endpoints:
            
            try:
                target_endpoint_info = self._build_endpoint_context(target_endpoint)
                relevant_schema_info = self._get_relevant_schema_info(target_endpoint)
                
                if use_dependency_aware_prompt:
                    # 依存関係対応プロンプト用のコンテキスト構築
                    context = self._build_dependency_aware_context(
                        target_endpoint,
                        target_endpoint_info,
                        relevant_schema_info,
                        error_types_instruction
                    )
                else:
                    # 従来のプロンプト用のコンテキスト構築
                    context = {
                        "target_endpoint_info": target_endpoint_info,
                        "relevant_schema_info": relevant_schema_info,
                        "error_types_instruction": error_types_instruction
                    }
                
                try:
                    if 'prompt_template' in locals():
                        suite_data = llm_client.call_with_json_response(
                            [Message(MessageRole.USER,
                                    prompt_template.format(**context))]
                        )
                    else:
                        suite_data = llm_client.call_with_json_response(
                            [Message(MessageRole.USER,
                                    prompt_template_str.format(**context))]
                        )
                    
                
                except (LLMException, LLMResponseFormatException) as llm_error:
                    logger.error(f"Error invoking LLM for endpoint {target_endpoint.method} {target_endpoint.path}: {llm_error}", exc_info=True)
                    chain = self._generate_fallback_chain(target_endpoint)
                    generated_chains.append(chain)
                    continue
                
                try:
                    if use_dependency_aware_prompt:
                        suite_data = self._validate_and_normalize_dependency_aware_response(suite_data, target_endpoint)
                    else:
                        if not isinstance(suite_data, dict) or \
                            "name" not in suite_data or \
                            "target_method" not in suite_data or \
                            "target_path" not in suite_data or \
                            "test_cases" not in suite_data or \
                            not isinstance(suite_data["test_cases"], list):
                            raise ValueError("LLM response does not match expected TestSuite structure")

                    for case_data in suite_data["test_cases"]:
                        if not isinstance(case_data, dict) or \
                            "name" not in case_data or \
                            "description" not in case_data or \
                            "error_type" not in case_data or \
                            "test_steps" not in case_data or \
                            not isinstance(case_data["test_steps"], list):
                            raise ValueError("LLM response contains invalid TestCase structure")

                        for step_data in case_data["test_steps"]:
                             if not isinstance(step_data, dict) or \
                                "method" not in step_data or \
                                "path" not in step_data or \
                                "request_headers" not in step_data or \
                                "request_body" not in step_data or \
                                "request_params" not in step_data or \
                                "extract_rules" not in step_data or \
                                "expected_status" not in step_data:
                                raise ValueError("LLM response contains invalid TestStep structure")
                             
                             step_data = self._normalize_step_data_fields(step_data)

                    if 'target_method' not in suite_data or suite_data['target_method'] is None:
                        suite_data['target_method'] = target_endpoint.method
                        logger.warning(f"target_method not found in LLM response, using endpoint method: {target_endpoint.method}")
                    if 'target_path' not in suite_data or suite_data['target_path'] is None:
                        suite_data['target_path'] = target_endpoint.path
                        logger.warning(f"target_path not found in LLM response, using endpoint path: {target_endpoint.path}")

                    generated_chains.append(suite_data)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON for {target_endpoint.method} {target_endpoint.path}: {e}")
                    try:
                        import re
                        json_match = re.search(r'```json\s*(.*?)\s*```', suite_data, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            suite_data = json.loads(json_str)

                            if not isinstance(suite_data, dict) or \
                                "name" not in suite_data or \
                                "target_method" not in suite_data or \
                                "target_path" not in suite_data or \
                                "test_cases" not in suite_data or \
                                not isinstance(suite_data["test_cases"], list):
                                    raise ValueError("Extracted JSON does not match expected TestSuite structure")

                            for case_data in suite_data["test_cases"]:
                                if not isinstance(case_data, dict) or \
                                "name" not in case_data or \
                                "description" not in case_data or \
                                "error_type" not in case_data or \
                                "test_steps" not in case_data or \
                                not isinstance(case_data["test_steps"], list):
                                    raise ValueError("Extracted JSON contains invalid TestCase structure")

                                for step_data in case_data["test_steps"]:
                                    required_fields = [
                                        "method", "path",
                                        "request_headers", "request_body", "request_params",
                                        "extract_rules", "expected_status"
                                    ]
                                    if not isinstance(step_data, dict) or any(field not in step_data for field in required_fields):
                                        raise ValueError("Extracted JSON contains invalid TestStep structure")

                            generated_chains.append(suite_data)
                        else:
                            logger.error(f"Could not find JSON code block in response for {target_endpoint.method} {target_endpoint.path}")
                    except Exception as extract_error:
                        logger.error(f"Error extracting or parsing JSON from response: {extract_error}")

                except Exception as e:
                    logger.error(f"Error processing LLM response for {target_endpoint.method} {target_endpoint.path}: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error generating test suite for {target_endpoint.method} {target_endpoint.path}: {e}", exc_info=True)

        return generated_chains

    def _build_endpoint_context(self, endpoint: Endpoint) -> str:
        """単一のエンドポイント情報からLLMのためのコンテキストを構築する"""
        endpoint_info = f"Endpoint: {endpoint.method} {endpoint.path}\n"
        endpoint_model = EndpointSchema.from_orm(endpoint)
        
        if endpoint.summary:
            endpoint_info += f"Summary: {endpoint.summary}\n"
        
        if endpoint.description:
            endpoint_info += f"Description: {endpoint.description}\n"
        
        if endpoint_model.request_body:
            endpoint_info += "Request Body:\n"
            endpoint_info += f"```json\n{json.dumps(endpoint_model.request_body, indent=2)}\n```\n"
        
        if endpoint_model.request_headers:
            endpoint_info += "Request Headers:\n"
            for header_name, header_info in endpoint_model.request_headers.items():
                required = "required" if header_info.get("required", False) else "optional"
                endpoint_info += f"- {header_name} (in header, {required})\n"
        
        if endpoint_model.request_query_params:
            endpoint_info += "Query Parameters:\n"
            for param_name, param_info in endpoint_model.request_query_params.items():
                required = "required" if param_info.get("required", False) else "optional"
                endpoint_info += f"- {param_name} (in query, {required})\n"
        
        path_parameters = []
        
        if self.schema:
            if endpoint.path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][endpoint.path]
                if "parameters" in path_item:
                    path_parameters.extend(path_item["parameters"])
            
            if endpoint.path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][endpoint.path]
                if endpoint.method.lower() in path_item:
                    operation = path_item[endpoint.method.lower()]
                    if "parameters" in operation:
                        path_parameters.extend(operation["parameters"])

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

        if endpoint_model.responses:
            endpoint_info += "Responses:\n"
            for status, response in endpoint_model.responses.items():
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
        ハイブリッド検索を活用してターゲットエンドポイントに関連するスキーマ情報を取得する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            関連スキーマ情報のテキスト表現
        """
        try:
            # ハイブリッド検索の実行
            hybrid_results = self._perform_hybrid_search(target_endpoint)
            
            if not hybrid_results:
                logger.warning("No relevant schema information found via hybrid search.")
                if self.schema:
                    return self._extract_schema_info_directly(target_endpoint)
                else:
                    return "No relevant schema information found."

            # 検索結果の統合とフォーマット
            return self._format_hybrid_search_results(target_endpoint, hybrid_results)

        except Exception as e:
            logger.error(f"Error during hybrid search for endpoint {target_endpoint.method} {target_endpoint.path}: {e}", exc_info=True)
            
            if self.schema:
                return self._extract_schema_info_directly(target_endpoint)
            else:
                return "Error retrieving relevant schema information."
    
    def _perform_hybrid_search(self, target_endpoint: Endpoint) -> List[Dict]:
        """
        ハイブリッド検索を実行する（ベクトル検索 + 依存関係ベース検索）
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            統合された検索結果のリスト
        """
        hybrid_results = []
        
        # 1. ベクトル検索の実行
        vector_results = self._perform_vector_search(target_endpoint)
        
        # 2. 依存関係ベース検索の実行
        dependency_results = self._perform_dependency_based_search(target_endpoint)
        
        # 3. 検索結果の統合とランキング
        hybrid_results = self._merge_and_rank_results(vector_results, dependency_results, target_endpoint)
        
        return hybrid_results
    
    def _perform_vector_search(self, target_endpoint: Endpoint) -> List[Dict]:
        """
        従来のベクトル検索を実行する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            ベクトル検索結果のリスト
        """
        try:
            # PGVectorManagerのインスタンスを取得
            vectordb_manager = VectorDBManagerFactory.create_default(service_id=self.service_id)

            # 拡張されたクエリの生成
            query = self._build_enhanced_query(target_endpoint)

            # similarity_searchを実行
            docs: List[Document] = vectordb_manager.similarity_search(query, k=5)

            vector_results = []
            for i, doc in enumerate(docs):
                vector_results.append({
                    "source": "vector_search",
                    "rank": i + 1,
                    "score": 1.0 - (i * 0.1),  # 簡易的なスコア計算
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "search_type": "semantic"
                })
            
            return vector_results

        except Exception as e:
            logger.error(f"Error during vector search: {e}", exc_info=True)
            return []
    
    def _perform_dependency_based_search(self, target_endpoint: Endpoint) -> List[Dict]:
        """
        依存関係ベースの構造的検索を実行する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            依存関係ベース検索結果のリスト
        """
        if not self.dependencies or not self.dependency_analyzer:
            return []
        
        dependency_results = []
        
        try:
            # 1. body_reference依存関係の検索
            body_ref_results = self._search_body_reference_dependencies(target_endpoint)
            dependency_results.extend(body_ref_results)
            
            # 2. パスパラメータ依存関係の検索
            path_param_results = self._search_path_parameter_dependencies(target_endpoint)
            dependency_results.extend(path_param_results)
            
            # 3. リソース操作依存関係の検索
            resource_op_results = self._search_resource_operation_dependencies(target_endpoint)
            dependency_results.extend(resource_op_results)
            
            return dependency_results

        except Exception as e:
            logger.error(f"Error during dependency-based search: {e}", exc_info=True)
            return []
    
    def _search_body_reference_dependencies(self, target_endpoint: Endpoint) -> List[Dict]:
        """
        body_reference依存関係に基づく関連エンドポイント検索
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            body_reference依存関係の検索結果
        """
        results = []
        
        # ターゲットエンドポイントに関連するbody_reference依存関係を検索
        for dep in self.dependencies:
            if dep.get("type") == "body_reference":
                target_info = dep.get("target", {})
                source_info = dep.get("source", {})
                
                # ターゲットエンドポイントが依存関係のターゲットと一致する場合
                if (target_info.get("path") == target_endpoint.path and
                    target_info.get("method", "").lower() == target_endpoint.method.lower()):
                    
                    # 依存元エンドポイントの情報を取得
                    source_endpoint_info = self._get_endpoint_info_from_schema(
                        source_info.get("path"),
                        source_info.get("method")
                    )
                    
                    if source_endpoint_info:
                        confidence = dep.get("confidence", 0.8)
                        strength = dep.get("strength", "required")
                        
                        results.append({
                            "source": "dependency_analysis",
                            "rank": 1 if strength == "required" else 2,
                            "score": confidence,
                            "content": source_endpoint_info,
                            "metadata": {
                                "dependency_type": "body_reference",
                                "field": target_info.get("field"),
                                "strength": strength,
                                "confidence": confidence,
                                "source_path": source_info.get("path"),
                                "source_method": source_info.get("method")
                            },
                            "search_type": "structural"
                        })
        
        return results
    
    def _search_path_parameter_dependencies(self, target_endpoint: Endpoint) -> List[Dict]:
        """
        パスパラメータ依存関係に基づく関連エンドポイント検索
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            パスパラメータ依存関係の検索結果
        """
        results = []
        
        for dep in self.dependencies:
            if dep.get("type") == "path_parameter":
                target_info = dep.get("target", {})
                source_info = dep.get("source", {})
                
                # ターゲットエンドポイントが依存関係のターゲットと一致する場合
                if (target_info.get("path") == target_endpoint.path and
                    target_info.get("method", "").lower() == target_endpoint.method.lower()):
                    
                    # 依存元エンドポイントの情報を取得
                    source_endpoint_info = self._get_endpoint_info_from_schema(
                        source_info.get("path"),
                        source_info.get("method")
                    )
                    
                    if source_endpoint_info:
                        results.append({
                            "source": "dependency_analysis",
                            "rank": 1,
                            "score": 0.9,  # パスパラメータ依存関係は高信頼度
                            "content": source_endpoint_info,
                            "metadata": {
                                "dependency_type": "path_parameter",
                                "parameter": target_info.get("parameter"),
                                "source_path": source_info.get("path"),
                                "source_method": source_info.get("method")
                            },
                            "search_type": "structural"
                        })
        
        return results
    
    def _search_resource_operation_dependencies(self, target_endpoint: Endpoint) -> List[Dict]:
        """
        リソース操作依存関係に基づく関連エンドポイント検索
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            リソース操作依存関係の検索結果
        """
        results = []
        
        for dep in self.dependencies:
            if dep.get("type") == "resource_operation":
                target_info = dep.get("target", {})
                source_info = dep.get("source", {})
                
                # ターゲットエンドポイントが依存関係のターゲットと一致する場合
                if (target_info.get("path") == target_endpoint.path and
                    target_info.get("method", "").lower() == target_endpoint.method.lower()):
                    
                    # 依存元エンドポイントの情報を取得
                    source_endpoint_info = self._get_endpoint_info_from_schema(
                        source_info.get("path"),
                        source_info.get("method")
                    )
                    
                    if source_endpoint_info:
                        results.append({
                            "source": "dependency_analysis",
                            "rank": 2,
                            "score": 0.7,  # リソース操作依存関係は中程度の信頼度
                            "content": source_endpoint_info,
                            "metadata": {
                                "dependency_type": "resource_operation",
                                "source_path": source_info.get("path"),
                                "source_method": source_info.get("method")
                            },
                            "search_type": "structural"
                        })
        
        return results
    
    def _get_endpoint_info_from_schema(self, path: str, method: str) -> Optional[str]:
        """
        スキーマから指定されたエンドポイントの情報を取得する
        
        Args:
            path: エンドポイントのパス
            method: HTTPメソッド
            
        Returns:
            エンドポイント情報のテキスト表現
        """
        if not self.schema or not path or not method:
            return None
        
        try:
            paths = self.schema.get("paths", {})
            if path not in paths:
                return None
            
            path_item = paths[path]
            method_lower = method.lower()
            
            if method_lower not in path_item:
                return None
            
            operation = path_item[method_lower]
            
            # エンドポイント情報をフォーマット
            endpoint_info = f"## {method.upper()} {path}\n"
            
            if "summary" in operation:
                endpoint_info += f"**Summary:** {operation['summary']}\n"
            
            if "description" in operation:
                endpoint_info += f"**Description:** {operation['description']}\n"
            
            if "requestBody" in operation:
                endpoint_info += f"**Request Body:**\n```json\n{json.dumps(operation['requestBody'], indent=2)}\n```\n"
            
            if "responses" in operation:
                endpoint_info += f"**Responses:**\n```json\n{json.dumps(operation['responses'], indent=2)}\n```\n"
            
            return endpoint_info
            
        except Exception as e:
            logger.error(f"Error extracting endpoint info for {method} {path}: {e}", exc_info=True)
            return None
    
    def _build_enhanced_query(self, target_endpoint: Endpoint) -> str:
        """
        拡張されたベクトル検索クエリを構築する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            拡張されたクエリ文字列
        """
        query_parts = []
        
        # 基本的なエンドポイント情報
        query_parts.append(f"{target_endpoint.method.upper()} {target_endpoint.path}")
        
        if target_endpoint.summary:
            query_parts.append(target_endpoint.summary)
        
        if target_endpoint.description:
            query_parts.append(target_endpoint.description)
        
        # IDフィールドの抽出と追加
        if target_endpoint.request_body and self.dependency_analyzer:
            try:
                id_fields = self.dependency_analyzer.extract_id_fields(target_endpoint.request_body)
                for field_name in id_fields.keys():
                    # IDフィールドからリソース名を抽出
                    resource_name = self.dependency_analyzer._extract_resource_name(field_name)
                    if resource_name:
                        query_parts.append(f"{resource_name} resource")
                        query_parts.append(f"{field_name} field")
            except Exception as e:
                logger.debug(f"Error extracting ID fields for query enhancement: {e}")
        
        # パスパラメータの抽出
        path_params = re.findall(r'{([^}]+)}', target_endpoint.path)
        for param in path_params:
            query_parts.append(f"{param} parameter")
        
        # リソース名の抽出
        path_parts = target_endpoint.path.strip("/").split("/")
        if path_parts:
            resource_name = path_parts[0]
            query_parts.append(f"{resource_name} resource")
        
        # 操作タイプの追加
        operation_type = self._get_operation_type(target_endpoint.method)
        if operation_type:
            query_parts.append(operation_type)
        
        return " ".join(query_parts)
    
    def _get_operation_type(self, method: str) -> str:
        """
        HTTPメソッドから操作タイプを取得する
        
        Args:
            method: HTTPメソッド
            
        Returns:
            操作タイプの説明
        """
        method_mapping = {
            "GET": "retrieve read fetch",
            "POST": "create add insert",
            "PUT": "update modify replace",
            "PATCH": "update modify partial",
            "DELETE": "remove delete destroy"
        }
        
        return method_mapping.get(method.upper(), "")
    
    def _merge_and_rank_results(self, vector_results: List[Dict], dependency_results: List[Dict], target_endpoint: Endpoint) -> List[Dict]:
        """
        ベクトル検索結果と依存関係ベース検索結果を統合し、ランキングする
        
        Args:
            vector_results: ベクトル検索結果
            dependency_results: 依存関係ベース検索結果
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            統合・ランキングされた検索結果
        """
        all_results = []
        
        # 依存関係ベース検索結果に重み付けを適用（優先度を高く）
        for result in dependency_results:
            result["final_score"] = result["score"] * 1.5  # 依存関係ベースの結果を優遇
            all_results.append(result)
        
        # ベクトル検索結果を追加
        for result in vector_results:
            result["final_score"] = result["score"] * 1.0
            all_results.append(result)
        
        # 重複除去（同じソースからの結果）
        unique_results = self._remove_duplicate_results(all_results)
        
        # 最終スコアでソート
        unique_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        # 最大10件に制限
        return unique_results[:10]
    
    def _remove_duplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        重複する検索結果を除去する
        
        Args:
            results: 検索結果のリスト
            
        Returns:
            重複除去後の検索結果
        """
        seen_content = set()
        unique_results = []
        
        for result in results:
            content_hash = hash(result["content"][:200])  # 最初の200文字でハッシュ化
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _format_hybrid_search_results(self, target_endpoint: Endpoint, hybrid_results: List[Dict]) -> str:
        """
        ハイブリッド検索結果をフォーマットする
        
        Args:
            target_endpoint: ターゲットエンドポイント
            hybrid_results: ハイブリッド検索結果
            
        Returns:
            フォーマットされた検索結果
        """
        if not hybrid_results:
            return "No relevant schema information found."
        
        formatted_parts = []
        
        # 依存関係情報のサマリー
        dependency_info = self._build_dependency_summary(target_endpoint)
        if dependency_info:
            formatted_parts.append(f"## Dependency Analysis Summary\n{dependency_info}\n")
        
        # 検索結果の詳細
        formatted_parts.append(f"## Related Schema Information for {target_endpoint.method.upper()} {target_endpoint.path}\n")
        
        for i, result in enumerate(hybrid_results):
            source_type = result.get("search_type", "unknown")
            score = result.get("final_score", 0.0)
            
            formatted_parts.append(f"### Source {i+1}: {source_type.title()} Search (Score: {score:.2f})")
            
            # メタデータ情報の追加
            metadata = result.get("metadata", {})
            if metadata:
                if metadata.get("dependency_type"):
                    formatted_parts.append(f"**Dependency Type:** {metadata['dependency_type']}")
                if metadata.get("field"):
                    formatted_parts.append(f"**Related Field:** {metadata['field']}")
                if metadata.get("strength"):
                    formatted_parts.append(f"**Dependency Strength:** {metadata['strength']}")
                if metadata.get("confidence"):
                    formatted_parts.append(f"**Confidence:** {metadata['confidence']:.2f}")
            
            formatted_parts.append(f"```\n{result['content']}\n```\n")
        
        return "\n".join(formatted_parts)
    
    def _build_dependency_summary(self, target_endpoint: Endpoint) -> str:
        """
        ターゲットエンドポイントの依存関係サマリーを構築する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            依存関係サマリーのテキスト
        """
        if not self.dependencies:
            return ""
        
        relevant_deps = []
        
        for dep in self.dependencies:
            target_info = dep.get("target", {})
            if (target_info.get("path") == target_endpoint.path and
                target_info.get("method", "").lower() == target_endpoint.method.lower()):
                relevant_deps.append(dep)
        
        if not relevant_deps:
            return ""
        
        summary_parts = []
        
        for dep in relevant_deps:
            dep_type = dep.get("type", "unknown")
            source_info = dep.get("source", {})
            
            if dep_type == "body_reference":
                field = dep.get("target", {}).get("field", "unknown")
                strength = dep.get("strength", "unknown")
                confidence = dep.get("confidence", 0.0)
                summary_parts.append(
                    f"- **{field}** field requires {source_info.get('method', '').upper()} {source_info.get('path', '')} "
                    f"(strength: {strength}, confidence: {confidence:.2f})"
                )
            elif dep_type == "path_parameter":
                param = dep.get("target", {}).get("parameter", "unknown")
                summary_parts.append(
                    f"- **{param}** parameter depends on {source_info.get('method', '').upper()} {source_info.get('path', '')}"
                )
            elif dep_type == "resource_operation":
                summary_parts.append(
                    f"- Resource operation depends on {source_info.get('method', '').upper()} {source_info.get('path', '')}"
                )
        
        if summary_parts:
            return "**Detected Dependencies:**\n" + "\n".join(summary_parts)
        
        return ""
    
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
        endpoint_model = EndpointSchema.from_orm(target_endpoint)
        
        try:
            if endpoint_model.path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][endpoint_model.path]
                relevant_info_parts.append(f"## Path: {endpoint_model.path}")
                relevant_info_parts.append(f"```json\n{json.dumps(path_item, indent=2)}\n```\n")
            
            if endpoint_model.request_body:
                for content_type, content in endpoint_model.request_body.get("content", {}).items():
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
            
            if endpoint_model.responses:
                for status, response in endpoint_model.responses.items():
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
            
            if "components" in self.schema and "schemas" in self.schema["components"]:
                path_parts = endpoint_model.path.strip("/").split("/")
                resource_name = path_parts[0] if path_parts else ""
                
                for schema_name, schema in self.schema["components"]["schemas"].items():
                    if resource_name.lower() in schema_name.lower():
                        relevant_info_parts.append(f"## Related Component Schema: {schema_name}")
                        relevant_info_parts.append(f"```json\n{json.dumps(schema, indent=2)}\n```\n")
            
            relevant_info = "\n".join(relevant_info_parts)
            
            if not relevant_info.strip():
                return "No relevant schema information found through direct extraction."
            
            return f"""
# Relevant Schema Information for {endpoint_model.method.upper()} {endpoint_model.path} (Direct Extraction)

{relevant_info}
"""
        except Exception as e:
            logger.error(f"Error during direct schema extraction for endpoint {endpoint_model.method} {endpoint_model.path}: {e}", exc_info=True)
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
        
        chain_name = f"Test for {method} {path}"
        
        steps = []
        
        path_params = []
        param_pattern = r'\{([^}]+)\}'
        import re
        path_params = re.findall(param_pattern, path)
        
        for param in path_params:
            param_type = "id"
            resource_name = "resource"
            
            path_parts = path.strip('/').split('/')
            if len(path_parts) > 0:
                resource_name = path_parts[0]
                if resource_name.endswith('s'):
                    resource_name = resource_name[:-1]
            
            if param.endswith('_id') or param == 'id':
                param_parts = param.split('_')
                if len(param_parts) > 1 and param_parts[-1] == 'id':
                    resource_name = '_'.join(param_parts[:-1])
            
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
        
        target_step = {
            "method": method,
            "path": path,
            "request": {}
        }
        
        if method in ["POST", "PUT", "PATCH"]:
            if target_endpoint.request_body and "content" in target_endpoint.request_body:
                for content_type, content in target_endpoint.request_body["content"].items():
                    if "application/json" in content_type and "schema" in content:
                        target_step["request"]["headers"] = {"Content-Type": "application/json"}
                        sample_body = self._generate_sample_body_from_schema(content["schema"])
                        target_step["request"]["body"] = sample_body
                        break
            else:
                target_step["request"]["headers"] = {"Content-Type": "application/json"}
                target_step["request"]["body"] = {"name": "Test name", "description": "Test description"}
        
        steps.append(target_step)
        
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
        
        if "$ref" in schema:
            return {"name": "Test name", "description": "Test description"}
        
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
        
        if not sample_body:
            sample_body = {"name": "Test name", "description": "Test description"}
        
        return sample_body
    
    def _build_dependency_aware_context(self, target_endpoint: Endpoint, target_endpoint_info: str,
                                      relevant_schema_info: str, error_types_instruction: str) -> Dict:
        """
        依存関係対応プロンプト用のコンテキストを構築する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            target_endpoint_info: ターゲットエンドポイント情報
            relevant_schema_info: 関連スキーマ情報
            error_types_instruction: エラータイプ指示
            
        Returns:
            依存関係対応プロンプト用のコンテキスト
        """
        # 依存関係グラフの構築
        dependency_graph = self._build_dependency_graph_text(target_endpoint)
        
        # 実行順序の決定
        execution_order = self._determine_execution_order(target_endpoint)
        
        # ターゲットエンドポイント情報の構築
        target_endpoint_text = f"{target_endpoint.method.upper()} {target_endpoint.path}"
        if target_endpoint.summary:
            target_endpoint_text += f"\nSummary: {target_endpoint.summary}"
        if target_endpoint.description:
            target_endpoint_text += f"\nDescription: {target_endpoint.description}"
        
        return {
            "dependency_graph": dependency_graph,
            "target_endpoint": target_endpoint_text,
            "relevant_schema_info": relevant_schema_info,
            "execution_order": execution_order,
            "error_types_instruction": error_types_instruction
        }
    
    def _build_dependency_graph_text(self, target_endpoint: Endpoint) -> str:
        """
        ターゲットエンドポイントの依存関係グラフをテキスト形式で構築する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            依存関係グラフのテキスト表現
        """
        if not self.dependencies:
            return "No dependencies detected."
        
        relevant_deps = []
        for dep in self.dependencies:
            target_info = dep.get("target", {})
            if (target_info.get("path") == target_endpoint.path and
                target_info.get("method", "").lower() == target_endpoint.method.lower()):
                relevant_deps.append(dep)
        
        if not relevant_deps:
            return "No dependencies detected for this endpoint."
        
        graph_parts = []
        graph_parts.append("**Dependency Graph:**")
        
        for i, dep in enumerate(relevant_deps, 1):
            dep_type = dep.get("type", "unknown")
            source_info = dep.get("source", {})
            target_info = dep.get("target", {})
            
            source_endpoint = f"{source_info.get('method', '').upper()} {source_info.get('path', '')}"
            target_endpoint_str = f"{target_info.get('method', '').upper()} {target_info.get('path', '')}"
            
            if dep_type == "body_reference":
                field = target_info.get("field", "unknown")
                strength = dep.get("strength", "unknown")
                confidence = dep.get("confidence", 0.0)
                graph_parts.append(
                    f"{i}. **{source_endpoint}** → **{target_endpoint_str}**"
                    f"\n   - Type: Body Reference"
                    f"\n   - Field: `{field}`"
                    f"\n   - Strength: {strength}"
                    f"\n   - Confidence: {confidence:.2f}"
                )
            elif dep_type == "path_parameter":
                param = target_info.get("parameter", "unknown")
                graph_parts.append(
                    f"{i}. **{source_endpoint}** → **{target_endpoint_str}**"
                    f"\n   - Type: Path Parameter"
                    f"\n   - Parameter: `{param}`"
                )
            elif dep_type == "resource_operation":
                graph_parts.append(
                    f"{i}. **{source_endpoint}** → **{target_endpoint_str}**"
                    f"\n   - Type: Resource Operation"
                )
            else:
                graph_parts.append(
                    f"{i}. **{source_endpoint}** → **{target_endpoint_str}**"
                    f"\n   - Type: {dep_type}"
                )
        
        return "\n\n".join(graph_parts)
    
    def _validate_and_normalize_dependency_aware_response(self, suite_data: Dict, target_endpoint: Endpoint) -> Dict:
        """
        依存関係対応プロンプトのレスポンスを検証し、標準形式に正規化する
        
        Args:
            suite_data: LLMからのレスポンスデータ
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            正規化されたTestSuiteデータ
            
        Raises:
            ValueError: レスポンス構造が不正な場合
        """
        if not isinstance(suite_data, dict):
            raise ValueError("LLM response must be a dictionary")
        
        # 依存関係対応プロンプトの場合、dependency_infoフィールドが含まれる可能性がある
        if "dependency_info" in suite_data:
            logger.info(f"Dependency info detected in LLM response: {suite_data.get('dependency_info')}")
        
        # 必須フィールドの確認と正規化
        normalized_data = {}
        
        # nameフィールドの処理
        if "name" not in suite_data:
            normalized_data["name"] = f"{target_endpoint.method.upper()} {target_endpoint.path} Test Suite"
        else:
            normalized_data["name"] = suite_data["name"]
        
        # target_methodとtarget_pathの処理
        if "target_method" not in suite_data:
            normalized_data["target_method"] = target_endpoint.method.upper()
        else:
            normalized_data["target_method"] = suite_data["target_method"]
            
        if "target_path" not in suite_data:
            normalized_data["target_path"] = target_endpoint.path
        else:
            normalized_data["target_path"] = suite_data["target_path"]
        
        # test_casesフィールドの処理
        if "test_cases" not in suite_data or not isinstance(suite_data["test_cases"], list):
            raise ValueError("LLM response must contain 'test_cases' as a list")
        
        normalized_data["test_cases"] = suite_data["test_cases"]
        
        # dependency_infoがある場合は保持
        if "dependency_info" in suite_data:
            normalized_data["dependency_info"] = suite_data["dependency_info"]
        
        return normalized_data
    
    def _normalize_step_data_fields(self, step_data: Dict) -> Dict:
        """
        TestStepデータのフィールドを正規化し、Pydanticシリアライゼーション警告を回避する
        
        Args:
            step_data: TestStepデータ
            
        Returns:
            正規化されたTestStepデータ
        """
        import json
        
        normalized_step = step_data.copy()
        
        # 文字列として格納されたJSONデータを辞書に変換
        json_fields = ["request_headers", "request_body", "request_params", "extract_rules"]
        
        for field in json_fields:
            if field in normalized_step:
                value = normalized_step[field]
                
                # 文字列の場合はJSONとしてパース
                if isinstance(value, str):
                    try:
                        if value.strip() in ["None", "null", ""]:
                            normalized_step[field] = {}
                        elif value.strip() == "{}":
                            normalized_step[field] = {}
                        else:
                            parsed_value = json.loads(value)
                            normalized_step[field] = parsed_value if parsed_value is not None else {}
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse {field} as JSON: {value}, using empty dict")
                        normalized_step[field] = {}
                # Noneの場合は空辞書に変換
                elif value is None:
                    normalized_step[field] = {}
                # 既に辞書の場合はそのまま
                elif isinstance(value, dict):
                    normalized_step[field] = value
                else:
                    logger.warning(f"Unexpected type for {field}: {type(value)}, using empty dict")
                    normalized_step[field] = {}
        
        return normalized_step
    
    def _determine_execution_order(self, target_endpoint: Endpoint) -> str:
        """
        依存関係に基づく実行順序を決定する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            実行順序のテキスト表現
        """
        if not self.dependencies:
            return f"1. {target_endpoint.method.upper()} {target_endpoint.path} (target endpoint)"
        
        # 依存関係の解析
        relevant_deps = []
        for dep in self.dependencies:
            target_info = dep.get("target", {})
            if (target_info.get("path") == target_endpoint.path and
                target_info.get("method", "").lower() == target_endpoint.method.lower()):
                relevant_deps.append(dep)
        
        if not relevant_deps:
            return f"1. {target_endpoint.method.upper()} {target_endpoint.path} (target endpoint)"
        
        # 実行順序の構築
        execution_steps = []
        step_counter = 1
        
        # 必須依存関係を優先的に処理
        required_deps = [dep for dep in relevant_deps if dep.get("strength") == "required"]
        optional_deps = [dep for dep in relevant_deps if dep.get("strength") != "required"]
        
        # 必須依存関係の処理
        for dep in required_deps:
            source_info = dep.get("source", {})
            source_endpoint = f"{source_info.get('method', '').upper()} {source_info.get('path', '')}"
            
            dep_type = dep.get("type", "unknown")
            if dep_type == "body_reference":
                field = dep.get("target", {}).get("field", "unknown")
                purpose = f"Create resource for {field} field"
            elif dep_type == "path_parameter":
                param = dep.get("target", {}).get("parameter", "unknown")
                purpose = f"Create resource for {param} parameter"
            else:
                purpose = "Setup prerequisite resource"
            
            execution_steps.append(f"{step_counter}. **{source_endpoint}** - {purpose}")
            step_counter += 1
        
        # 高信頼度の任意依存関係の処理
        high_confidence_optional = [dep for dep in optional_deps if dep.get("confidence", 0.0) > 0.8]
        for dep in high_confidence_optional:
            source_info = dep.get("source", {})
            source_endpoint = f"{source_info.get('method', '').upper()} {source_info.get('path', '')}"
            
            execution_steps.append(f"{step_counter}. **{source_endpoint}** - Optional high-confidence dependency")
            step_counter += 1
        
        # ターゲットエンドポイント
        execution_steps.append(f"{step_counter}. **{target_endpoint.method.upper()} {target_endpoint.path}** - Target endpoint execution")
        
        return "\n".join(execution_steps)


class EnhancedEndpointChainGenerator(EndpointChainGenerator):
    """
    ハイブリッド検索機能を持つ拡張されたエンドポイントチェーンジェネレータ
    
    MEMO.mdのフェーズ2で定義されたハイブリッド検索アルゴリズムを実装し、
    ベクトル検索と依存関係ベースの構造的検索を組み合わせて、
    より精度の高い関連エンドポイント情報の取得を実現します。
    """
    
    def __init__(self, service_id: int, endpoints: List[Endpoint], schema: Dict = None, error_types: Optional[List[str]] = None):
        """
        拡張されたエンドポイントチェーンジェネレータの初期化
        
        Args:
            service_id: サービスID
            endpoints: 選択されたエンドポイントのリスト
            schema: OpenAPIスキーマ（オプション）
            error_types: エラータイプのリスト（オプション）
        """
        super().__init__(service_id, endpoints, schema, error_types)
        
        # ハイブリッド検索の設定
        self.hybrid_search_enabled = True
        self.vector_search_weight = 1.0
        self.dependency_search_weight = 1.5
        self.max_results = 10
        
        logger.info(f"EnhancedEndpointChainGenerator initialized with {len(self.dependencies)} dependencies")
    
    def generate_enhanced_embeddings(self, endpoint: Endpoint) -> str:
        """
        スキーマ構造情報を含む拡張埋め込みベクトル用のテキストを生成する
        
        Args:
            endpoint: エンドポイント情報
            
        Returns:
            拡張埋め込み用のテキスト
        """
        embedding_parts = []
        
        # 基本的なエンドポイント情報
        embedding_parts.append(f"{endpoint.method.upper()} {endpoint.path}")
        
        if endpoint.summary:
            embedding_parts.append(f"Summary: {endpoint.summary}")
        
        if endpoint.description:
            embedding_parts.append(f"Description: {endpoint.description}")
        
        # スキーマフィールド情報の追加
        if endpoint.request_body and self.dependency_analyzer:
            try:
                id_fields = self.dependency_analyzer.extract_id_fields(endpoint.request_body)
                for field_name, field_info in id_fields.items():
                    embedding_parts.append(f"ID Field: {field_name}")
                    
                    # リソース名の抽出
                    resource_name = self.dependency_analyzer._extract_resource_name(field_name)
                    if resource_name:
                        embedding_parts.append(f"Related Resource: {resource_name}")
            except Exception as e:
                logger.debug(f"Error extracting ID fields for embedding: {e}")
        
        # 依存関係情報の追加
        for dep in self.dependencies:
            target_info = dep.get("target", {})
            source_info = dep.get("source", {})
            
            if (target_info.get("path") == endpoint.path and
                target_info.get("method", "").lower() == endpoint.method.lower()):
                
                dep_type = dep.get("type", "unknown")
                embedding_parts.append(f"Dependency: {dep_type}")
                embedding_parts.append(f"Depends on: {source_info.get('method', '').upper()} {source_info.get('path', '')}")
                
                if dep_type == "body_reference":
                    field = target_info.get("field", "")
                    if field:
                        embedding_parts.append(f"Required Field: {field}")
        
        # パスパラメータ情報
        path_params = re.findall(r'{([^}]+)}', endpoint.path)
        for param in path_params:
            embedding_parts.append(f"Path Parameter: {param}")
        
        # リソース情報
        path_parts = endpoint.path.strip("/").split("/")
        if path_parts:
            resource_name = path_parts[0]
            embedding_parts.append(f"Resource: {resource_name}")
        
        return " | ".join(embedding_parts)
    
    def hybrid_search(self, query_endpoint: Endpoint) -> List[Dict]:
        """
        ハイブリッド検索の実装
        
        Args:
            query_endpoint: 検索対象のエンドポイント
            
        Returns:
            ハイブリッド検索結果のリスト
        """
        if not self.hybrid_search_enabled:
            # ハイブリッド検索が無効の場合は従来の検索を使用
            return self._perform_vector_search(query_endpoint)
        
        try:
            # ハイブリッド検索の実行
            hybrid_results = self._perform_hybrid_search(query_endpoint)
            
            logger.info(f"Hybrid search returned {len(hybrid_results)} results for {query_endpoint.method} {query_endpoint.path}")
            
            return hybrid_results
            
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}", exc_info=True)
            # エラーが発生した場合はベクトル検索のみを実行
            return self._perform_vector_search(query_endpoint)
    
    def get_dependency_chain_info(self, target_endpoint: Endpoint) -> Dict:
        """
        依存関係チェーン情報を取得する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            依存関係チェーン情報
        """
        chain_info = {
            "target_endpoint": f"{target_endpoint.method.upper()} {target_endpoint.path}",
            "dependencies": [],
            "execution_order": [],
            "confidence_score": 0.0,
            "warnings": []
        }
        
        if not self.dependencies:
            chain_info["warnings"].append("No dependencies detected")
            return chain_info
        
        # ターゲットエンドポイントに関連する依存関係を抽出
        relevant_deps = []
        for dep in self.dependencies:
            target_info = dep.get("target", {})
            if (target_info.get("path") == target_endpoint.path and
                target_info.get("method", "").lower() == target_endpoint.method.lower()):
                relevant_deps.append(dep)
        
        if not relevant_deps:
            chain_info["warnings"].append("No dependencies found for this endpoint")
            return chain_info
        
        # 依存関係情報の構築
        total_confidence = 0.0
        for dep in relevant_deps:
            dep_info = {
                "type": dep.get("type", "unknown"),
                "source": dep.get("source", {}),
                "target": dep.get("target", {}),
                "strength": dep.get("strength", "unknown"),
                "confidence": dep.get("confidence", 0.0)
            }
            chain_info["dependencies"].append(dep_info)
            total_confidence += dep.get("confidence", 0.0)
        
        # 平均信頼度の計算
        if relevant_deps:
            chain_info["confidence_score"] = total_confidence / len(relevant_deps)
        
        # 実行順序の決定
        execution_order = self._build_execution_order_list(target_endpoint, relevant_deps)
        chain_info["execution_order"] = execution_order
        
        # 循環参照のチェック
        if self.dependency_analyzer:
            circular_deps = self.dependency_analyzer.check_circular_dependencies(self.dependencies)
            if len(circular_deps) != len(self.dependencies):
                chain_info["warnings"].append("Circular dependencies detected")
        
        return chain_info
    
    def _build_execution_order_list(self, target_endpoint: Endpoint, relevant_deps: List[Dict]) -> List[Dict]:
        """
        実行順序のリストを構築する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            relevant_deps: 関連する依存関係のリスト
            
        Returns:
            実行順序のリスト
        """
        execution_order = []
        
        # 必須依存関係を優先的に処理
        required_deps = [dep for dep in relevant_deps if dep.get("strength") == "required"]
        optional_deps = [dep for dep in relevant_deps if dep.get("strength") != "required"]
        
        step_counter = 1
        
        # 必須依存関係の処理
        for dep in required_deps:
            source_info = dep.get("source", {})
            
            execution_order.append({
                "step": step_counter,
                "endpoint": f"{source_info.get('method', '').upper()} {source_info.get('path', '')}",
                "purpose": self._get_dependency_purpose(dep),
                "required": True,
                "confidence": dep.get("confidence", 0.0)
            })
            step_counter += 1
        
        # 高信頼度の任意依存関係の処理
        high_confidence_optional = [dep for dep in optional_deps if dep.get("confidence", 0.0) > 0.8]
        for dep in high_confidence_optional:
            source_info = dep.get("source", {})
            
            execution_order.append({
                "step": step_counter,
                "endpoint": f"{source_info.get('method', '').upper()} {source_info.get('path', '')}",
                "purpose": self._get_dependency_purpose(dep),
                "required": False,
                "confidence": dep.get("confidence", 0.0)
            })
            step_counter += 1
        
        # ターゲットエンドポイント
        execution_order.append({
            "step": step_counter,
            "endpoint": f"{target_endpoint.method.upper()} {target_endpoint.path}",
            "purpose": "Target endpoint execution",
            "required": True,
            "confidence": 1.0
        })
        
        return execution_order
    
    def _get_dependency_purpose(self, dep: Dict) -> str:
        """
        依存関係の目的を取得する
        
        Args:
            dep: 依存関係情報
            
        Returns:
            依存関係の目的説明
        """
        dep_type = dep.get("type", "unknown")
        
        if dep_type == "body_reference":
            field = dep.get("target", {}).get("field", "unknown")
            return f"Create resource for {field} field"
        elif dep_type == "path_parameter":
            param = dep.get("target", {}).get("parameter", "unknown")
            return f"Create resource for {param} parameter"
        elif dep_type == "resource_operation":
            return "Setup prerequisite resource operation"
        else:
            return f"Setup {dep_type} dependency"
    
    def get_search_quality_metrics(self, target_endpoint: Endpoint) -> Dict:
        """
        検索品質のメトリクスを取得する
        
        Args:
            target_endpoint: ターゲットエンドポイント
            
        Returns:
            検索品質メトリクス
        """
        metrics = {
            "endpoint": f"{target_endpoint.method.upper()} {target_endpoint.path}",
            "vector_search_results": 0,
            "dependency_search_results": 0,
            "hybrid_search_results": 0,
            "dependency_coverage": 0.0,
            "confidence_score": 0.0,
            "search_effectiveness": "unknown"
        }
        
        try:
            # ベクトル検索結果の取得
            vector_results = self._perform_vector_search(target_endpoint)
            metrics["vector_search_results"] = len(vector_results)
            
            # 依存関係ベース検索結果の取得
            dependency_results = self._perform_dependency_based_search(target_endpoint)
            metrics["dependency_search_results"] = len(dependency_results)
            
            # ハイブリッド検索結果の取得
            hybrid_results = self._perform_hybrid_search(target_endpoint)
            metrics["hybrid_search_results"] = len(hybrid_results)
            
            # 依存関係カバレッジの計算
            relevant_deps = [dep for dep in self.dependencies
                           if (dep.get("target", {}).get("path") == target_endpoint.path and
                               dep.get("target", {}).get("method", "").lower() == target_endpoint.method.lower())]
            
            if relevant_deps:
                covered_deps = len([dep for dep in relevant_deps if dep.get("confidence", 0.0) > 0.5])
                metrics["dependency_coverage"] = covered_deps / len(relevant_deps)
                
                # 平均信頼度の計算
                total_confidence = sum(dep.get("confidence", 0.0) for dep in relevant_deps)
                metrics["confidence_score"] = total_confidence / len(relevant_deps)
            
            # 検索効果の評価
            if metrics["hybrid_search_results"] > metrics["vector_search_results"]:
                metrics["search_effectiveness"] = "improved"
            elif metrics["hybrid_search_results"] == metrics["vector_search_results"]:
                metrics["search_effectiveness"] = "equivalent"
            else:
                metrics["search_effectiveness"] = "degraded"
            
        except Exception as e:
            logger.error(f"Error calculating search quality metrics: {e}", exc_info=True)
            metrics["search_effectiveness"] = "error"
        
        return metrics
