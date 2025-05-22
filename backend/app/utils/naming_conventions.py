"""
Caseforge サービスの命名規則ガイドライン

このモジュールは、サービス全体で一貫した命名規則を定義し、
コードの可読性と保守性を向上させるためのガイドラインを提供します。
"""

NAMING_STYLES = {
    "pascal_case": "単語の先頭を大文字にし、スペースや区切り文字を使用しない (例: ServiceManager)",
    "snake_case": "すべて小文字で、単語をアンダースコアで区切る (例: service_manager)",
    "upper_snake_case": "すべて大文字で、単語をアンダースコアで区切る (例: PROJECT_MANAGER)",
    "camel_case": "最初の単語は小文字で始め、以降の単語の先頭を大文字にする (例: serviceManager)",
    "kebab_case": "すべて小文字で、単語をハイフンで区切る (例: service-manager)",
}

PYTHON_NAMING_CONVENTIONS = {
    # クラス
    "class_names": {
        "style": "pascal_case",
        "examples": ["Service", "LLMClient", "TimeoutException"],
        "description": "クラス名はパスカルケースを使用し、名詞または名詞句を使用します。"
    },
    
    # メソッド・関数
    "method_function_names": {
        "style": "snake_case",
        "examples": ["get_timeout_config", "call_with_prompt", "to_dict"],
        "description": "メソッドと関数名はスネークケースを使用し、動詞または動詞句を使用します。"
    },
    
    # プライベートメソッド・関数
    "private_method_function_names": {
        "style": "snake_case",
        "prefix": "_",
        "examples": ["_setup_client", "_call_llm", "_resolve_timeout"],
        "description": "プライベートメソッドと関数はアンダースコアで始まるスネークケースを使用します。"
    },
    
    # 変数
    "variable_names": {
        "style": "snake_case",
        "examples": ["message", "error_code", "timeout_value"],
        "description": "変数名はスネークケースを使用し、意味のある名前を付けます。"
    },
    
    # 定数
    "constant_names": {
        "style": "upper_snake_case",
        "examples": ["DEFAULT_TIMEOUT", "API_VERSION", "MAX_RETRIES"],
        "description": "定数名はすべて大文字のスネークケースを使用します。"
    },
    
    # 列挙型の値
    "enum_values": {
        "style": "upper_snake_case",
        "examples": ["OPENAI", "SYSTEM", "USER"],
        "description": "列挙型の値はすべて大文字のスネークケースを使用します。"
    },
    
    # 型変数
    "type_variables": {
        "style": "single_uppercase_or_pascal_case",
        "examples": ["T", "F", "LLMClientType"],
        "description": "型変数は単一の大文字またはパスカルケースを使用します。"
    },
    
    # モジュール名
    "module_names": {
        "style": "snake_case",
        "examples": ["timeout", "retry", "chain_generator"],
        "description": "モジュール名はスネークケースを使用し、短く意味のある名前を付けます。"
    },
    
    # パッケージ名
    "package_names": {
        "style": "snake_case",
        "examples": ["utils", "services", "models"],
        "description": "パッケージ名はスネークケースを使用し、単数形の名詞を使用します。"
    },
    
    # データベースモデル関連
    "table_names": {
        "style": "snake_case",
        "examples": ["service", "test_suite", "endpoint"],
        "description": "テーブル名はスネークケースを使用し、単数形の名詞を使用します。"
    },
    
    "relationship_names": {
        "style": "snake_case",
        "examples": ["schemas", "test_suites", "endpoints"],
        "description": "リレーションシップ名はスネークケースを使用し、複数形の名詞を使用します。"
    }
}

