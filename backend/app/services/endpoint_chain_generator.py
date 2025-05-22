from typing import List, Dict, Optional
import json
import os
from app.models import Endpoint
from app.schemas.service import Endpoint as EndpointSchema 
from app.services.rag import EmbeddingFunctionForCaseforge
from app.config import settings
from app.logging_config import logger
from langchain_community.vectorstores import FAISS
from app.utils.path_manager import path_manager

class EndpointChainGenerator:
    """選択されたエンドポイントからテストチェーンを生成するクラス"""
    
    def __init__(self, service_id: str, endpoints: List[Endpoint], schema: Dict = None, error_types: Optional[List[str]] = None): # error_types 引数を追加
        """
        Args:
            service_id: サービスID
            endpoints: 選択されたエンドポイントのリスト
            schema: OpenAPIスキーマ（オプション）
        """
        self.service_id = service_id
        self.endpoints = endpoints
        self.schema = schema
        self.error_types = error_types
    
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
        
        logger.info(f"Using LLM model: {model_name}")
        
        try:
            llm_client = LLMClientFactory.create(
                provider_type=LLMProviderType.LOCAL,
                model_name=model_name,
                temperature=0.2,
            )
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing LLM client: {e}", exc_info=True)
            raise
        
        try:
            prompt_template = get_prompt_template("endpoint_test_generation")
            logger.info("Using endpoint_test_generation prompt template from registry")
        except KeyError:
            logger.warning("endpoint_test_generation prompt template not found, using hardcoded prompt")
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
        }}
      ]
    }}
  ]
}}
````

