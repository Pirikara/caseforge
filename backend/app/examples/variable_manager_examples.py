import asyncio
import json
from app.services.test.variable_manager import (
    VariableManager, 
    VariableScope, 
    VariableType,
    VariableNotFoundError,
    CircularReferenceError
)

async def main():
    """変数管理クラスの使用例"""
    print("=== 変数管理クラスの使用例 ===")
    
    # 変数管理クラスのインスタンス作成
    var_manager = VariableManager()
    
    # 基本的な変数の設定と取得
    print("\n--- 基本的な変数の設定と取得 ---")
    var_manager.set_variable("user_id", 12345, VariableScope.GLOBAL, VariableType.INTEGER, "ユーザーID")
    var_manager.set_variable("username", "test_user", VariableScope.CASE)
    var_manager.set_variable("is_admin", False, VariableScope.CASE, VariableType.BOOLEAN)
    
    print(f"user_id: {var_manager.get_variable('user_id')}")
    print(f"username: {var_manager.get_variable('username')}")
    print(f"is_admin: {var_manager.get_variable('is_admin')}")
    
    # 型の自動推論
    print("\n--- 型の自動推論 ---")
    var_manager.set_variable("auto_int", 100)
    var_manager.set_variable("auto_float", 3.14)
    var_manager.set_variable("auto_bool", True)
    var_manager.set_variable("auto_list", [1, 2, 3])
    var_manager.set_variable("auto_dict", {"key": "value"})
    
    # 変数の型付き取得
    print("\n--- 変数の型付き取得 ---")
    try:
        int_value = var_manager.get_variable_with_type("auto_int", int)
        print(f"auto_int (int): {int_value}")
        
        # 型が一致しない場合はエラー
        str_value = var_manager.get_variable_with_type("auto_int", str)
        print(f"auto_int (str): {str_value}")  # この行は実行されない
    except Exception as e:
        print(f"型エラー: {e}")
    
    # スコープの優先順位
    print("\n--- スコープの優先順位 ---")
    var_manager.set_variable("priority", "グローバル値", VariableScope.GLOBAL)
    var_manager.set_variable("priority", "スイート値", VariableScope.SUITE)
    var_manager.set_variable("priority", "ケース値", VariableScope.CASE)
    var_manager.set_variable("priority", "ステップ値", VariableScope.STEP)
    
    print(f"priority: {var_manager.get_variable('priority')}")  # ステップ値が表示される
    
    # スコープのクリア
    var_manager.clear_scope(VariableScope.STEP)
    print(f"STEPクリア後のpriority: {var_manager.get_variable('priority')}")  # ケース値が表示される
    
    var_manager.clear_scope(VariableScope.CASE)
    print(f"CASEクリア後のpriority: {var_manager.get_variable('priority')}")  # スイート値が表示される
    
    # 変数の削除
    print("\n--- 変数の削除 ---")
    var_manager.delete_variable("username")
    try:
        print(f"username: {var_manager.get_variable('username')}")
    except VariableNotFoundError as e:
        print(f"変数が見つかりません: {e}")
    
    # 変数の置換
    print("\n--- 変数の置換 ---")
    var_manager.set_variable("first_name", "太郎")
    var_manager.set_variable("last_name", "山田")
    
    template = "こんにちは、${last_name} ${first_name}さん！"
    replaced = var_manager.replace_variables_in_string(template)
    print(f"テンプレート: {template}")
    print(f"置換後: {replaced}")
    
    # オブジェクト内の変数置換
    print("\n--- オブジェクト内の変数置換 ---")
    obj = {
        "user": {
            "name": "${first_name}",
            "full_name": "${last_name} ${first_name}",
            "id": "${user_id}"
        },
        "permissions": ["read", "write"],
        "is_admin": "${is_admin}"
    }
    
    replaced_obj = var_manager.replace_variables_in_object(obj)
    print(f"置換後のオブジェクト: {json.dumps(replaced_obj, ensure_ascii=False, indent=2)}")
    
    # 循環参照の検出
    print("\n--- 循環参照の検出 ---")
    var_manager.set_variable("var1", "${var2}")
    var_manager.set_variable("var2", "${var3}")
    var_manager.set_variable("var3", "${var1}")
    
    try:
        result = var_manager.replace_variables_in_string("${var1}")
        print(f"置換結果: {result}")
    except CircularReferenceError as e:
        print(f"循環参照が検出されました: {e}")
    
    # 動的変数生成
    print("\n--- 動的変数生成 ---")
    random_str = var_manager.generate_random_string(8, name="random_str")
    print(f"ランダム文字列: {random_str}")
    
    random_int = var_manager.generate_random_integer(1, 100, name="random_int")
    print(f"ランダム整数: {random_int}")
    
    uuid_str = var_manager.generate_uuid(name="uuid")
    print(f"UUID: {uuid_str}")
    
    timestamp = var_manager.generate_timestamp(name="timestamp")
    print(f"タイムスタンプ: {timestamp}")
    
    # 非同期関数の使用例
    print("\n--- 非同期関数の使用例 ---")
    template_async = "非同期処理での置換: ${first_name} (ID: ${user_id})"
    replaced_async = await var_manager.replace_variables_in_string_async(template_async)
    print(replaced_async)
    
    # 実際のテストシナリオでの使用例
    print("\n--- 実際のテストシナリオでの使用例 ---")
    
    # テストスイートの開始
    print("テストスイートの開始")
    var_manager.clear_scope(VariableScope.STEP)
    var_manager.clear_scope(VariableScope.CASE)
    var_manager.set_variable("base_url", "https://api.example.com", VariableScope.SUITE)
    var_manager.set_variable("api_version", "v1", VariableScope.SUITE)
    
    # テストケース1: ユーザー作成
    print("\nテストケース1: ユーザー作成")
    var_manager.clear_scope(VariableScope.STEP)
    var_manager.set_variable("new_user_id", None, VariableScope.CASE)
    
    # ステップ1: ユーザー作成リクエスト
    print("ステップ1: ユーザー作成リクエスト")
    var_manager.clear_scope(VariableScope.STEP)
    var_manager.set_variable("username", f"user_{var_manager.generate_random_string(5)}", VariableScope.STEP)
    var_manager.set_variable("email", f"{var_manager.get_variable('username')}@example.com", VariableScope.STEP)
    
    # リクエストボディの作成（変数置換）
    request_body = {
        "username": "${username}",
        "email": "${email}",
        "password": "password123"
    }
    
    replaced_body = var_manager.replace_variables_in_object(request_body)
    print(f"リクエストボディ: {json.dumps(replaced_body, ensure_ascii=False)}")
    
    # レスポンスからの値抽出（実際のAPIレスポンスの代わりにモック）
    mock_response = {
        "id": 12345,
        "username": replaced_body["username"],
        "email": replaced_body["email"],
        "created_at": "2025-05-16T01:30:00Z"
    }
    
    # 抽出した値を変数に設定
    var_manager.set_variable("new_user_id", mock_response["id"], VariableScope.CASE)
    var_manager.set_variable("created_at", mock_response["created_at"], VariableScope.CASE)
    
    print(f"抽出した値 - user_id: {var_manager.get_variable('new_user_id')}")
    
    # ステップ2: 作成したユーザーの取得
    print("\nステップ2: 作成したユーザーの取得")
    var_manager.clear_scope(VariableScope.STEP)
    
    # パスパラメータの置換
    path_template = "/users/${new_user_id}"
    path = var_manager.replace_variables_in_string(path_template)
    print(f"リクエストパス: {path}")
    
    # テストケース2: ユーザー更新
    print("\nテストケース2: ユーザー更新")
    var_manager.clear_scope(VariableScope.STEP)
    var_manager.set_variable("updated_username", f"updated_{var_manager.get_variable('username')}", VariableScope.CASE)
    
    # パスパラメータとリクエストボディの置換
    path_template = "/users/${new_user_id}"
    path = var_manager.replace_variables_in_string(path_template)
    
    request_body = {
        "username": "${updated_username}"
    }
    
    replaced_body = var_manager.replace_variables_in_object(request_body)
    print(f"リクエストパス: {path}")
    print(f"リクエストボディ: {json.dumps(replaced_body, ensure_ascii=False)}")
    
    print("\n=== 変数管理クラスの使用例終了 ===")

if __name__ == "__main__":
    asyncio.run(main())