TYPESCRIPT_NAMING_CONVENTIONS = {
    # コンポーネント
    "component_names": {
        "style": "pascal_case",
        "examples": ["ServiceCard", "Header", "TestRunChart"],
        "description": "Reactコンポーネント名はパスカルケースを使用します。"
    },
    
    # インターフェース・型
    "interface_type_names": {
        "style": "pascal_case",
        "examples": ["Service", "ServiceCardProps", "TestRun"],
        "description": "インターフェースと型名はパスカルケースを使用します。"
    },
    
    # フック関数
    "hook_names": {
        "style": "camel_case",
        "prefix": "use",
        "examples": ["useServices", "useTestRuns", "useEndpoints"],
        "description": "カスタムフック名は 'use' で始まるキャメルケースを使用します。"
    },
    
    # 関数
    "function_names": {
        "style": "camel_case",
        "examples": ["deleteService", "formatDate", "handleSubmit"],
        "description": "関数名はキャメルケースを使用し、動詞または動詞句を使用します。"
    },
    
    # 変数・プロパティ
    "variable_property_names": {
        "style": "camel_case",
        "examples": ["data", "error", "isLoading", "serviceId"],
        "description": "変数とプロパティ名はキャメルケースを使用します。ただし、バックエンドとの整合性が必要な場合は例外とします。"
    },
    
    # CSS クラス名
    "css_class_names": {
        "style": "kebab_case",
        "examples": ["card-header", "text-xl", "flex-container"],
        "description": "CSSクラス名はケバブケースを使用します。"
    },
    
    # ファイル名
    "file_names": {
        "component_files": {
            "style": "pascal_case",
            "extension": ".tsx",
            "examples": ["ServiceCard.tsx", "Header.tsx"]
        },
        "hook_files": {
            "style": "camel_case",
            "extension": ".ts",
            "examples": ["useServices.ts", "useTestRuns.ts"]
        },
        "utility_files": {
            "style": "camel_case",
            "extension": ".ts",
            "examples": ["fetcher.ts", "utils.ts"]
        }
    }
}

def apply_naming_conventions():
    """
    サービス全体に命名規則を適用するためのガイドライン
    
    このセクションでは、新しいコードを書く際や既存のコードをリファクタリングする際に
    命名規則を適用するためのガイドラインを提供します。
    """
    guidelines = [
        "1. 新しいコードを書く際は、上記の命名規則に従ってください。",
        "2. 既存のコードをリファクタリングする際は、ファイル単位で命名規則を適用してください。",
        "3. 変数名や関数名を変更する際は、その影響範囲を確認し、関連するすべての箇所を更新してください。",
        "4. 公開APIやデータベーススキーマの変更は、互換性を考慮して慎重に行ってください。",
        "5. コードレビューの際は、命名規則の遵守も確認項目に含めてください。"
    ]
    
    return "\n".join(guidelines)

NAMING_EXCEPTIONS = [
    "1. サードパーティライブラリとの連携部分では、そのライブラリの命名規則に従うことがあります。",
    "2. フロントエンドからバックエンドAPIを呼び出す際のパラメータ名は、APIの命名規則に合わせます。",
    "3. データベースとの連携部分では、既存のデータベーススキーマの命名規則に従うことがあります。"
]

def naming_examples():
    """命名規則の適用例を示します"""
    
    python_examples = {
        "良い例": [
            "class UserAuthentication:",
            "def validate_token(token):",
            "user_profile = get_user_profile(user_id)",
            "MAX_LOGIN_ATTEMPTS = 5",
            "class ErrorType(Enum):\n    VALIDATION_ERROR = 1"
        ],
        "悪い例": [
            "class userAuthentication:",
            "def ValidateToken(token):",
            "UserProfile = GetUserProfile(UserId)",
            "maxLoginAttempts = 5",
            "class ErrorType(Enum):\n    validation_error = 1"
        ]
    }
    
    typescript_examples = {
        "良い例": [
            "function ServiceCard({ service }) {...}",
            "interface UserProfileProps {...}",
            "function useAuthentication() {...}",
            "const handleSubmit = () => {...}",
            "const userData = await fetchUserData();"
        ],
        "悪い例": [
            "function service_card({ service }) {...}",
            "interface user_profile_props {...}",
            "function UseAuthentication() {...}",
            "const HandleSubmit = () => {...}",
            "const user_data = await fetch_user_data();"
        ]
    }
    
    return {
        "python": python_examples,
        "typescript": typescript_examples
    }
