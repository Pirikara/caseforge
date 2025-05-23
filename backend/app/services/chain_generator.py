from typing import List, Dict, Optional
import json
import os
import uuid
from datetime import datetime
from app.services.rag.embeddings import EmbeddingFunctionForCaseforge
from app.services.schema_analyzer import OpenAPIAnalyzer
from app.config import settings
from app.logging_config import logger
from app.models import TestSuite, TestStep, Service, TestCase, engine
from sqlmodel import select, Session
from app.exceptions import TimeoutException
from app.utils.timeout import run_with_timeout
from app.utils.path_manager import path_manager

from sqlalchemy.orm import selectinload

class DependencyAwareRAG:
    """依存関係を考慮したRAGクラス"""
    
    def __init__(self, id: int, schema: dict, error_types: Optional[List[str]] = None):
        """
        Args:
            id: サービスID (int)
            schema: パース済みのOpenAPIスキーマ（dict形式）
        """
        self.service_id = id # Keep attribute name for internal consistency if needed, but use int ID
        self.schema = schema
        self.error_types = error_types
        self.analyzer = OpenAPIAnalyzer(schema)
        self.dependencies = self.analyzer.extract_dependencies()
        
        is_testing = os.environ.get("TESTING") == "1"
        
        if is_testing:
            self.vectordb = None
        else:
                embedding_fn = EmbeddingFunctionForCaseforge()
                
                try:
                    from app.services.vector_db.manager import VectorDBManagerFactory
                    self.vectordb = VectorDBManagerFactory.create_default(str(id), db_type="pgvector")
                except Exception as e:
                    logger.warning(f"DependencyAwareRAG: ベクトルDB初期化エラー: {e}", exc_info=True)
                    self.vectordb = None
    
    def generate_request_chains(self) -> List[Dict]:
        """
        依存関係を考慮したリクエストチェーンを生成する
        
        Returns:
            リクエストチェーンのリスト
        """
        dependency_graph = self._build_dependency_graph()
        chain_candidates = self._identify_chain_candidates(dependency_graph)
        
        chains = []
        for candidate in chain_candidates:
            chain = self._generate_chain_for_candidate(candidate)
            if chain:
                chains.append(chain)
        
        return chains
    
    def _build_dependency_graph(self) -> Dict:
        """依存関係グラフを構築する"""
        graph = {}
        
        for path, methods in self.schema.get("paths", {}).items():
            for method_name in methods:
                if method_name != "parameters":
                    node_id = f"{method_name.upper()} {path}"
                    graph[node_id] = {
                        "path": path,
                        "method": method_name,
                        "dependencies": [],
                        "dependents": []
                    }
        
        for dep in self.dependencies:
            if dep["type"] in ["path_parameter", "resource_operation"]:
                source_method = dep["source"]["method"].upper()
                source_path = dep["source"]["path"]
                target_method = dep["target"]["method"].upper()
                target_path = dep["target"]["path"]
                
                source_id = f"{source_method} {source_path}"
                target_id = f"{target_method} {target_path}"
                
                if source_id in graph and target_id in graph:
                    graph[target_id]["dependencies"].append(source_id)
                    graph[source_id]["dependents"].append(target_id)
        
        return graph
    
    def _identify_chain_candidates(self, graph: Dict) -> List[List[str]]:
        """有望なチェーン候補を特定する"""
        candidates = []
        
        start_nodes = [node_id for node_id, node in graph.items() if not node["dependencies"]]
        
        for start_node in start_nodes:
            paths = self._find_paths_from_node(graph, start_node)
            candidates.extend(paths)
        
        candidates.sort(key=len, reverse=True)
        
        unique_candidates = []
        for candidate in candidates:
            if candidate not in unique_candidates:
                unique_candidates.append(candidate)
                if len(unique_candidates) >= 10:
                    break
        
        return unique_candidates
    
    def _find_paths_from_node(self, graph: Dict, start_node: str, path: Optional[List[str]] = None) -> List[List[str]]:
        """ノードからの全パスを再帰的に探索する"""
        if path is None:
            path = []
        
        current_path = path + [start_node]
        
        if not graph[start_node]["dependents"]:
            return [current_path]
        
        paths = []
        for dependent in graph[start_node]["dependents"]:
            if dependent not in current_path:
                new_paths = self._find_paths_from_node(graph, dependent, current_path)
                paths.extend(new_paths)
        
        if not paths and len(current_path) > 1:
            return [current_path]
        
        return paths
    
    def _generate_chain_for_candidate(self, candidate: List[str]) -> Optional[Dict]:
        """チェーン候補に対してRAGを実行し、リクエストチェーンを生成する"""
        try:
            is_testing = os.environ.get("TESTING") == "1"
            
            if is_testing:
                sample_chain = {
                    "name": "ユーザー作成と取得",
                    "target_method": "POST",
                    "target_path": "/users",
                    "test_cases": [
                        {
                            "name": "正常系",
                            "description": "正常なユーザー作成と取得",
                            "error_type": None,
                            "test_steps": [
                                {
                                    "sequence": 0,
                                    "method": "POST",
                                    "path": "/users",
                                    "request_body": {"name": "Test User", "email": "test@example.com"},
                                    "extract_rules": {"user_id": "$.id"},
                                    "expected_status": 201
                                },
                                {
                                    "sequence": 1,
                                    "method": "GET",
                                    "path": "/users/{user_id}",
                                    "request_params": {"user_id": "{user_id}"},
                                    "expected_status": 200
                                }
                            ]
                        },
                        {
                            "name": "必須フィールド欠落",
                            "description": "emailフィールドがない場合",
                            "error_type": "missing_field",
                            "test_steps": [
                                {
                                    "sequence": 0,
                                    "method": "POST",
                                    "path": "/users",
                                    "request_body": {"name": "Test User"},
                                    "expected_status": 400
                                }
                            ]
                        }
                    ]
                }
                return sample_chain
            
            context = self._build_context_for_candidate(candidate)
            
            from app.services.llm.client import LLMClientFactory, LLMProviderType
            from app.services.llm.prompts import get_prompt_template
            
            llm_client = LLMClientFactory.create(
                provider_type=LLMProviderType.LOCAL,
                temperature=0.2,
            )
            
            try:
                prompt_template = get_prompt_template("test_suite_generation")
            except KeyError:
                logger.warning("test_suite_generation prompt template not found, using hardcoded prompt")
                prompt_template_str = """あなたはAPIテストの専門家です。以下のOpenAPIエンドポイント情報を使用してください。
{context}

提供されたエンドポイント情報に基づき、そのエンドポイントに対するテストスイート（TestSuite）と、それに含まれる複数のテストケース（TestCase）を生成してください。
テストケースには、正常系テストケースと、{error_types_instruction}を含めてください。
各テストケースは、APIリクエストのシーケンスであるテストステップ（TestStep）で構成されます。依存関係がある場合は、前のステップの応答から必要な情報を抽出し、次のステップのリクエストに含めるようにしてください。

生成するJSONオブジェクトは以下の構造に従ってください。**JSONオブジェクトのみを返し、説明や他のテキストは含めないでください。**

```json
{{
  "name": "TestSuiteの名前 (例: POST /users エンドポイントのテスト)",
  "target_method": "対象エンドポイントのHTTPメソッド",
  "target_path": "対象エンドポイントのパス",
  "description": "このテストスイートの説明（省略可）",
  "test_cases": [
    {{
      "name": "TestCaseの名前 (例: 正常系)",
      "description": "TestCaseの説明",
      "error_type": null,
      "test_steps": [
        {{
          "name": "任意のステップ名（省略可）",
          "sequence": 0,
          "method": "HTTPメソッド (GET, POST, PUT, DELETE)",
          "path": "APIパス（パラメータはプレースホルダー形式）",
          "request_headers": {{}},
          "request_body": {{}},
          "request_params": {{}},
          "extract_rules": {{}},
          "expected_status": 200
        }}
        // 他のTestStep
      ]
    }}
    // 他のTestCase
  ]
}}
```
フィールドについて：
各テストステップには必ず以下のフィールドを含めること：
- method（HTTPメソッド）
- path（パス）
- request_headers（ヘッダー）
- request_body（リクエストボディ）
- request_params（クエリパラメータが不要でも空オブジェクト）
- extract_rules（レスポンスから値を取り出す定義。不要でも空のオブジェクト）
- expected_status（想定されるHTTPステータスコード）

注意事項（絶対遵守）：
1. expected_status は必ず整数（例: 200, 404）で指定してください（文字列ではなく）。
2. extract_rules には応答から値を抽出するためのJSONPath式を指定してください。
3. 抽出した値は、次のステップのパスパラメータやボディで $.変数名 のように使用してください。
各 test_steps には実行順を示す sequence を昇順で付けてください。
4. request_headers, request_body, request_params はJSON形式のオブジェクトとして記述してください。
5. 出力はJSONのみで構成し、説明文やコメントを含めないでください。
"""

            error_types_instruction = "様々な異常系テストケース（例: 必須フィールドの欠落、無効な入力値、認証エラーなど）"
            if self.error_types and len(self.error_types) > 0:
                error_types_instruction = f"以下の異常系テストケース（{', '.join(self.error_types)}）"

            try:
                if 'prompt_template' in locals():
                    chain = llm_client.call_with_json_response(
                        [llm_client.Message(llm_client.MessageRole.USER,
                                           prompt_template.format(
                                               context=context,
                                               error_types_instruction=error_types_instruction
                                           ))]
                    )
                else:
                    chain = llm_client.call_with_json_response(
                        [llm_client.Message(llm_client.MessageRole.USER,
                                           prompt_template_str.format(
                                               context=context,
                                               error_types_instruction=error_types_instruction
                                           ))]
                    )
                
                return chain
            except llm_client.LLMResponseFormatException as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return None
            except llm_client.LLMException as e:
                logger.error(f"Error invoking LLM: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error generating chain: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating chain for candidate: {e}")
            return None
    
    def _build_context_for_candidate(self, candidate: List[str]) -> str:
        """チェーン候補からLLMのためのコンテキストを構築する"""
        context_parts = []
        
        for node_id in candidate:
            method, path = node_id.split(" ", 1)
            
            if path in self.schema.get("paths", {}):
                path_item = self.schema["paths"][path]
                if method.lower() in path_item:
                    operation = path_item[method.lower()]
                    
                    endpoint_info = f"Endpoint: {method} {path}\n"
                    
                    if "summary" in operation:
                        endpoint_info += f"Summary: {operation['summary']}\n"
                    
                    if "description" in operation:
                        endpoint_info += f"Description: {operation['description']}\n"
                    
                    if "parameters" in operation:
                        endpoint_info += "Parameters:\n"
                        for param in operation["parameters"]:
                            param_name = param.get("name", "unknown")
                            param_in = param.get("in", "unknown")
                            required = "required" if param.get("required", False) else "optional"
                            endpoint_info += f"- {param_name} (in {param_in}, {required})\n"
                    
                    if "requestBody" in operation:
                        endpoint_info += "Request Body:\n"
                        content = operation["requestBody"].get("content", {})
                        for media_type, media_content in content.items():
                            endpoint_info += f"- Media Type: {media_type}\n"
                            if "schema" in media_content:
                                schema = media_content["schema"]
                                if "$ref" in schema:
                                    ref_name = schema["$ref"].split("/")[-1]
                                    endpoint_info += f"  Schema: {ref_name}\n"
                                elif "type" in schema:
                                    endpoint_info += f"  Type: {schema['type']}\n"
                    
                    if "responses" in operation:
                        endpoint_info += "Responses:\n"
                        for status, response in operation["responses"].items():
                            endpoint_info += f"- Status: {status}\n"
                            if "description" in response:
                                endpoint_info += f"  Description: {response['description']}\n"
                            if "content" in response:
                                for media_type, media_content in response["content"].items():
                                    if "schema" in media_content:
                                        schema = media_content["schema"]
                                        if "$ref" in schema:
                                            ref_name = schema["$ref"].split("/")[-1]
                                            endpoint_info += f"  Schema: {ref_name}\n"
                    
                    context_parts.append(endpoint_info)
        
        context_parts.append("\nDependencies:")
        for i in range(len(candidate) - 1):
            source = candidate[i]
            target = candidate[i + 1]
            context_parts.append(f"- {source} -> {target}")
        
        return "\n\n".join(context_parts)

