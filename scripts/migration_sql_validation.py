from __future__ import annotations

import re


def contains_sql_statement(sql: str, statement: str) -> bool:
    normalized_sql = re.sub(r"\s+", " ", sql.upper())
    normalized_statement = re.sub(r"\s+", " ", statement.upper())
    return normalized_statement in normalized_sql


def validate_table_safe_rollback_alter_statements(
    migration_version: str,
    rollback_sql: str,
) -> list[str]:
    errors: list[str] = []
    for match in re.finditer(r"\bALTER\s+TABLE\s+(?!IF\s+EXISTS\b)", rollback_sql, re.IGNORECASE):
        line_number = rollback_sql.count("\n", 0, match.start()) + 1
        errors.append(
            f"Migration {migration_version} rollback line {line_number} uses "
            "ALTER TABLE without IF EXISTS"
        )
    return errors
