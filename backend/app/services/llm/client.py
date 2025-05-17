"""
LLMクライアントの抽象化モジュール

このモジュールは、異なるLLMプロバイダーに対して統一的なインターフェースを提供します。
同期処理と非同期処理の両方に対応し、タイムアウト処理とリトライ機構を組み込んでいます。
"""

import abc
import json
import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast, Callable
from enum import Enum

from app.config import config, settings  # settingsも互換性のために残す
from app.exceptions import CaseforgeException, ErrorCode, TimeoutException
from app.logging_config import logger
from app.utils.retry import retry, async_retry, RetryStrategy
from app.utils.timeout import timeout, async_timeout

# サードパーティライブラリのインポート
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# 型変数の定義
T = TypeVar('T')
LLMClientType = TypeVar('LLMClientType', bound='LLMClient')

class LLMException(CaseforgeException):
    """LLM呼び出し関連の例外"""
    def __init__(
        self,
        message: str = "LLM呼び出し中にエラーが発生しました",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCode.LLM_ERROR, details)


class LLMResponseFormatException(LLMException):
    """LLMレスポンスのフォーマットエラー"""
    def __init__(
        self,
        message: str = "LLMレスポンスのフォーマットが不正です",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)


class LLMProviderType(Enum):
    """LLMプロバイダーの種類"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class MessageRole(Enum):
    """メッセージの役割"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message:
    """LLMに送信するメッセージ"""
    def __init__(self, role: MessageRole, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        """メッセージを辞書形式に変換"""
        return {
            "role": self.role.value,
            "content": self.content
        }


class LLMClient(abc.ABC):
    """LLMクライアントの抽象基底クラス"""
    
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        LLMクライアントの初期化
        
        Args:
            model_name: モデル名
            temperature: 温度パラメータ（0.0〜1.0）
            max_tokens: 最大トークン数
            timeout_seconds: タイムアウト秒数
            retry_config: リトライ設定
            **kwargs: その他のパラメータ
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds or config.timeout.LLM_CALL.get_value()
        self.retry_config = retry_config or {
            "max_retries": 3,
            "retry_delay": 1.0,
            "max_retry_delay": 60.0,
            "retry_jitter": 0.1,
            "backoff_factor": 2.0,
            "retry_strategy": RetryStrategy.EXPONENTIAL,
            "retry_exceptions": [ConnectionError, TimeoutError, json.JSONDecodeError]
        }
        self.extra_params = kwargs
        
        # 初期化時にクライアントを設定
        self._setup_client()
    
    @abc.abstractmethod
    def _setup_client(self) -> None:
        """クライアントの設定（サブクラスで実装）"""
        pass
    
    @abc.abstractmethod
    def _call_llm(self, messages: List[Message], **kwargs) -> str:
        """
        LLMを呼び出す（サブクラスで実装）
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        pass
    
    @abc.abstractmethod
    async def _acall_llm(self, messages: List[Message], **kwargs) -> str:
        """
        LLMを非同期で呼び出す（サブクラスで実装）
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        pass
    
    @retry(retry_key="LLM_CALL")
    @timeout(timeout_key="LLM_CALL")
    def call(self, messages: List[Message], **kwargs) -> str:
        """
        LLMを呼び出す（タイムアウトとリトライ付き）
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        try:
            logger.info(f"Calling LLM {self.model_name} with {len(messages)} messages")
            response = self._call_llm(messages, **kwargs)
            logger.info(f"LLM response received: {response[:100]}...")
            return response
        except Exception as e:
            logger.error(f"Error calling LLM: {e}", exc_info=True)
            raise LLMException(f"LLM呼び出し中にエラーが発生しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })
    
    @async_retry(retry_key="LLM_CALL")
    @async_timeout(timeout_key="LLM_CALL")
    async def acall(self, messages: List[Message], **kwargs) -> str:
        """
        LLMを非同期で呼び出す（タイムアウトとリトライ付き）
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        try:
            logger.info(f"Async calling LLM {self.model_name} with {len(messages)} messages")
            response = await self._acall_llm(messages, **kwargs)
            logger.info(f"LLM response received: {response[:100]}...")
            return response
        except Exception as e:
            logger.error(f"Error async calling LLM: {e}", exc_info=True)
            raise LLMException(f"LLM非同期呼び出し中にエラーが発生しました: {e}", details={
                "model": self.model_name,
                "error": str(e)
            })
    
    def call_with_prompt(self, prompt_template: str, **kwargs) -> str:
        """
        プロンプトテンプレートを使用してLLMを呼び出す
        
        Args:
            prompt_template: プロンプトテンプレート
            **kwargs: テンプレートに埋め込む変数
            
        Returns:
            LLMからのレスポンス
        """
        # プロンプトテンプレートを変数で埋める
        prompt = prompt_template.format(**kwargs)
        
        # ユーザーメッセージとして送信
        messages = [Message(MessageRole.USER, prompt)]
        
        return self.call(messages)
    
    async def acall_with_prompt(self, prompt_template: str, **kwargs) -> str:
        """
        プロンプトテンプレートを使用してLLMを非同期で呼び出す
        
        Args:
            prompt_template: プロンプトテンプレート
            **kwargs: テンプレートに埋め込む変数
            
        Returns:
            LLMからのレスポンス
        """
        # プロンプトテンプレートを変数で埋める
        prompt = prompt_template.format(**kwargs)
        
        # ユーザーメッセージとして送信
        messages = [Message(MessageRole.USER, prompt)]
        
        return await self.acall(messages)
    
    
    def call_with_json_response(self, messages: List["Message"], **kwargs) -> Dict[str, Any]:
        """
        Calls LLM and robustly extracts JSON from its response.

        Args:
            messages: List of prompt messages.
            **kwargs: Additional parameters.

        Returns:
            Parsed JSON dictionary.
        """
        response = self.call(messages, **kwargs)

        try:
            import regex
            # 1. Extract all ```json ... ``` blocks
            json_blocks = regex.findall(r"```json\s*(\{(?:[^{}]|(?R))*\})\s*```", response, regex.DOTALL)
            for block in json_blocks:
                try:
                    logger.debug("Trying to parse JSON from code block.")
                    return json.loads(block)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse block from ```json``` code block: {e}")
                    continue  # Try other methods

            # 2. Try to extract the first top-level { ... } block
            brace_match = regex.search(r"(\{(?:[^{}]|(?R))*\})", response, regex.DOTALL)
            if brace_match:
                json_str = brace_match.group(1)
                try:
                    logger.debug("Trying to parse JSON from top-level braces.")
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse top-level braces JSON: {e}")

            # 3. Fallback: try the entire response
            logger.warning("Attempting to parse entire response as JSON.")
            return json.loads(response)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            raise LLMResponseFormatException("LLMレスポンスをJSONとしてパースできませんでした", details={
                "response": response,
                "error": str(e)
            })

    async def acall_with_json_response(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """
        LLMを非同期で呼び出し、JSONレスポンスを取得する
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            JSONとしてパースされたLLMレスポンス
        """
        response = await self.acall(messages, **kwargs)
        
        try:
            # MarkdownコードブロックからJSONを抽出
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                logger.debug(f"Extracted JSON string: {json_str}")
                return json.loads(json_str)
            else:
                # コードブロックが見つからない場合は、レスポンス全体をJSONとしてパースを試みる
                logger.warning("JSON code block not found in LLM response, attempting to parse entire response as JSON.")
                return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            raise LLMResponseFormatException("LLMレスポンスをJSONとしてパースできませんでした", details={
                "response": response,
                "error": str(e)
            })


class OpenAIClient(LLMClient):
    """OpenAI APIを使用するLLMクライアント"""
    
    def _setup_client(self) -> None:
        """OpenAIクライアントの設定"""
        api_base = self.extra_params.get("api_base", config.llm.OPENAI_API_BASE.get_value())
        api_key = self.extra_params.get("api_key", config.llm.OPENAI_API_KEY.get_value())
        
        self.client = ChatOpenAI(
            model_name=self.model_name,
            openai_api_base=api_base,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=api_key,
            **{k: v for k, v in self.extra_params.items() if k not in ["api_base", "api_key"]}
        )
    
    def _call_llm(self, messages: List[Message], **kwargs) -> str:
        """
        OpenAI APIを使用してLLMを呼び出す
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        # メッセージをLangChain形式に変換
        langchain_messages = []
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=message.content))
        
        # LLMを呼び出す
        response = self.client.invoke(langchain_messages)
        
        # レスポンスからコンテンツを取得
        return response.content
    
    async def _acall_llm(self, messages: List[Message], **kwargs) -> str:
        """
        OpenAI APIを使用してLLMを非同期で呼び出す
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        # メッセージをLangChain形式に変換
        langchain_messages = []
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=message.content))
        
        # LLMを非同期で呼び出す
        response = await self.client.ainvoke(langchain_messages)
        
        # レスポンスからコンテンツを取得
        return response.content


