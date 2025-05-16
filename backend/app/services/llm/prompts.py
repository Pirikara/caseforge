"""
プロンプトテンプレート管理モジュール

このモジュールは、プロジェクト内で使用されるプロンプトテンプレートを集約し、
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
        
        # 組み込みのテンプレートを登録
        self.register("test_suite_generation", PromptTemplate(
            template="""あなたはAPIテストの専門家です。以下のOpenAPIエンドポイント情報を使用してください。
{context}

提供されたエンドポイント情報に基づき、そのエンドポイントに対するテストスイート（TestSuite）と、それに含まれる複数のテストケース（TestCase）を生成してください。
テストケースには、正常系テストケースと、{error_types_instruction}を含めてください。
各テストケースは、APIリクエストのシーケンスであるテストステップ（TestStep）で構成されます。依存関係がある場合は、前のステップの応答から必要な情報を抽出し、次のステップのリクエストに含めるようにしてください。

生成するJSONオブジェクトは以下の構造に従ってください。**JSONオブジェクトのみを返し、説明や他のテキストは含めないでください。**

```json
{{
  "name": "テストスイート名",
  "description": "テストスイートの説明",
  "test_cases": [
    {{
      "name": "テストケース名",
      "description": "テストケースの説明",
      "type": "正常系" または "異常系",
      "steps": [
        {{
          "name": "ステップ名",
          "description": "ステップの説明",
          "request": {{
            "method": "HTTPメソッド",
            "path": "エンドポイントパス",
            "headers": {{
              "ヘッダー名": "ヘッダー値"
            }},
            "query_params": {{
              "クエリパラメータ名": "値"
            }},
            "path_params": {{
              "パスパラメータ名": "値"
            }},
            "body": {{
              // リクエストボディ（JSON形式）
            }}
          }},
          "expected_response": {{
            "status_code": 期待するHTTPステータスコード,
            "headers": {{
              "ヘッダー名": "期待する値"
            }},
            "body": {{
              // 期待するレスポンスボディ（JSON形式）
              // 完全一致ではなく、特定のフィールドの存在や値を検証
            }}
          }},
          "validation": [
            {{
              "type": "検証タイプ", // "json_path", "header", "status_code" など
              "target": "検証対象", // JSONPathや特定のヘッダー名など
              "operator": "演算子", // "equals", "contains", "exists" など
              "expected": "期待値" // 期待される値
            }}
          ],
          "extract_variables": [
            {{
              "name": "変数名",
              "from": "抽出元", // "response_body", "response_header" など
              "path": "抽出パス" // JSONPathやヘッダー名など
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
            template="""あなたはAPIテストの専門家です。以下のターゲットエンドポイントと、関連するOpenAPIスキーマ情報を元に、そのエンドポイントに対するテストスイート（TestSuite）を生成してください。

ターゲットエンドポイント:
{target_endpoint_info}

関連するスキーマ情報:
{relevant_schema_info}

テストスイートには、以下のテストケースを含めてください。
1. 正常系テストケース: ターゲットエンドポイントが正常に処理されるリクエスト。必要な前提リクエスト（リソース作成など）を含めること。
2. 異常系テストケース: {error_types_instruction}に基づいたテストケースを複数生成してください。

各テストケースは、そのテストケースを実行するために必要な前提ステップと、ターゲットエンドポイントへのリクエストステップで構成される必要があります。エンドポイント間の依存関係を考慮し、例えばターゲットエンドポイントがパスパラメータにリソースIDを必要とする場合、そのリソースを作成しIDを抽出する先行リクエストを含めてください。

以下の形式に従い、テストスイート（TestSuite）をJSONオブジェクトとして返してください。説明文などJSON以外のテキストは**絶対に含めないでください**。

```json
{{
  "name": "テストスイートの名前（例: PUT /users のテストスイート）",
  "target_method": "対象エンドポイントのHTTPメソッド（例: PUT）",
  "target_path": "対象エンドポイントのパス（例: /users/{{id}}）",
  "test_cases": [
    {{
      "name": "テストケース名（例: 正常系）",
      "description": "テストケースの目的や意図",
      "error_type": null,  // 異常系は "invalid_input" などの文字列、正常系は null
      "test_steps": [
        {{
          "method": "HTTPメソッド（例: POST）",
          "path": "APIのパス（例: /users）",
          "request_headers": {{
            "Content-Type": "application/json"
          }},
          "request_body": {{
            "name": "John Doe"
          }},
          "request_params": {{
            "id": "123"
          }},
          "extract_rules": {{
            "user_id": "$.id"
          }},
          "expected_status": 200
        }}
        // ... 他のステップ ...
      ]
    }}
    // ... 他のテストケース ...
  ]
}}
```""",
            metadata={
                "description": "特定のエンドポイントに対するテスト生成用のプロンプト",
                "version": "1.2", # バージョンを更新
                "author": "Caseforge Team"
            }
        ))
        
        # 環境変数で指定されたディレクトリからテンプレートを読み込む
        templates_dir = os.environ.get("PROMPT_TEMPLATES_DIR")
        if templates_dir and os.path.isdir(templates_dir):
            try:
                self.load_from_directory(templates_dir)
            except Exception as e:
                logger.error(f"Error loading templates from {templates_dir}: {e}", exc_info=True)


# シングルトンインスタンス
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