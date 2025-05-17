from sqlalchemy.types import TypeDecorator, TEXT
import json

class JSONEncodedDict(TypeDecorator):
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}