from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations"

REQUIRED_TABLES = (
    "idea_candidate_record",
    "idea_idempotency_record",
    "idea_lifecycle_history",
    "idea_audit_event",
    "idea_outbox_event",
    "idea_review_decision",
    "idea_feedback_event",
    "idea_conversion_intent",
    "idea_conversion_outcome",
    "idea_report_evidence_pack_request",
)

REQUIRED_INDEXES = (
    "idx_idea_candidate_record_family_status",
    "idx_idea_candidate_record_evidence_hash",
    "idx_idea_candidate_record_persisted_at",
    "idx_idea_idempotency_record_candidate",
    "idx_idea_lifecycle_history_candidate_time",
    "idx_idea_audit_event_candidate_time",
    "idx_idea_outbox_event_status_time",
    "idx_idea_outbox_event_aggregate_time",
    "idx_idea_review_decision_candidate_time",
    "idx_idea_feedback_event_candidate_time",
    "idx_idea_conversion_intent_candidate_target",
    "idx_idea_conversion_outcome_intent_time",
    "idx_idea_report_evidence_pack_candidate_time",
)

REQUIRED_FORWARD_FRAGMENTS = (
    "JSONB NOT NULL",
    "TIMESTAMPTZ NOT NULL",
    "PRIMARY KEY",
    "REFERENCES idea_candidate_record(candidate_id)",
    "REFERENCES idea_conversion_intent(conversion_intent_id)",
)

PROHIBITED_SQL_FRAGMENTS = (
    "TODO",
    "TBD",
    "PLACEHOLDER",
    "DROP TABLE IF EXISTS idea_candidate_record;",
)


class MigrationContract(NamedTuple):
    version: str
    forward_path: Path
    rollback_path: Path


REQUIRED_MIGRATIONS = (
    MigrationContract(
        version="001",
        forward_path=MIGRATIONS_DIR / "001_idea_repository_foundation.sql",
        rollback_path=MIGRATIONS_DIR / "001_idea_repository_foundation.rollback.sql",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _contains_sql_statement(sql: str, statement: str) -> bool:
    normalized_sql = re.sub(r"\s+", " ", sql.upper())
    normalized_statement = re.sub(r"\s+", " ", statement.upper())
    return normalized_statement in normalized_sql


def validate_migration_contracts(
    migrations: tuple[MigrationContract, ...] = REQUIRED_MIGRATIONS,
) -> list[str]:
    errors: list[str] = []
    for migration in migrations:
        if not migration.forward_path.exists():
            errors.append(
                f"Migration {migration.version} missing {_display_path(migration.forward_path)}"
            )
            continue
        if not migration.rollback_path.exists():
            errors.append(
                f"Migration {migration.version} missing rollback "
                f"{_display_path(migration.rollback_path)}"
            )
            continue

        forward_sql = _read(migration.forward_path)
        rollback_sql = _read(migration.rollback_path)
        errors.extend(_validate_forward_sql(migration, forward_sql))
        errors.extend(_validate_rollback_sql(migration, rollback_sql))
    return errors


def _validate_forward_sql(migration: MigrationContract, forward_sql: str) -> list[str]:
    errors: list[str] = []
    upper_forward = forward_sql.upper()
    for prohibited in PROHIBITED_SQL_FRAGMENTS:
        if prohibited in upper_forward:
            errors.append(
                f"Migration {migration.version} forward SQL contains prohibited "
                f"fragment `{prohibited}`"
            )
    for table in REQUIRED_TABLES:
        if not _contains_sql_statement(forward_sql, f"CREATE TABLE IF NOT EXISTS {table}"):
            errors.append(f"Migration {migration.version} missing table `{table}`")
    for index in REQUIRED_INDEXES:
        if not _contains_sql_statement(forward_sql, f"CREATE INDEX IF NOT EXISTS {index}"):
            errors.append(f"Migration {migration.version} missing index `{index}`")
    for fragment in REQUIRED_FORWARD_FRAGMENTS:
        if fragment.upper() not in upper_forward:
            errors.append(f"Migration {migration.version} forward SQL missing `{fragment}`")
    return errors


def _validate_rollback_sql(migration: MigrationContract, rollback_sql: str) -> list[str]:
    errors: list[str] = []
    for index in REQUIRED_INDEXES:
        if not _contains_sql_statement(rollback_sql, f"DROP INDEX IF EXISTS {index};"):
            errors.append(f"Migration {migration.version} rollback missing index `{index}`")
    for table in reversed(REQUIRED_TABLES):
        if not _contains_sql_statement(rollback_sql, f"DROP TABLE IF EXISTS {table};"):
            errors.append(f"Migration {migration.version} rollback missing table `{table}`")
    return errors


def main() -> int:
    errors = validate_migration_contracts()
    if errors:
        print("\n".join(errors))
        return 1
    print("Migration contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