**Instructions (MUST FOLLOW STRICTLY):**
0. Each test step must include **all** of the following keys: `method`, `path`, `request_headers`, `request_body`, `request_params`, `extract_rules`, `expected_status`. Even if values are empty, all keys must be present.
1. Use appropriate JSONPath expressions in `extract_rules` to capture IDs or other values from previous responses.
2. Use the extracted values in subsequent steps (e.g., in path parameters or request body).
3. The **final step of each test case must always be the target endpoint call**.
4. Ensure logical, realistic sequences of steps (e.g., create resource → update → assert).
5. The output must be **a single valid JSON object**, and **nothing else** (no comments, no explanation).
6. Generate one test suite **per target endpoint**.
7. Include both the HTTP method and path in the test suite’s `"name"` field.
8. For each test case, the `"name"` field should indicate the case type (e.g., "Normal case", "Invalid input").
9. Use the appropriate `error_type` for abnormal cases: `"missing_field"`, `"invalid_input"`, `"unauthorized"`, `"not_found"`, etc. Use `null` for normal cases.
"""
            prompt_template = prompt_template_str

        error_types_instruction = "以下の異常系の種類（missing_field, invalid_input, unauthorized, not_found など）"
        if self.error_types and len(self.error_types) > 0:
            error_types_instruction = f"以下の異常系の種類（{', '.join(self.error_types)}）"
            logger.info(f"Generating tests with specific error types: {self.error_types}")
        
        for target_endpoint in self.endpoints:
            logger.info(f"Generating chain for endpoint: {target_endpoint.method} {target_endpoint.path}")
            
            try:
                target_endpoint_info = self._build_endpoint_context(target_endpoint)
                
                relevant_schema_info = self._get_relevant_schema_info(target_endpoint)
                
                context = {
                    "target_endpoint_info": target_endpoint_info,
                    "relevant_schema_info": relevant_schema_info,
                    "error_types_instruction": error_types_instruction
                }
                
                logger.info(f"Invoking LLM for endpoint {target_endpoint.method} {target_endpoint.path}")
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
                    
                    logger.info(f"LLM response received for {target_endpoint.method} {target_endpoint.path}")
                
                except (LLMException, LLMResponseFormatException) as llm_error:
                    logger.error(f"Error invoking LLM for endpoint {target_endpoint.method} {target_endpoint.path}: {llm_error}", exc_info=True)
                    logger.info(f"Generating fallback test chain for {target_endpoint.method} {target_endpoint.path}")
                    chain = self._generate_fallback_chain(target_endpoint)
                    generated_chains.append(chain)
                    logger.info(f"Added fallback chain for {target_endpoint.method} {target_endpoint.path}")
                    continue
                
                try:
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

                    if 'target_method' not in suite_data or suite_data['target_method'] is None:
                        suite_data['target_method'] = target_endpoint.method
                        logger.warning(f"target_method not found in LLM response, using endpoint method: {target_endpoint.method}")
                    if 'target_path' not in suite_data or suite_data['target_path'] is None:
                        suite_data['target_path'] = target_endpoint.path
                        logger.warning(f"target_path not found in LLM response, using endpoint path: {target_endpoint.path}")

                    generated_chains.append(suite_data)
                    logger.info(f"Successfully generated test suite for {target_endpoint.method} {target_endpoint.path} with {len(suite_data.get('test_cases', []))} test cases")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response as JSON for {target_endpoint.method} {target_endpoint.path}: {e}")
                    try:
                        import re
                        json_match = re.search(r'```json\s*(.*?)\s*```', suite_data, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            suite_data = json.loads(json_str)
                            logger.error(f"Raw response json: {suite_data}")

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
                            logger.info(f"Successfully extracted and parsed JSON from markdown code block for {target_endpoint.method} {target_endpoint.path}")
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
        RAGを活用してターゲットエンドポイントに関連するスキーマ情報を取得する
        
        Args:
            target_endpoint: ターゲットとなるエンドポイント
            
        Returns:
            関連スキーマ情報のテキスト表現
        """
        try:
            faiss_path = path_manager.get_faiss_dir(self.service_id, temp=False)
            
            if not path_manager.exists(faiss_path):
                tmp_faiss_path = path_manager.get_faiss_dir(self.service_id, temp=True)
                if path_manager.exists(tmp_faiss_path):
                    logger.info(f"FAISS vector DB found in temporary directory: {tmp_faiss_path}")
                    faiss_path = tmp_faiss_path
                else:
                    logger.warning(f"FAISS vector DB not found for service {self.service_id} at {faiss_path} or {tmp_faiss_path}. Cannot perform RAG search.")
                    
                    if self.schema:
                        logger.info(f"Using schema directly for endpoint {target_endpoint.method} {target_endpoint.path}")
                        return self._extract_schema_info_directly(target_endpoint)
                    else:
                        return "No relevant schema information found."
            
            logger.info(f"Loading FAISS vector DB from {faiss_path}")
            embedding_fn = EmbeddingFunctionForCaseforge()
            
            try:
                vectordb = FAISS.load_local(faiss_path, embedding_fn, allow_dangerous_deserialization=True)
                logger.info(f"Successfully loaded FAISS vector DB from {faiss_path}")
            except Exception as load_error:
                logger.error(f"Error loading FAISS vector DB from {faiss_path}: {load_error}", exc_info=True)
                
                if self.schema:
                    logger.info(f"Falling back to direct schema extraction due to FAISS load error")
                    return self._extract_schema_info_directly(target_endpoint)
                else:
                    return "Error loading vector database. No relevant schema information found."

            query = f"{target_endpoint.method.upper()} {target_endpoint.path} {target_endpoint.summary or ''} {target_endpoint.description or ''}"
            if target_endpoint.request_body:
                 query += f" Request Body: {json.dumps(target_endpoint.request_body)}"
            if target_endpoint.request_headers:
                 query += f" Request Headers: {json.dumps(target_endpoint.request_headers)}"
            if target_endpoint.request_query_params:
                 query += f" Query Parameters: {json.dumps(target_endpoint.request_query_params)}"
            if target_endpoint.responses:
                 query += f" Responses: {json.dumps(target_endpoint.responses)}"

            docs = vectordb.similarity_search(query, k=5)

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
