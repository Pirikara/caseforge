import pytest
from app.services.openapi.parser import EndpointParser

TEST_SERVICE_ID = 1

from app.services.openapi.parser import EndpointParser, _resolve_references, parse_openapi_schema # Import the common parser and resolver function

TEST_SERVICE_ID = 1

def test_resolve_references_simple():
    """シンプルな$ref参照が正しく解決されるかテスト"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    SimpleSchema:
      type: object
      properties:
        id:
          type: integer
    AnotherSchema:
      $ref: '#/components/schemas/SimpleSchema'
"""
    # Use the common _resolve_references function directly
    schema, resolved_schema = parse_openapi_schema(schema_content=schema_content)
    another_schema_part = schema["components"]["schemas"]["AnotherSchema"]
    resolved_another_schema = _resolve_references(another_schema_part, schema)

    assert "type" in resolved_another_schema
    assert resolved_another_schema["type"] == "object"
    assert "properties" in resolved_another_schema
    assert "id" in resolved_another_schema["properties"]
    assert resolved_another_schema["properties"]["id"]["type"] == "integer"

def test_resolve_references_nested():
    """ネストされた$ref参照が正しく解決されるかテスト"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    Address:
      type: object
      properties:
        street:
          type: string
    User:
      type: object
      properties:
        name:
          type: string
        address:
          $ref: '#/components/schemas/Address'
    UserProfile:
      type: object
      properties:
        user:
          $ref: '#/components/schemas/User'
"""
    # Use the common _resolve_references function directly
    schema, resolved_schema = parse_openapi_schema(schema_content=schema_content)
    user_profile_schema_part = schema["components"]["schemas"]["UserProfile"]
    resolved_user_profile_schema = _resolve_references(user_profile_schema_part, schema)

    assert "properties" in resolved_user_profile_schema
    assert "user" in resolved_user_profile_schema["properties"]
    user_schema = resolved_user_profile_schema["properties"]["user"]
    assert "properties" in user_schema
    assert "name" in user_schema["properties"]
    assert user_schema["properties"]["name"]["type"] == "string"
    assert "address" in user_schema["properties"]
    address_schema = user_schema["properties"]["address"]
    assert "properties" in address_schema
    assert "street" in address_schema["properties"]
    assert address_schema["properties"]["street"]["type"] == "string"

def test_resolve_references_array_items():
    """配列のitems内の$ref参照が正しく解決されるかテスト"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    Item:
      type: object
      properties:
        name:
          type: string
    ItemList:
      type: array
      items:
        $ref: '#/components/schemas/Item'
"""
    schema, resolved_schema = parse_openapi_schema(schema_content=schema_content)
    item_list_schema_part = schema["components"]["schemas"]["ItemList"]
    resolved_item_list_schema = _resolve_references(item_list_schema_part, schema)

    assert "type" in resolved_item_list_schema
    assert resolved_item_list_schema["type"] == "array"
    assert "items" in resolved_item_list_schema
    item_schema = resolved_item_list_schema["items"]
    assert "type" in item_schema
    assert item_schema["type"] == "object"
    assert "properties" in item_schema
    assert "name" in item_schema["properties"]
    assert item_schema["properties"]["name"]["type"] == "string"

def test_resolve_references_composite_types():
    """allOf, anyOf, oneOf内の$ref参照が正しく解決されるかテスト"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    ErrorModel:
      type: object
      properties:
        code:
          type: integer
    ValidationError:
      allOf:
        - $ref: '#/components/schemas/ErrorModel'
        - type: object
          properties:
            message:
              type: string
"""
    # Use the common _resolve_references function directly
    schema, resolved_schema = parse_openapi_schema(schema_content=schema_content)
    validation_error_schema_part = schema["components"]["schemas"]["ValidationError"]
    resolved_validation_error_schema = _resolve_references(validation_error_schema_part, schema)

    assert "allOf" in resolved_validation_error_schema
    assert isinstance(resolved_validation_error_schema["allOf"], list)
    assert len(resolved_validation_error_schema["allOf"]) == 2

    error_model_schema = resolved_validation_error_schema["allOf"][0]
    assert "type" in error_model_schema
    assert error_model_schema["type"] == "object"
    assert "properties" in error_model_schema
    assert "code" in error_model_schema["properties"]
    assert error_model_schema["properties"]["code"]["type"] == "integer"

    validation_error_schema = resolved_validation_error_schema["allOf"][1]
    assert "type" in validation_error_schema
    assert validation_error_schema["type"] == "object"
    assert "properties" in validation_error_schema
    assert "message" in validation_error_schema["properties"]
    assert validation_error_schema["properties"]["message"]["type"] == "string"

