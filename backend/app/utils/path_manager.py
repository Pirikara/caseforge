import os
from pathlib import Path
from typing import Optional, Union, List, Any
import logging
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)

class PathManager:
    """
    パス管理クラス
    
    ファイルパスの取得と管理を一元化するためのクラス。
    プロジェクト内のパス関連の操作を統一的に扱うためのインターフェースを提供します。
    """
    
    def __init__(self):
        """
        PathManagerの初期化
        """
        # プロジェクトルートディレクトリの検出
        self._root_path = self._detect_project_root()
        
    @staticmethod
    @lru_cache(maxsize=1)
    def _detect_project_root() -> Path:
        """
        プロジェクトルートディレクトリを検出する
        
        Returns:
            Path: プロジェクトルートディレクトリのパス
        """
        # 環境変数からプロジェクトルートを取得
        if "PROJECT_ROOT" in os.environ:
            return Path(os.environ["PROJECT_ROOT"])
        
        # 現在のファイルの場所から推測
        current_file = Path(__file__).resolve()
        # backend/app/utils/path_manager.py から3階層上がルート
        return current_file.parent.parent.parent.parent
    
    def get_root_path(self) -> Path:
        """
        プロジェクトルートパスを取得する
        
        Returns:
            Path: プロジェクトルートディレクトリのパス
        """
        return self._root_path
    
    def get_config_path(self, filename: Optional[str] = None) -> Path:
        """
        設定ファイルのパスを取得する
        
        Args:
            filename (Optional[str]): 設定ファイル名。指定しない場合はディレクトリを返す
            
        Returns:
            Path: 設定ファイルのパス
        """
        if filename:
            return self._root_path / filename
        return self._root_path
    
    def get_schema_dir(self, project_id: Optional[str] = None) -> Path:
        """
        スキーマディレクトリのパスを取得する
        
        Args:
            project_id (Optional[str]): プロジェクトID。指定した場合はプロジェクト固有のディレクトリを返す
            
        Returns:
            Path: スキーマディレクトリのパス
        """
        schema_dir = Path(settings.SCHEMA_DIR)
        if project_id:
            return schema_dir / project_id
        return schema_dir
    
    def get_tests_dir(self, project_id: Optional[str] = None) -> Path:
        """
        テストディレクトリのパスを取得する
        
        Args:
            project_id (Optional[str]): プロジェクトID。指定した場合はプロジェクト固有のディレクトリを返す
            
        Returns:
            Path: テストディレクトリのパス
        """
        tests_dir = Path(settings.TESTS_DIR)
        if project_id:
            return tests_dir / project_id
        return tests_dir
    
    def get_log_dir(self, project_id: Optional[str] = None, run_id: Optional[str] = None) -> Path:
        """
        ログディレクトリのパスを取得する
        
        Args:
            project_id (Optional[str]): プロジェクトID。指定した場合はプロジェクト固有のディレクトリを返す
            run_id (Optional[str]): 実行ID。指定した場合は実行固有のログファイルパスを返す
            
        Returns:
            Path: ログディレクトリまたはログファイルのパス
        """
        log_dir = Path(settings.LOG_DIR)
        if project_id:
            project_log_dir = log_dir / project_id
            if run_id:
                return project_log_dir / f"{run_id}.json"
            return project_log_dir
        return log_dir
    
    def get_temp_dir(self, subdir: Optional[str] = None) -> Path:
        """
        一時ディレクトリのパスを取得する
        
        Args:
            subdir (Optional[str]): サブディレクトリ名
            
        Returns:
            Path: 一時ディレクトリのパス
        """
        temp_dir = Path("/tmp")
        if subdir:
            return temp_dir / subdir
        return temp_dir
    
    def get_faiss_dir(self, project_id: str, temp: bool = False) -> Path:
        """
        FAISSベクトルDBディレクトリのパスを取得する
        
        Args:
            project_id (str): プロジェクトID
            temp (bool): 一時ディレクトリを使用するかどうか
            
        Returns:
            Path: FAISSベクトルDBディレクトリのパス
        """
        if temp:
            return self.get_temp_dir("faiss") / project_id
        
        # 永続化ディレクトリのパス
        data_dir = os.environ.get("DATA_DIR", "/app/data")
        return Path(data_dir) / "faiss" / project_id
    
    def ensure_dir(self, path: Union[str, Path]) -> Path:
        """
        ディレクトリが存在することを確認し、存在しない場合は作成する
        
        Args:
            path (Union[str, Path]): 確認するディレクトリのパス
            
        Returns:
            Path: 確認したディレクトリのパス
        """
        path_obj = Path(path)
        if not path_obj.exists():
            path_obj.mkdir(parents=True, exist_ok=True)
            logger.debug(f"ディレクトリを作成しました: {path_obj}")
        return path_obj
    
    def ensure_file_dir(self, file_path: Union[str, Path]) -> Path:
        """
        ファイルの親ディレクトリが存在することを確認し、存在しない場合は作成する
        
        Args:
            file_path (Union[str, Path]): ファイルパス
            
        Returns:
            Path: ファイルの親ディレクトリのパス
        """
        path_obj = Path(file_path)
        parent_dir = path_obj.parent
        return self.ensure_dir(parent_dir)
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """
        パスを正規化する
        
        Args:
            path (Union[str, Path]): 正規化するパス
            
        Returns:
            Path: 正規化されたパス
        """
        return Path(path).resolve()
    
    def exists(self, path: Union[str, Path]) -> bool:
        """
        パスが存在するかどうかを確認する
        
        Args:
            path (Union[str, Path]): 確認するパス
            
        Returns:
            bool: パスが存在する場合はTrue、そうでない場合はFalse
        """
        return Path(path).exists()
    
    def is_file(self, path: Union[str, Path]) -> bool:
        """
        パスがファイルかどうかを確認する
        
        Args:
            path (Union[str, Path]): 確認するパス
            
        Returns:
            bool: パスがファイルの場合はTrue、そうでない場合はFalse
        """
        path_obj = Path(path)
        return path_obj.exists() and path_obj.is_file()
    
    def is_dir(self, path: Union[str, Path]) -> bool:
        """
        パスがディレクトリかどうかを確認する
        
        Args:
            path (Union[str, Path]): 確認するパス
            
        Returns:
            bool: パスがディレクトリの場合はTrue、そうでない場合はFalse
        """
        path_obj = Path(path)
        return path_obj.exists() and path_obj.is_dir()
    
    def join_path(self, *paths: Union[str, Path]) -> Path:
        """
        複数のパスを結合する
        
        Args:
            *paths (Union[str, Path]): 結合するパス
            
        Returns:
            Path: 結合されたパス
        """
        result = Path(paths[0])
        for path in paths[1:]:
            result = result / path
        return result
    
    def list_dir(self, path: Union[str, Path], pattern: Optional[str] = None) -> List[Path]:
        """
        ディレクトリ内のファイルとディレクトリを一覧表示する
        
        Args:
            path (Union[str, Path]): ディレクトリパス
            pattern (Optional[str]): 検索パターン
            
        Returns:
            List[Path]: ファイルとディレクトリのリスト
        """
        path_obj = Path(path)
        if not path_obj.exists() or not path_obj.is_dir():
            return []
        
        if pattern:
            return list(path_obj.glob(pattern))
        return list(path_obj.iterdir())
    
    def get_relative_path(self, path: Union[str, Path], base: Optional[Union[str, Path]] = None) -> Path:
        """
        ベースパスからの相対パスを取得する
        
        Args:
            path (Union[str, Path]): 対象パス
            base (Optional[Union[str, Path]]): ベースパス。指定しない場合はプロジェクトルートを使用
            
        Returns:
            Path: 相対パス
        """
        path_obj = Path(path).resolve()
        base_obj = Path(base).resolve() if base else self._root_path
        return path_obj.relative_to(base_obj)


# シングルトンインスタンスの作成
@lru_cache(maxsize=1)
def get_path_manager() -> PathManager:
    """
    PathManagerのシングルトンインスタンスを取得する
    
    Returns:
        PathManager: PathManagerのインスタンス
    """
    return PathManager()


# 使いやすいようにインスタンスをエクスポート
path_manager = get_path_manager()