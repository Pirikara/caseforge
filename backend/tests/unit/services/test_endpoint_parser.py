import pytest
from app.services.endpoint_parser import EndpointParser

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
    parser = EndpointParser(schema_content)
    resolved_schema = parser._resolve_references(parser.schema["components"]["schemas"]["AnotherSchema"])

    assert "type" in resolved_schema
    assert resolved_schema["type"] == "object"
    assert "properties" in resolved_schema
    assert "id" in resolved_schema["properties"]
    assert resolved_schema["properties"]["id"]["type"] == "integer"

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
    parser = EndpointParser(schema_content)
    resolved_schema = parser._resolve_references(parser.schema["components"]["schemas"]["UserProfile"])

    assert "properties" in resolved_schema
    assert "user" in resolved_schema["properties"]
    user_schema = resolved_schema["properties"]["user"]
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
    parser = EndpointParser(schema_content)
    resolved_schema = parser._resolve_references(parser.schema["components"]["schemas"]["ItemList"])

    assert "type" in resolved_schema
    assert resolved_schema["type"] == "array"
    assert "items" in resolved_schema
    item_schema = resolved_schema["items"]
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
    parser = EndpointParser(schema_content)
    resolved_schema = parser._resolve_references(parser.schema["components"]["schemas"]["ValidationError"])

    assert "allOf" in resolved_schema
    assert isinstance(resolved_schema["allOf"], list)
    assert len(resolved_schema["allOf"]) == 2

    error_model_schema = resolved_schema["allOf"][0]
    assert "type" in error_model_schema
    assert error_model_schema["type"] == "object"
    assert "properties" in error_model_schema
    assert "code" in error_model_schema["properties"]
    assert error_model_schema["properties"]["code"]["type"] == "integer"

    validation_error_schema = resolved_schema["allOf"][1]
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
    parser = EndpointParser(schema_content)
    resolved_schema = parser._resolve_references(parser.schema["components"]["schemas"]["SchemaWithBadRef"])

    assert "$ref" in resolved_schema
    assert resolved_schema["$ref"] == '#/components/schemas/NonExistentSchema'

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
    parser = EndpointParser(schema_content)
    try:
        resolved_schema = parser._resolve_references(parser.schema["components"]["schemas"]["A"])
        assert isinstance(resolved_schema, dict)
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
    assert "type" in request_body_schema
    assert request_body_schema["type"] == "object"
    assert "properties" in request_body_schema
    assert "id" in request_body_schema["properties"]
    assert request_body_schema["properties"]["id"]["type"] == "integer"
    assert "name" in request_body_schema["properties"]
    assert request_body_schema["properties"]["name"]["type"] == "string"

    assert "responses" in endpoint
    response_201 = endpoint["responses"].get("201")
    assert response_201 is not None
    assert "content" in response_201
    response_schema = response_201["content"].get("application/json", {}).get("schema")
    assert response_schema is not None
    assert "type" in response_schema
    assert response_schema["type"] == "object"
    assert "properties" in response_schema
    assert "id" in response_schema["properties"]
    assert response_schema["properties"]["id"]["type"] == "integer"
    assert "name" in response_schema["properties"]
    assert response_schema["properties"]["name"]["type"] == "string"