class ChainStore:
    """リクエストチェーンの保存と取得を担当するクラス"""
    
    def __init__(self):
        """初期化"""
        pass
    
    def save_suites(self, session: Session, id: int, test_suites: List[Dict], overwrite: bool = True) -> None:
        """
        生成されたテストスイートをデータベースに保存する
        
        Args:
            session: データベースセッション
            id: サービスID (int)
            test_suites: 保存するテストスイteのリスト (LLM生成JSON構造)
            overwrite: 既存のテストスイートを上書きするかどうか (デフォルト: True)
        """
        try:
            tests_dir = path_manager.get_tests_dir(str(id))
            path_manager.ensure_dir(tests_dir)
            
            suites_file_path = path_manager.join_path(tests_dir, "test_suites.json")
            if not overwrite and path_manager.exists(suites_file_path):
                try:
                    with open(suites_file_path, "r") as f:
                        existing_suites = json.load(f)
                    all_suites = existing_suites + test_suites
                    with open(suites_file_path, "w") as f:
                        json.dump(all_suites, f, indent=2)
                except Exception as e:
                    logger.error(f"Error reading or updating existing test suites file: {e}")
                    with open(suites_file_path, "w") as f:
                        json.dump(test_suites, f, indent=2)
            else:
                with open(suites_file_path, "w") as f:
                    json.dump(test_suites, f, indent=2)
            
            service_query = select(Service).where(Service.id == id)
            db_service = session.exec(service_query).first()
            
            if not db_service:
                logger.error(f"Service not found: {id}")
                return
            
            if overwrite:
                existing_suites_query = select(TestSuite).where(TestSuite.service_id == db_service.id)
                existing_suites = session.exec(existing_suites_query).all()
                
                for suite in existing_suites:
                    for case in suite.test_cases:
                        for step in case.test_steps:
                            session.delete(step)
                        session.delete(case)
                    session.delete(suite)
                

            for suite_data in test_suites:
                suite_id = suite_data.get("id", str(uuid.uuid4()))
                test_suite = TestSuite(
                    id=suite_id,
                    service_id=db_service.id,
                    target_method=suite_data.get("target_method"),
                    target_path=suite_data.get("target_path"),
                    name=suite_data.get("name", "Unnamed TestSuite"),
                    description=suite_data.get("description", "")
                )
                session.add(test_suite)
                session.flush()

                
                for case_data in suite_data.get("test_cases", []):
                    case_id = str(uuid.uuid4())
                    test_case = TestCase(
                        id=case_id,
                        suite_id=test_suite.id,
                        name=case_data.get("name", "Unnamed TestCase"),
                        description=case_data.get("description", ""),
                        error_type=case_data.get("error_type")
                    )
                    session.add(test_case)
                    session.flush()

                    for i, step_data in enumerate(case_data.get("test_steps", [])):
                        step_id = str(uuid.uuid4())
                        test_step = TestStep(
                            id=step_id,
                            case_id=test_case.id,
                            sequence=i,
                            name=step_data.get("name"),
                            method=step_data.get("method"),
                            path=step_data.get("path"),
                            request_headers=step_data.get("request_headers"),
                            request_body=step_data.get("request_body"),
                            request_params=step_data.get("request_params"),
                            extract_rules=step_data.get("extract_rules"),
                            expected_status=step_data.get("expected_status")
                        )
                        session.add(test_step)
                
            session.commit()
                
        except Exception as e:
            logger.error(f"Error saving test suites for service {id}: {e}", exc_info=True)
            session.rollback()
            raise
    
    def list_test_suites(self, session: Session, id: int) -> List[Dict]:
        """
        サービスのテストスイート一覧を取得する
        
        Args:
            session: データベースセッション
            id: サービスID (int)
            
        Returns:
            テストスイートのリスト
        """
        try:
            service_query = select(Service).where(Service.id == id).options(selectinload(Service.test_suites))
            db_service = session.exec(service_query).first()

            if not db_service:
                return []
            
            test_suites = []
            for suite in db_service.test_suites:
                suite_data = {
                    "id": suite.id,
                    "name": suite.name,
                    "description": suite.description,
                    "target_method": suite.target_method,
                    "target_path": suite.target_path,
                    "created_at": suite.created_at.isoformat() if suite.created_at else None,
                    "test_cases_count": len(suite.test_cases) if suite.test_cases else 0,
                    "service_id": db_service.id, # Keep service_id key for frontend compatibility, but use int ID
                }
                test_suites.append(suite_data)
            
            return test_suites

        except Exception as e:
            logger.error(f"Error listing test suites for service {id}: {e}", exc_info=True)
            
            try:
                # Fallback to filesystem - assuming directory names are integer IDs
                path = path_manager.join_path(path_manager.get_tests_dir(str(id)), "test_suites.json")
                if path_manager.exists(path):
                    with open(path, "r") as f:
                        test_suites = json.load(f)
                    # Update service_id in fallback data if necessary
                    for suite in test_suites:
                         suite["service_id"] = id
                    return test_suites
            except Exception as fallback_error:
                logger.error(f"Fallback error reading test suites from file system for service {id}: {fallback_error}", exc_info=True)
            
            return []

    def merge_and_save_test_suites(self, id: int, new_test_suites: List[Dict]) -> None:
        """
        新しいテストスイートリストを既存のテストスイートとマージしてデータベースに保存する。
        新しいリストに含まれるtarget_methodとtarget_pathの組み合わせが同じテストスイートは既存のもので置き換え、
        新しいリストにない組み合わせの既存テストスイートはそのまま残す。
        
        Args:
            id: サービスID
            new_test_suites: 新しく生成されたテストスイートのリスト
        """
        try:
            with Session(engine) as session:
                service_query = select(Service).where(Service.id == id)
                db_service = session.exec(service_query).first()
                
                if not db_service:
                    return
                
                existing_suites_dict = {(suite.target_method, suite.target_path): suite for suite in db_service.test_suites}
                
                suites_to_save = []
                
                for suite_data in new_test_suites:
                    target_method = suite_data.get("target_method")
                    target_path = suite_data.get("target_path")
                    
                    if not target_method or not target_path:
                        logger.warning(f"Skipping test suite with missing target_method or target_path: {suite_data}")
                        continue

                    suite_key = (target_method, target_path)
                    
                    if suite_key in existing_suites_dict:
                        existing_suite = existing_suites_dict[suite_key]
                        for case in existing_suite.test_cases:
                            for step in case.test_steps:
                                session.delete(step)
                            session.delete(case)
                        session.delete(existing_suite)
                    
                    suite_id = str(uuid.uuid4())
                    test_suite = TestSuite(
                        id=suite_id,
                        service_id=db_service.id,
                        target_method=target_method,
                        target_path=target_path,
                        name=suite_data.get("name", f"{target_method} {target_path} TestSuite"),
                        description=suite_data.get("description", "")
                    )
                    session.add(test_suite)
                    session.flush()
                    
                    for case_data in suite_data.get("test_cases", []):
                        case_id = str(uuid.uuid4())
                        test_case = TestCase(
                            id=case_id,
                            suite_id=test_suite.id,
                            name=case_data.get("name", "Unnamed TestCase"),
                            description=case_data.get("description", ""),
                            error_type=case_data.get("error_type")
                        )
                        session.add(test_case)
                        session.flush()

                        for i, step_data in enumerate(case_data.get("test_steps", [])):
                            step_id = str(uuid.uuid4())
                            test_step = TestStep(
                                id=step_id,
                                case_id=test_case.id,
                                sequence=i,
                                name=step_data.get("name"),
                                method=step_data.get("method"),
                                path=step_data.get("path"),
                                expected_status=step_data.get("expected_status")
                            )
                            
                            request = step_data.get("request", {})
                            test_step.request_headers = request.get("headers")
                            test_step.request_body = request.get("body")
                            test_step.request_params = request.get("params")
                            
                            response = step_data.get("response", {})
                            test_step.extract_rules = response.get("extract")
                            
                            session.add(test_step)
                    
                    suites_to_save.append(test_suite)

                session.commit()
                
        except Exception as e:
            logger.error(f"Error merging and saving test suites for service {id}: {e}", exc_info=True)
            session.rollback()
            raise
    
    def get_test_suite(self, session: Session, id: int, suite_id: str) -> Optional[Dict]:
        """
        特定のテストスイートの詳細を取得する
        
        Args:
            session: データベースセッション
            id: サービスID
            suite_id: テストスイートID
            
        Returns:
            テストスイートの詳細。見つからない場合はNone。
        """
        try:
            service_query = select(Service).where(Service.id == id).options(selectinload(Service.test_suites))
            db_service = session.exec(service_query).first()

            if not db_service:
                return None
            
            for suite in db_service.test_suites:
                if suite.id == suite_id:
                    test_cases_data = []
                    sorted_cases = sorted(suite.test_cases, key=lambda c: c.name)

                    for case in sorted_cases:
                        test_steps_data = []
                        sorted_steps = sorted(case.test_steps, key=lambda s: s.sequence)

                        for step in sorted_steps:
                            step_data = {
                                "id": step.id,
                                "sequence": step.sequence,
                                "name": step.name,
                                "method": step.method,
                                "path": step.path,
                                "request": {
                                    "headers": step.request_headers,
                                    "body": step.request_body,
                                    "params": step.request_params
                                },
                                "expected_status": step.expected_status,
                                "extract_rules": step.extract_rules
                            }
                            test_steps_data.append(step_data)

                        case_data = {
                            "id": case.id,
                            "name": case.name,
                            "description": case.description,
                            "error_type": case.error_type,
                            "created_at": case.created_at.isoformat() if case.created_at else None,
                            "test_steps": test_steps_data
                        }
                        test_cases_data.append(case_data)
                        
                    suite_data = {
                        "id": suite.id,
                        "name": suite.name,
                        "description": suite.description,
                        "target_method": suite.target_method,
                        "target_path": suite.target_path,
                        "created_at": suite.created_at.isoformat() if suite.created_at else None,
                        "test_cases": test_cases_data
                    }
                    
                    return suite_data
                
            logger.warning(f"Test suite not found: {suite_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting test suite {suite_id} for service {id}: {e}")
            return None

        except Exception as e:
            logger.error(f"Error getting chain {suite_id} for service {id}: {e}")
            return None
