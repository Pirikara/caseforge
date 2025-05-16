"""
設定クラスの使用例

このモジュールでは、新しい設定クラスの使用方法を示します。
"""

import os
from app.config import config, settings, get_config

def show_config_usage():
    """新しい設定クラスの使用例"""
    print("=== 新しい設定クラスの使用例 ===")
    
    # 階層構造化された設定値の取得
    print(f"アプリケーション名: {config.app.NAME.get_value()}")
    print(f"デバッグモード: {config.app.DEBUG.get_value()}")
    
    # パス設定の取得
    print(f"スキーマディレクトリ: {config.paths.SCHEMA_DIR.get_value()}")
    print(f"テストディレクトリ: {config.paths.TESTS_DIR.get_value()}")
    
    # LLM設定の取得
    print(f"LLMモデル名: {config.llm.MODEL_NAME.get_value()}")
    print(f"OpenAI API ベースURL: {config.llm.OPENAI_API_BASE.get_value()}")
    
    # タイムアウト設定の取得
    print(f"デフォルトタイムアウト: {config.timeout.DEFAULT.get_value()}")
    print(f"LLM呼び出しタイムアウト: {config.timeout.LLM_CALL.get_value()}")
    
    # 設定値を辞書形式で取得
    config_dict = config.to_dict()
    print("\n設定値の辞書形式:")
    print(f"アプリケーション設定: {config_dict['app']}")
    print(f"パス設定: {config_dict['paths']}")


def show_compatibility():
    """従来の設定クラスとの互換性を示す例"""
    print("\n=== 従来の設定クラスとの互換性 ===")
    
    # 従来の設定値の取得
    print(f"アプリケーション名 (従来): {settings.APP_NAME}")
    print(f"デバッグモード (従来): {settings.DEBUG}")
    
    # 新しい設定クラスでの同等の設定値
    print(f"アプリケーション名 (新): {config.app.NAME.get_value()}")
    print(f"デバッグモード (新): {config.app.DEBUG.get_value()}")
    
    # 両方の設定値が同じであることを確認
    assert settings.APP_NAME == config.app.NAME.get_value()
    assert settings.DEBUG == config.app.DEBUG.get_value()
    print("互換性チェック: OK")


def show_environment_override():
    """環境変数による設定値の上書き例"""
    print("\n=== 環境変数による設定値の上書き ===")
    
    # 現在の設定値を表示
    print(f"現在のアプリケーション名: {config.app.NAME.get_value()}")
    
    # 環境変数で設定値を上書き
    os.environ["APP_NAME"] = "CaseforgeOverride"
    
    # キャッシュをクリアして設定を再読み込み
    config.clear_cache()
    
    # 上書きされた設定値を表示
    print(f"上書き後のアプリケーション名: {config.app.NAME.get_value()}")
    
    # 環境変数を元に戻す
    del os.environ["APP_NAME"]
    config.clear_cache()
    print(f"元に戻したアプリケーション名: {config.app.NAME.get_value()}")


def show_config_file_reload():
    """設定ファイルの再読み込み例"""
    print("\n=== 設定ファイルの再読み込み ===")
    
    # 現在の設定値を表示
    print(f"現在のアプリケーション名: {config.app.NAME.get_value()}")
    
    # 設定ファイルのパスを変更して再読み込み
    # 注: 実際には別の設定ファイルを用意する必要があります
    config.config_file = "another_config.yaml"
    config.reload()
    
    # 設定ファイルが存在しない場合はデフォルト値が使用される
    print(f"再読み込み後のアプリケーション名: {config.app.NAME.get_value()}")
    
    # 元の設定ファイルに戻す
    config.config_file = "config.yaml"
    config.reload()
    print(f"元の設定ファイルに戻した後のアプリケーション名: {config.app.NAME.get_value()}")


def show_singleton_pattern():
    """シングルトンパターンの例"""
    print("\n=== シングルトンパターン ===")
    
    # get_config()を使用して設定インスタンスを取得
    config1 = get_config()
    config2 = get_config()
    
    # 同じインスタンスであることを確認
    print(f"config1 id: {id(config1)}")
    print(f"config2 id: {id(config2)}")
    print(f"同じインスタンス: {config1 is config2}")


def main():
    """メイン関数"""
    show_config_usage()
    show_compatibility()
    show_environment_override()
    show_config_file_reload()
    show_singleton_pattern()


if __name__ == "__main__":
    main()