def test_resolve_references_non_existent():
    """存在しない$ref参照がエラーにならないかテスト"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    SchemaWithBadRef:
      $ref: '#/components/schemas/NonExistentSchema'
"""
    schema, resolved_schema = parse_openapi_schema(schema_content=schema_content)
    schema_with_bad_ref_part = schema["components"]["schemas"]["SchemaWithBadRef"]
    resolved_schema_with_bad_ref = _resolve_references(schema_with_bad_ref_part, schema)

    assert "$ref" in resolved_schema_with_bad_ref
    assert resolved_schema_with_bad_ref["$ref"] == '#/components/schemas/NonExistentSchema'

def test_resolve_references_circular():
    """循環参照が無限ループにならないかテスト (簡易的なチェック)"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths: {}
components:
  schemas:
    A:
      properties:
        b:
          $ref: '#/components/schemas/B'
    B:
      properties:
        a:
          $ref: '#/components/schemas/A'
"""
    schema, resolved_schema = parse_openapi_schema(schema_content=schema_content)
    schema_a_part = schema["components"]["schemas"]["A"]
    try:
        resolved_schema_a = _resolve_references(schema_a_part, schema)
        assert isinstance(resolved_schema_a, dict)
    except RecursionError:
        pytest.fail("Circular reference caused RecursionError")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred: {e}")

def test_parse_endpoints_with_ref():
    """$refを含むスキーマでエンドポイントが正しくパースされるかテスト"""
    schema_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /items:
    post:
      summary: Create a new item
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'
      responses:
        '201':
          description: Item created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Item'
components:
  schemas:
    Item:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
"""
    parser = EndpointParser(schema_content)
    endpoints = parser.parse_endpoints(TEST_SERVICE_ID)

    assert len(endpoints) == 1
    endpoint = endpoints[0]

    assert endpoint["path"] == "/items"
    assert endpoint["method"] == "POST"
    assert endpoint["summary"] == "Create a new item"

    assert "request_body" in endpoint
    request_body_schema = endpoint["request_body"]
    assert "content" in request_body_schema
    assert "application/json" in request_body_schema["content"]
    request_body_schema_content = request_body_schema["content"]["application/json"].get("schema")
    assert request_body_schema_content is not None
    assert "$ref" not in request_body_schema_content
    assert "type" in request_body_schema_content
    assert request_body_schema_content["type"] == "object"
    assert "properties" in request_body_schema_content
    assert "id" in request_body_schema_content["properties"]
    assert request_body_schema_content["properties"]["id"]["type"] == "integer"
    assert "name" in request_body_schema_content["properties"]
    assert request_body_schema_content["properties"]["name"]["type"] == "string"

    assert "responses" in endpoint
    response_201 = endpoint["responses"].get("201")
    assert response_201 is not None
    assert "content" in response_201
    response_schema = response_201["content"].get("application/json", {}).get("schema")
    assert response_schema is not None
    assert "$ref" not in response_schema
    assert "type" in response_schema
    assert response_schema["type"] == "object"
    assert "properties" in response_schema
    assert "id" in response_schema["properties"]
    assert response_schema["properties"]["id"]["type"] == "integer"
    assert "name" in response_schema["properties"]
    assert response_schema["properties"]["name"]["type"] == "string"
