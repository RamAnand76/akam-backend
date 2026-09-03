import json
from datetime import datetime
from sqlalchemy import DateTime, TypeDecorator, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class JSONType(TypeDecorator):
    """Platform-independent JSON type (stores as JSON/Text in SQLite, JSONB in PostgreSQL)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return json.dumps({})

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return {}


class VectorType(TypeDecorator):
    """Platform-independent Vector type (stores as serialized JSON array in SQLite, vector in PostgreSQL)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None
