"""
プロンプトテンプレート管理モジュール

このモジュールは、サービス内で使用されるプロンプトテンプレートを集約し、
再利用可能な形で管理します。
"""

from typing import Dict, Any, Optional
import os
import json
import yaml
from pathlib import Path

from app.logging_config import logger


class PromptTemplate:
    """プロンプトテンプレートクラス"""
    
    def __init__(self, template: str, metadata: Optional[Dict[str, Any]] = None):
        """
        プロンプトテンプレートの初期化
        
        Args:
            template: テンプレート文字列
            metadata: テンプレートに関するメタデータ
        """
        self.template = template
        self.metadata = metadata or {}
    
    def format(self, **kwargs) -> str:
        """
        テンプレートを変数で埋める
        
        Args:
            **kwargs: テンプレートに埋め込む変数
            
        Returns:
            フォーマット済みのプロンプト
        """
        return self.template.format(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        テンプレートを辞書形式に変換
        
        Returns:
            テンプレートの辞書表現
        """
        return {
            "template": self.template,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptTemplate':
        """
        辞書からテンプレートを作成
        
        Args:
            data: テンプレートの辞書表現
        
        Returns:
            プロンプトテンプレート
        """
        return cls(
            template=data["template"],
            metadata=data.get("metadata", {})
        )


class PromptTemplateRegistry:
    """プロンプトテンプレートレジストリ"""
    
    def __init__(self):
        """プロンプトテンプレートレジストリの初期化"""
        self._templates: Dict[str, PromptTemplate] = {}
        self._loaded = False
    
    def register(self, name: str, template: PromptTemplate) -> None:
        """
        テンプレートを登録
        
        Args:
            name: テンプレート名
            template: プロンプトテンプレート
        """
        self._templates[name] = template
    
    def get(self, name: str) -> PromptTemplate:
        """
        テンプレートを取得
        
        Args:
            name: テンプレート名
            
        Returns:
            プロンプトテンプレート
            
        Raises:
            KeyError: テンプレートが見つからない場合
        """
        if not self._loaded:
            self.load_default_templates()
        
        if name not in self._templates:
            raise KeyError(f"Template not found: {name}")
        
        return self._templates[name]
    
    def load_from_file(self, path: str) -> None:
        """
        ファイルからテンプレートを読み込む
        
        Args:
            path: テンプレートファイルのパス
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.endswith((".yaml", ".yml")):
                    templates_data = yaml.safe_load(f)
                elif path.endswith(".json"):
                    templates_data = json.load(f)
                else:
                    raise ValueError("Unsupported file format. Must be .yaml, .yml, or .json")
            
            for name, data in templates_data.items():
                if isinstance(data, str):
                    self.register(name, PromptTemplate(data))
                elif isinstance(data, dict):
                    self.register(name, PromptTemplate.from_dict(data))
                else:
                    logger.warning(f"Invalid template data for {name}: {data}")
        
        except Exception as e:
            logger.error(f"Error loading templates from {path}: {e}", exc_info=True)
            raise
    
    def load_from_directory(self, directory: str) -> None:
        """
        ディレクトリからテンプレートを読み込む
        
        Args:
            directory: テンプレートディレクトリのパス
        """
        try:
            for file_path in Path(directory).glob("*.{yaml,yml,json}"):
                self.load_from_file(str(file_path))
        except Exception as e:
            logger.error(f"Error loading templates from directory {directory}: {e}", exc_info=True)
            raise
    
    def load_default_templates(self) -> None:
        """デフォルトのテンプレートを読み込む"""
        self._loaded = True
        
        self.register("test_suite_generation", PromptTemplate(
            template="""You are an expert in API testing. Please use the following OpenAPI endpoint information:
{context}

Based on this endpoint definition, generate a **TestSuite** in JSON format. The suite should contain multiple **TestCases**, including:
- at least one successful (happy path) test case
- and at least the following error test cases: {error_types_instruction}

Each test case should be composed of a sequence of **TestSteps**, where each step represents one API request and its expected response. 
If a test requires any data dependency (e.g., using an ID from a previous response), include **setup steps** to create the necessary resources (e.g., a user before creating an article).  
Extract required values using variables and reuse them in the subsequent steps. This includes query parameters, path parameters, or fields in request bodies.

You must strictly follow the format below.  
**Only return a valid JSON object. Do not include any explanations, comments, code blocks, or markdown. Only the JSON itself.**

```json
{{
  "name": "Name of the test suite",
  "description": "Description of the test suite",
  "test_cases": [
    {{
      "name": "Test case name",
      "description": "Test case description",
      "type": "Positive" or "Negative",
      "steps": [
        {{
          "name": "Step name",
          "description": "Step description",
          "request": {{
            "method": "HTTP method",
            "path": "API path",
            "headers": {{
              "Header name": "Header value"
            }},
            "query_params": {{
              "Query params name": "Query params value"
            }},
            "path_params": {{
              "Path params name": "Path params value"
            }},
            "body": {{
              // JSON-formatted request body
            }}
          }},
          "expected_response": {{
            "status_code": HTTP status code,
            "headers": {{
              "Header name": "Expected header value"
            }},
            "body": {{
              // JSON-formatted expected response body
              // Focus on specific field values or presence
            }}
          }},
          "validation": [
            {{
              "type": "Validation type", // "json_path", "header", "status_code" etc.
              "target": "Validation target", // JSONPath or header name
              "operator": "operator", // "equals", "contains", "exists" etc.
              "expected": "Expected value"
            }}
          ],
          "extract_variables": [
            {{
              "name": "Variable name",
              "from": "source", // "response_body", "response_header" etc.
              "path": "extraction path" // JSONPath or header name
            }}
          ]
        }}
      ]
    }}
  ]
}}
```""",
            metadata={
                "description": "APIテストスイート生成用のプロンプト",
                "version": "1.0",
                "author": "Caseforge Team"
            }
        ))
        
        self.register("endpoint_test_generation", PromptTemplate(
            template="""You are an expert in API testing. Based on the following target endpoint and related OpenAPI schema information, generate a complete test suite (TestSuite) in strict JSON format.

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
```

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
10. Return only a single valid JSON object matching the following format. **Do not include any explanations, markdown formatting, or non-JSON text.**
""",
            metadata={
                "description": "特定のエンドポイントに対するテスト生成用のプロンプト",
                "version": "1.2",
                "author": "Caseforge Team"
            }
        ))
        
        self.register("dependency_aware_rag", PromptTemplate(
            template="""You are an expert in API testing. Based on the following target endpoint and related OpenAPI schema information, generate a complete test suite (TestSuite) in strict JSON format.

Dependency information:
{dependency_graph}

Target endpoint:
{target_endpoint}

Related OpenAPI schema:
{relevant_schema_info}

The test suite must include the following test cases:
1. **Normal case**: A request that successfully triggers the expected behavior. Include any necessary setup steps (e.g. creating required resources).
2. **Error cases**: Generate multiple test cases according to the following instruction:
{error_types_instruction}

## Dependency Analysis and Setup Requirements

**Automatically detect and handle dependencies based on:**
- **ID fields in request body**: `userId`, `authorId`, `categoryId`, `articleId`, etc. → Require corresponding resource creation
- **Path parameters**: `/users/{{id}}`, `/articles/{{articleId}}` → Require resource existence
- **Query parameters**: `?userId=123`, `?categoryId=456` → Require referenced resources

**Common dependency patterns:**
- `*Id` or `*_id` fields → POST to `/{{resource_plural}}` (e.g., `userId` → POST `/users`)
- Nested resources → Create parent first (e.g., `/users/{{userId}}/posts` → create user first)
- Reference fields → Create referenced entities before the target operation

**Setup step template examples:**
```json
// User creation (for authorId, userId dependencies)
{{
  "method": "POST",
  "path": "/users", 
  "request_body": {{"name": "Test User", "email": "test@example.com"}},
  "extract_rules": {{"user_id": "$.id"}}
}}

// Category creation (for categoryId dependencies)  
{{
  "method": "POST",
  "path": "/categories",
  "request_body": {{"name": "Test Category", "description": "Test Description"}}, 
  "extract_rules": {{"category_id": "$.id"}}
}}

// Article creation (for articleId dependencies, may need authorId)
{{
  "method": "POST", 
  "path": "/articles",
  "request_body": {{"title": "Test Article", "content": "Test Content", "authorId": "{{user_id}}"}},
  "extract_rules": {{"article_id": "$.id"}}
}}
```

## Error Case Generation Rules
**Note**: The error must be isolated to the final target endpoint call.
All test cases must include all prerequisite steps (e.g., POST /users, POST /articles)
to ensure the target endpoint is executable.

**For each error type specified in {error_types_instruction}:**
1. Each error test case MUST include the **same setup steps as the normal case**, including all required resource creations (e.g., users, articles, categories). These setup steps MUST appear in full before the target endpoint is invoked.
2. Modify ONLY the final request to the target endpoint to trigger the specific error. All prior setup steps MUST remain unchanged.
3. **Keep the test realistic** - error should be isolated to the target endpoint's parameters/body
4. **Use appropriate error status codes** based on the error type (400, 401, 404, 422, etc.)

**Error modification examples:**
- `missing_field`: Omit required fields from request body
- `invalid_input`: Use wrong data types, invalid formats, or constraint violations
- `invalid_reference`: Use non-existent IDs for reference fields
- `unauthorized`: Omit or use invalid authentication headers
- `not_found`: Use non-existent resource IDs in path parameters

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
```

**Instructions (MUST FOLLOW STRICTLY):**
0. Each test step must include **all** of the following keys: `method`, `path`, `request_headers`, `request_body`, `request_params`, `extract_rules`, `expected_status`. Even if values are empty, all keys must be present.

1. **Analyze dependencies first**: Examine the target endpoint's path, parameters, and request body schema to identify required resources (look for ID fields, path parameters, reference relationships).

2. **Generate setup steps**: For each dependency, create appropriate setup steps that:
   - Create the required resource using realistic minimal data
   - Extract the necessary ID/reference values using JSONPath expressions
   - Use appropriate HTTP methods and paths based on RESTful conventions

3. **Build the normal case**: Include all setup steps followed by a successful target endpoint call using extracted values.

4. **Generate error cases**: For each error type in {error_types_instruction}:
   - Copy the exact same setup steps from the normal case
   - Modify only the final target endpoint request to trigger the specific error
   - Use appropriate expected status codes for each error type

5. Use appropriate JSONPath expressions in `extract_rules` to capture IDs or other values from previous responses.
6. Use the extracted values in subsequent steps using `{{variable_name}}` syntax (e.g., in path parameters or request body).
7. The **final step of each test case must always be the target endpoint call**.
8. Ensure logical, realistic sequences of steps (e.g., create user → create article → update article).
9. The output must be **a single valid JSON object**, and **nothing else** (no comments, no explanation).
10. Generate one test suite **per target endpoint**.
11. Include both the HTTP method and path in the test suite's `"name"` field.
12. For each test case, the `"name"` field should indicate the case type (e.g., "Normal case", "Invalid input").
13. Use the appropriate `error_type` for abnormal cases: `"missing_field"`, `"invalid_input"`, `"unauthorized"`, `"not_found"`, etc. Use `null` for normal cases.
14. Return only a single valid JSON object matching the format above. **Do not include any explanations, markdown formatting, or non-JSON text.**
""",
            metadata={
                "description": "依存関係を考慮したRAGベースのテスト生成プロンプト",
                "version": "2.0",
                "author": "Caseforge Team",
                "phase": "2",
                "features": [
                    "body_reference_dependencies",
                    "dependency_chain_analysis",
                    "setup_step_insertion",
                    "circular_reference_handling",
                    "confidence_based_processing"
                ]
            }
        ))
        
        self.register("dependency_chain_generator", PromptTemplate(
            template="""以下の依存関係情報から、テスト実行に最適な順序を決定してください。

## 検出された依存関係
{dependencies}

## 対象エンドポイント
{target_endpoint}

## 指示
1. 依存関係の強度（required/optional）を考慮
2. 循環参照がある場合は警告を出力
3. 最適な実行順序を提案

## 出力形式
```json
{{
  "execution_order": [
    {{
      "step": 1,
      "endpoint": "POST /users",
      "purpose": "authorId生成のためのユーザー作成",
      "required": true
    }},
    {{
      "step": 2,
      "endpoint": "POST /articles",
      "purpose": "対象エンドポイントの実行",
      "required": true
    }}
  ],
  "warnings": [
    "循環参照が検出されました: /articles ↔ /comments"
  ],
  "confidence": 0.95
}}
```""",
            metadata={
                "description": "依存関係チェーンの実行順序決定プロンプト",
                "version": "1.0",
                "author": "Caseforge Team"
            }
        ))
        
        templates_dir = os.environ.get("PROMPT_TEMPLATES_DIR")
        if templates_dir and os.path.isdir(templates_dir):
            try:
                self.load_from_directory(templates_dir)
            except Exception as e:
                logger.error(f"Error loading templates from {templates_dir}: {e}", exc_info=True)


prompt_registry = PromptTemplateRegistry()


def get_prompt_template(name: str) -> PromptTemplate:
    """
    プロンプトテンプレートを取得する
    
    Args:
        name: テンプレート名
        
    Returns:
        プロンプトテンプレート
    """
    return prompt_registry.get(name)


def register_prompt_template(name: str, template: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    プロンプトテンプレートを登録する
    
    Args:
        name: テンプレート名
        template: テンプレート文字列
        metadata: テンプレートに関するメタデータ
    """
    prompt_registry.register(name, PromptTemplate(template, metadata))
