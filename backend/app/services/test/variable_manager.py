import json
import re
import uuid
import random
import string
import datetime
from typing import Dict, Any, Optional, TypeVar, Type
from enum import Enum
from pydantic import BaseModel, Field, ValidationError, field_validator

class VariableType(str, Enum):
    """変数の型を定義する列挙型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    NULL = "null"
    ANY = "any"

class VariableScope(str, Enum):
    """変数のスコープを定義する列挙型"""
    GLOBAL = "global"  # 全テストで共有
    SUITE = "suite"    # テストスイート内で共有
    CASE = "case"      # テストケース内で共有
    STEP = "step"      # テストステップ内のみ
    SESSION = "session"  # セッション内で共有（永続化）

class Variable(BaseModel):
    """変数を表すモデル"""
    name: str
    value: Any
    type: VariableType
    scope: VariableScope
    description: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)

    @field_validator('value')
    def validate_value_type(cls, v, info):
        values = info.data
        """値の型を検証する"""
        if 'type' not in values:
            return v
        
        var_type = values['type']
        
        if var_type == VariableType.STRING:
            if not isinstance(v, str):
                raise ValueError(f"Value must be a string, got {type(v)}")
        elif var_type == VariableType.INTEGER:
            if not isinstance(v, int) or isinstance(v, bool):
                raise ValueError(f"Value must be an integer, got {type(v)}")
        elif var_type == VariableType.FLOAT:
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ValueError(f"Value must be a float, got {type(v)}")
        elif var_type == VariableType.BOOLEAN:
            if not isinstance(v, bool):
                raise ValueError(f"Value must be a boolean, got {type(v)}")
        elif var_type == VariableType.LIST:
            if not isinstance(v, list):
                raise ValueError(f"Value must be a list, got {type(v)}")
        elif var_type == VariableType.DICT:
            if not isinstance(v, dict):
                raise ValueError(f"Value must be a dict, got {type(v)}")
        elif var_type == VariableType.NULL:
            if v is not None:
                raise ValueError(f"Value must be None, got {type(v)}")
        
        return v

class CircularReferenceError(Exception):
    """変数の循環参照を検出した場合に発生する例外"""
    pass

class VariableNotFoundError(Exception):
    """変数が見つからない場合に発生する例外"""
    pass

class VariableTypeError(Exception):
    """変数の型が一致しない場合に発生する例外"""
    pass

T = TypeVar('T')

class VariableManager:
    """変数管理クラス"""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        変数管理クラスの初期化
        
        Args:
            storage_path: 変数の永続化に使用するファイルパス
        """
        # スコープごとの変数辞書
        self._variables: Dict[VariableScope, Dict[str, Variable]] = {
            VariableScope.GLOBAL: {},
            VariableScope.SUITE: {},
            VariableScope.CASE: {},
            VariableScope.STEP: {},
            VariableScope.SESSION: {}
        }
        
        # 永続化用のファイルパス
        self._storage_path = storage_path
        
        # 永続化された変数の読み込み
        if storage_path:
            self._load_persistent_variables()
    
    def set_variable(self, name: str, value: Any, scope: VariableScope = VariableScope.CASE, 
                    var_type: Optional[VariableType] = None, description: Optional[str] = None) -> Variable:
        """
        変数を設定する
        
        Args:
            name: 変数名
            value: 変数の値
            scope: 変数のスコープ
            var_type: 変数の型（指定しない場合は自動判定）
            description: 変数の説明
            
        Returns:
            設定された変数
        """
        # 型の自動判定
        if var_type is None:
            var_type = self._infer_type(value)
        
        # 変数の作成
        variable = Variable(
            name=name,
            value=value,
            type=var_type,
            scope=scope,
            description=description
        )
        
        # 変数の保存
        self._variables[scope][name] = variable
        
        # セッションスコープの場合は永続化
        if scope == VariableScope.SESSION and self._storage_path:
            self._save_persistent_variables()
        
        return variable
    
    def get_variable(self, name: str, default: Optional[Any] = None) -> Any:
        """
        変数の値を取得する
        
        Args:
            name: 変数名
            default: 変数が見つからない場合のデフォルト値
            
        Returns:
            変数の値
        """
        variable = self._find_variable(name)
        if variable:
            return variable.value
        
        if default is not None:
            return default
        
        raise VariableNotFoundError(f"Variable '{name}' not found")
    
    def get_variable_with_type(self, name: str, expected_type: Type[T], default: Optional[T] = None) -> T:
        """
        指定した型で変数の値を取得する
        
        Args:
            name: 変数名
            expected_type: 期待する型
            default: 変数が見つからない場合のデフォルト値
            
        Returns:
            変数の値
        """
        value = self.get_variable(name, default)
        
        if not isinstance(value, expected_type):
            raise VariableTypeError(f"Variable '{name}' is not of type {expected_type.__name__}")
        
        return value
    
    def delete_variable(self, name: str) -> bool:
        """
        変数を削除する
        
        Args:
            name: 変数名
            
        Returns:
            削除に成功した場合はTrue、変数が見つからない場合はFalse
        """
        for scope in [VariableScope.STEP, VariableScope.CASE, VariableScope.SUITE, VariableScope.GLOBAL, VariableScope.SESSION]:
            if name in self._variables[scope]:
                del self._variables[scope][name]
                
                # セッションスコープの場合は永続化
                if scope == VariableScope.SESSION and self._storage_path:
                    self._save_persistent_variables()
                
                return True
        
        return False
    
    def clear_scope(self, scope: VariableScope) -> None:
        """
        指定したスコープの変数をすべて削除する
        
        Args:
            scope: クリアするスコープ
        """
        self._variables[scope].clear()
        
        # セッションスコープの場合は永続化
        if scope == VariableScope.SESSION and self._storage_path:
            self._save_persistent_variables()
    
    def replace_variables_in_string(self, template: str, max_depth: int = 10) -> str:
        """
        文字列内の変数参照を実際の値に置換する
        
        Args:
            template: 変数参照を含む文字列
            max_depth: 最大再帰深度（循環参照検出用）
            
        Returns:
            変数が置換された文字列
        """
        if max_depth <= 0:
            raise CircularReferenceError("Maximum recursion depth exceeded, possible circular reference")
        
        # ${variable_name} 形式の変数参照を検出
        pattern = r'\${([^}]+)}'
        
        def replace_match(match):
            var_name = match.group(1)
            try:
                value = self.get_variable(var_name)
                
                # 値が文字列の場合、さらに変数参照があるかもしれないので再帰的に置換
                if isinstance(value, str):
                    return self.replace_variables_in_string(value, max_depth - 1)
                
                # 文字列以外の場合は文字列に変換
                return str(value)
            except VariableNotFoundError:
                # 変数が見つからない場合は元のまま
                return match.group(0)
        
        return re.sub(pattern, replace_match, template)
    
    def replace_variables_in_object(self, obj: Any, max_depth: int = 10) -> Any:
        """
        オブジェクト内の変数参照を実際の値に置換する
        
        Args:
            obj: 変数参照を含むオブジェクト
            max_depth: 最大再帰深度（循環参照検出用）
            
        Returns:
            変数が置換されたオブジェクト
        """
        if max_depth <= 0:
            raise CircularReferenceError("Maximum recursion depth exceeded, possible circular reference")
        
        if isinstance(obj, str):
            return self.replace_variables_in_string(obj, max_depth)
        elif isinstance(obj, dict):
            return {k: self.replace_variables_in_object(v, max_depth - 1) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.replace_variables_in_object(item, max_depth - 1) for item in obj]
        else:
            return obj
    
    def generate_random_string(self, length: int = 10, include_digits: bool = True, 
                              include_special: bool = False, name: Optional[str] = None, 
                              scope: VariableScope = VariableScope.CASE) -> str:
        """
        ランダムな文字列を生成する
        
        Args:
            length: 生成する文字列の長さ
            include_digits: 数字を含めるかどうか
            include_special: 特殊文字を含めるかどうか
            name: 生成した値を保存する変数名（指定しない場合は保存しない）
            scope: 変数のスコープ
            
        Returns:
            生成されたランダム文字列
        """
        chars = string.ascii_letters
        if include_digits:
            chars += string.digits
        if include_special:
            chars += string.punctuation
        
        value = ''.join(random.choice(chars) for _ in range(length))
        
        if name:
            self.set_variable(name, value, scope, VariableType.STRING, "Generated random string")
        
        return value
    
    def generate_random_integer(self, min_value: int = 0, max_value: int = 1000, 
                               name: Optional[str] = None, scope: VariableScope = VariableScope.CASE) -> int:
        """
        ランダムな整数を生成する
        
        Args:
            min_value: 最小値
            max_value: 最大値
            name: 生成した値を保存する変数名（指定しない場合は保存しない）
            scope: 変数のスコープ
            
        Returns:
            生成されたランダム整数
        """
        value = random.randint(min_value, max_value)
        
        if name:
            self.set_variable(name, value, scope, VariableType.INTEGER, "Generated random integer")
        
        return value
    
    def generate_uuid(self, name: Optional[str] = None, scope: VariableScope = VariableScope.CASE) -> str:
        """
        UUIDを生成する
        
        Args:
            name: 生成した値を保存する変数名（指定しない場合は保存しない）
            scope: 変数のスコープ
            
        Returns:
            生成されたUUID
        """
        value = str(uuid.uuid4())
        
        if name:
            self.set_variable(name, value, scope, VariableType.STRING, "Generated UUID")
        
        return value
    
    def generate_timestamp(self, format_str: str = "%Y-%m-%dT%H:%M:%S.%fZ", 
                          name: Optional[str] = None, scope: VariableScope = VariableScope.CASE) -> str:
        """
        現在のタイムスタンプを生成する
        
        Args:
            format_str: 日時フォーマット
            name: 生成した値を保存する変数名（指定しない場合は保存しない）
            scope: 変数のスコープ
            
        Returns:
            生成されたタイムスタンプ
        """
        value = datetime.datetime.now().strftime(format_str)
        
        if name:
            self.set_variable(name, value, scope, VariableType.STRING, "Generated timestamp")
        
        return value
    
    def _infer_type(self, value: Any) -> VariableType:
        """
        値から型を推論する
        
        Args:
            value: 型を推論する値
            
        Returns:
            推論された型
        """
        if value is None:
            return VariableType.NULL
        elif isinstance(value, bool):
            return VariableType.BOOLEAN
        elif isinstance(value, int):
            return VariableType.INTEGER
        elif isinstance(value, float):
            return VariableType.FLOAT
        elif isinstance(value, str):
            return VariableType.STRING
        elif isinstance(value, list):
            return VariableType.LIST
        elif isinstance(value, dict):
            return VariableType.DICT
        else:
            return VariableType.ANY
    
    def _find_variable(self, name: str) -> Optional[Variable]:
        """
        変数を検索する（スコープの優先順位: STEP > CASE > SUITE > GLOBAL > SESSION）
        
        Args:
            name: 変数名
            
        Returns:
            見つかった変数、見つからない場合はNone
        """
        for scope in [VariableScope.STEP, VariableScope.CASE, VariableScope.SUITE, VariableScope.GLOBAL, VariableScope.SESSION]:
            if name in self._variables[scope]:
                return self._variables[scope][name]
        
        return None
    
    def _load_persistent_variables(self) -> None:
        """永続化された変数を読み込む"""
        try:
            with open(self._storage_path, 'r') as f:
                data = json.load(f)
                
                for var_data in data:
                    try:
                        variable = Variable(**var_data)
                        if variable.scope == VariableScope.SESSION:
                            self._variables[VariableScope.SESSION][variable.name] = variable
                    except ValidationError:
                        # 無効な変数データはスキップ
                        pass
        except (FileNotFoundError, json.JSONDecodeError):
            # ファイルが存在しないか、JSONとして解析できない場合は何もしない
            pass
    
    def _save_persistent_variables(self) -> None:
        """セッションスコープの変数を永続化する"""
        if not self._storage_path:
            return
        
        data = [var.dict() for var in self._variables[VariableScope.SESSION].values()]
        
        with open(self._storage_path, 'w') as f:
            json.dump(data, f, default=str)
    
    async def replace_variables_in_string_async(self, template: str, max_depth: int = 10) -> str:
        """
        文字列内の変数参照を実際の値に置換する（非同期版）
        
        Args:
            template: 変数参照を含む文字列
            max_depth: 最大再帰深度（循環参照検出用）
            
        Returns:
            変数が置換された文字列
        """
        # 非同期版も同じ実装で問題ない（内部で非同期処理を行わないため）
        return self.replace_variables_in_string(template, max_depth)
    
    async def replace_variables_in_object_async(self, obj: Any, max_depth: int = 10) -> Any:
        """
        オブジェクト内の変数参照を実際の値に置換する（非同期版）
        
        Args:
            obj: 変数参照を含むオブジェクト
            max_depth: 最大再帰深度（循環参照検出用）
            
        Returns:
            変数が置換されたオブジェクト
        """
        # 非同期版も同じ実装で問題ない（内部で非同期処理を行わないため）
        return self.replace_variables_in_object(obj, max_depth)