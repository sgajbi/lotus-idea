from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol, Sequence


class SchemaCursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> object: ...

    def fetchall(self) -> Sequence[Sequence[Any]]: ...


def postgres_idea_schema_fingerprint(cursor: SchemaCursor) -> str:
    inventory = {
        "columns": _read_rows(cursor, _COLUMN_INVENTORY_SQL),
        "constraints": _read_rows(cursor, _CONSTRAINT_INVENTORY_SQL),
        "indexes": _read_rows(cursor, _INDEX_INVENTORY_SQL),
    }
    encoded = json.dumps(
        inventory,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _read_rows(cursor: SchemaCursor, query: str) -> list[list[Any]]:
    cursor.execute(query)
    return [[_normalize_value(value) for value in row] for row in cursor.fetchall()]


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split())
    return value


_COLUMN_INVENTORY_SQL = """
SELECT
    table_name,
    column_name,
    ordinal_position,
    data_type,
    udt_name,
    is_nullable,
    COALESCE(column_default, '')
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name LIKE 'idea\\_%' ESCAPE '\\'
ORDER BY table_name, ordinal_position
"""

_CONSTRAINT_INVENTORY_SQL = """
SELECT
    relation.relname,
    constraint_record.conname,
    constraint_record.contype,
    pg_get_constraintdef(constraint_record.oid, true)
FROM pg_constraint AS constraint_record
JOIN pg_class AS relation ON relation.oid = constraint_record.conrelid
JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
WHERE namespace.nspname = 'public'
  AND relation.relname LIKE 'idea\\_%' ESCAPE '\\'
ORDER BY relation.relname, constraint_record.conname
"""

_INDEX_INVENTORY_SQL = """
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename LIKE 'idea\\_%' ESCAPE '\\'
ORDER BY tablename, indexname
"""