class AnthropicClient(LLMClient):
    """Anthropic APIを使用するLLMクライアント"""
    
    def _setup_client(self) -> None:
        """Anthropicクライアントの設定"""
        # 注: 実際のAnthropicクライアントの実装は、Anthropic APIのPythonクライアントに依存します
        # ここでは、将来的な実装のためのプレースホルダーとして定義しています
        try:
            from langchain_anthropic import ChatAnthropic
            
            api_key = self.extra_params.get("api_key", config.llm.ANTHROPIC_API_KEY.get_value())
            
            self.client = ChatAnthropic(
                model_name=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                anthropic_api_key=api_key,
                **{k: v for k, v in self.extra_params.items() if k != "api_key"}
            )
        except (ImportError, AttributeError):
            logger.warning("Anthropic APIクライアントのインポートに失敗しました。モックを使用します。")
            self.client = None
    
    def _call_llm(self, messages: List[Message], **kwargs) -> str:
        """
        Anthropic APIを使用してLLMを呼び出す
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        if self.client is None:
            raise LLMException("Anthropic APIクライアントが初期化されていません")
        
        # メッセージをLangChain形式に変換
        langchain_messages = []
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=message.content))
        
        # LLMを呼び出す
        response = self.client.invoke(langchain_messages)
        
        # レスポンスからコンテンツを取得
        return response.content
    
    async def _acall_llm(self, messages: List[Message], **kwargs) -> str:
        """
        Anthropic APIを使用してLLMを非同期で呼び出す
        
        Args:
            messages: メッセージのリスト
            **kwargs: その他のパラメータ
            
        Returns:
            LLMからのレスポンス
        """
        if self.client is None:
            raise LLMException("Anthropic APIクライアントが初期化されていません")
        
        # メッセージをLangChain形式に変換
        langchain_messages = []
        for message in messages:
            if message.role == MessageRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=message.content))
            elif message.role == MessageRole.USER:
                langchain_messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=message.content))
        
        # LLMを非同期で呼び出す
        response = await self.client.ainvoke(langchain_messages)
        
        # レスポンスからコンテンツを取得
        return response.content


class LLMClientFactory:
    """LLMクライアントのファクトリークラス"""
    
    @staticmethod
    def create(
        provider_type: LLMProviderType,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMClient:
        """
        LLMクライアントを作成する
        
        Args:
            provider_type: LLMプロバイダーの種類
            model_name: モデル名（指定しない場合は設定から取得）
            temperature: 温度パラメータ（0.0〜1.0）
            max_tokens: 最大トークン数
            **kwargs: その他のパラメータ
            
        Returns:
            LLMクライアント
        """
        if provider_type == LLMProviderType.OPENAI:
            model = model_name or config.llm.MODEL_NAME.get_value()
            return OpenAIClient(model, temperature, max_tokens, **kwargs)
        elif provider_type == LLMProviderType.ANTHROPIC:
            model = model_name or config.llm.ANTHROPIC_MODEL_NAME.get_value()
            return AnthropicClient(model, temperature, max_tokens, **kwargs)
        elif provider_type == LLMProviderType.LOCAL:
            # ローカルモデルの場合は、OpenAIクライアントを使用し、APIベースを設定
            model = model_name or config.llm.MODEL_NAME.get_value()
            api_base = kwargs.get("api_base", config.llm.OPENAI_API_BASE.get_value())
            return OpenAIClient(model, temperature, max_tokens, api_base=api_base, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider type: {provider_type}")
    
    @staticmethod
    def create_from_config(config_dict: Dict[str, Any]) -> LLMClient:
        """
        設定から LLMクライアントを作成する
        
        Args:
            config_dict: LLMクライアントの設定
            
        Returns:
            LLMクライアント
        """
        provider_type = LLMProviderType(config_dict.get("provider", "openai"))
        model_name = config_dict.get("model_name")
        temperature = config_dict.get("temperature", 0.0)
        max_tokens = config_dict.get("max_tokens")
        
        # その他のパラメータを抽出
        kwargs = {k: v for k, v in config_dict.items() if k not in ["provider", "model_name", "temperature", "max_tokens"]}
        
        return LLMClientFactory.create(provider_type, model_name, temperature, max_tokens, **kwargs)
    
    @staticmethod
    def create_default() -> LLMClient:
        """
        デフォルト設定でLLMクライアントを作成する
        
        Returns:
            LLMクライアント
        """
        # 設定からプロバイダータイプを決定
        provider_value = config.llm.PROVIDER.get_value()
        if provider_value:
            provider_type = LLMProviderType(provider_value.lower())
        else:
            # デフォルトはOpenAI
            provider_type = LLMProviderType.OPENAI
        
        return LLMClientFactory.create(provider_type)