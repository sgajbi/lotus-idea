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
    "idea_downstream_submission",
)

REQUIRED_INDEXES = (
    "idx_idea_candidate_record_family_status",
    "idx_idea_candidate_record_review_queue_order",
    "idx_idea_candidate_record_scope_tenant",
    "idx_idea_candidate_record_scope_book",
    "idx_idea_candidate_record_scope_portfolio",
    "idx_idea_candidate_record_scope_client",
    "idx_idea_candidate_record_evidence_hash",
    "idx_idea_candidate_record_persisted_at",
    "idx_idea_idempotency_record_candidate",
    "idx_idea_lifecycle_history_candidate_time",
    "idx_idea_audit_event_candidate_time",
    "idx_idea_outbox_event_status_time",
    "idx_idea_outbox_event_retry_due",
    "idx_idea_outbox_event_lease_expiry",
    "idx_idea_outbox_event_aggregate_time",
    "idx_idea_review_decision_candidate_time",
    "idx_idea_feedback_event_candidate_time",
    "idx_idea_conversion_intent_candidate_target",
    "idx_idea_conversion_outcome_intent_time",
    "idx_idea_report_evidence_pack_candidate_time",
    "idx_idea_downstream_submission_resource",
)

REQUIRED_FORWARD_FRAGMENTS = (
    "JSONB NOT NULL",
    "TIMESTAMPTZ NOT NULL",
    "PRIMARY KEY",
    "REFERENCES idea_candidate_record(candidate_id)",
    "REFERENCES idea_conversion_intent(conversion_intent_id)",
    "ck_idea_outbox_event_event_type",
    "ck_idea_outbox_event_aggregate_type",
    "ck_idea_outbox_event_schema_version",
    "request_fingerprint TEXT NOT NULL",
    "resource_type TEXT NOT NULL",
    "resource_id TEXT NOT NULL",
    "source_authority TEXT NOT NULL",
    "submitted_at_utc TIMESTAMPTZ NOT NULL",
)

AI_LINEAGE_REQUIRED_TABLES = ("idea_ai_explanation_lineage",)

AI_LINEAGE_REQUIRED_INDEXES = (
    "idx_idea_ai_explanation_lineage_candidate_time",
    "idx_idea_ai_explanation_lineage_workflow_time",
    "idx_idea_ai_explanation_lineage_posture_time",
)

AI_LINEAGE_REQUIRED_FORWARD_FRAGMENTS = (
    "JSONB NOT NULL",
    "TIMESTAMPTZ NOT NULL",
    "PRIMARY KEY",
    "BOOLEAN NOT NULL",
    "REFERENCES idea_candidate_record(candidate_id)",
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
    required_tables: tuple[str, ...]
    required_indexes: tuple[str, ...]
    required_forward_fragments: tuple[str, ...]
    required_rollback_fragments: tuple[str, ...] = ()


REQUIRED_MIGRATIONS = (
    MigrationContract(
        version="001",
        forward_path=MIGRATIONS_DIR / "001_idea_repository_foundation.sql",
        rollback_path=MIGRATIONS_DIR / "001_idea_repository_foundation.rollback.sql",
        required_tables=REQUIRED_TABLES,
        required_indexes=REQUIRED_INDEXES,
        required_forward_fragments=REQUIRED_FORWARD_FRAGMENTS,
    ),
    MigrationContract(
        version="002",
        forward_path=MIGRATIONS_DIR / "002_ai_explanation_lineage.sql",
        rollback_path=MIGRATIONS_DIR / "002_ai_explanation_lineage.rollback.sql",
        required_tables=AI_LINEAGE_REQUIRED_TABLES,
        required_indexes=AI_LINEAGE_REQUIRED_INDEXES,
        required_forward_fragments=AI_LINEAGE_REQUIRED_FORWARD_FRAGMENTS,
    ),
    MigrationContract(
        version="003",
        forward_path=MIGRATIONS_DIR / "003_outbox_event_contract_constraints.sql",
        rollback_path=MIGRATIONS_DIR / "003_outbox_event_contract_constraints.rollback.sql",
        required_tables=(),
        required_indexes=(),
        required_forward_fragments=(
            "ALTER TABLE idea_outbox_event",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_event_type",
            "ADD CONSTRAINT ck_idea_outbox_event_event_type",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_aggregate_type",
            "ADD CONSTRAINT ck_idea_outbox_event_aggregate_type",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_schema_version",
            "ADD CONSTRAINT ck_idea_outbox_event_schema_version",
        ),
        required_rollback_fragments=(
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_event_type",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_aggregate_type",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_schema_version",
        ),
    ),
    MigrationContract(
        version="004",
        forward_path=MIGRATIONS_DIR / "004_outbox_dead_letter_recovery.sql",
        rollback_path=MIGRATIONS_DIR / "004_outbox_dead_letter_recovery.rollback.sql",
        required_tables=("idea_outbox_recovery_audit",),
        required_indexes=(
            "idx_idea_outbox_dead_letter_support_reference",
            "idx_idea_outbox_recovery_support_reference",
            "idx_idea_outbox_recovery_requested_at",
        ),
        required_forward_fragments=(
            "REFERENCES idea_outbox_event(outbox_event_id)",
            "idempotency_fingerprint TEXT NOT NULL UNIQUE",
            "request_fingerprint TEXT NOT NULL",
            "original_failure_reason TEXT NOT NULL",
            "original_first_failed_at_utc TIMESTAMPTZ NOT NULL",
            "original_last_failed_at_utc TIMESTAMPTZ NOT NULL",
            "CONSTRAINT uq_idea_outbox_recovery_event UNIQUE (outbox_event_id)",
            "CONSTRAINT ck_idea_outbox_recovery_lease_window",
            "sha256(outbox_event_id::bytea)",
        ),
    ),
    MigrationContract(
        version="006",
        forward_path=MIGRATIONS_DIR / "006_conversion_outcome_lifecycle.sql",
        rollback_path=MIGRATIONS_DIR / "006_conversion_outcome_lifecycle.rollback.sql",
        required_tables=("idea_conversion_outcome_quarantine",),
        required_indexes=(
            "idx_idea_conversion_outcome_current",
            "idx_idea_conversion_outcome_quarantine_intent",
        ),
        required_forward_fragments=(
            "source_event_version INTEGER",
            "supersedes_conversion_outcome_id TEXT",
            "correction_reason TEXT",
            "actor_subject TEXT",
            "CONSTRAINT uq_idea_conversion_outcome_intent_version",
            "UNIQUE (conversion_intent_id, source_event_version)",
            "CONSTRAINT fk_idea_conversion_outcome_supersedes",
            "CHECK (source_event_version > 0)",
            "invalid_legacy_conversion_outcome_history",
            "ON CONFLICT (conversion_outcome_id) DO NOTHING",
        ),
        required_rollback_fragments=(
            "DROP CONSTRAINT IF EXISTS fk_idea_conversion_outcome_supersedes",
            "DROP CONSTRAINT IF EXISTS uq_idea_conversion_outcome_intent_version",
            "DROP COLUMN IF EXISTS source_event_version",
            "DROP TABLE IF EXISTS idea_conversion_outcome_quarantine",
        ),
    ),
    MigrationContract(
        version="007",
        forward_path=MIGRATIONS_DIR / "007_outbox_event_lineage.sql",
        rollback_path=MIGRATIONS_DIR / "007_outbox_event_lineage.rollback.sql",
        required_tables=(),
        required_indexes=(),
        required_forward_fragments=(
            "trace_id TEXT",
            "lineage_origin TEXT",
            "ALTER COLUMN correlation_id SET NOT NULL",
            "ALTER COLUMN trace_id SET NOT NULL",
            "CONSTRAINT ck_idea_outbox_event_lineage_origin",
            "CONSTRAINT ck_idea_outbox_event_lineage_identifiers",
            "CONSTRAINT ck_idea_outbox_event_causation_origin",
            "legacy_migrated",
        ),
        required_rollback_fragments=(
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_causation_origin",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_lineage_identifiers",
            "DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_lineage_origin",
            "ALTER COLUMN correlation_id DROP NOT NULL",
            "DROP COLUMN IF EXISTS trace_id",
        ),
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
    for table in migration.required_tables:
        if not _contains_sql_statement(forward_sql, f"CREATE TABLE IF NOT EXISTS {table}"):
            errors.append(f"Migration {migration.version} missing table `{table}`")
    for index in migration.required_indexes:
        if not _contains_sql_statement(forward_sql, f"CREATE INDEX IF NOT EXISTS {index}"):
            errors.append(f"Migration {migration.version} missing index `{index}`")
    for fragment in migration.required_forward_fragments:
        if fragment.upper() not in upper_forward:
            errors.append(f"Migration {migration.version} forward SQL missing `{fragment}`")
    return errors


def _validate_rollback_sql(migration: MigrationContract, rollback_sql: str) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_table_safe_rollback_alter_statements(migration, rollback_sql))
    for index in migration.required_indexes:
        if not _contains_sql_statement(rollback_sql, f"DROP INDEX IF EXISTS {index};"):
            errors.append(f"Migration {migration.version} rollback missing index `{index}`")
    for table in reversed(migration.required_tables):
        if not _contains_sql_statement(rollback_sql, f"DROP TABLE IF EXISTS {table};"):
            errors.append(f"Migration {migration.version} rollback missing table `{table}`")
    upper_rollback = rollback_sql.upper()
    for fragment in migration.required_rollback_fragments:
        if fragment.upper() not in upper_rollback:
            errors.append(f"Migration {migration.version} rollback SQL missing `{fragment}`")
    return errors


def _validate_table_safe_rollback_alter_statements(
    migration: MigrationContract,
    rollback_sql: str,
) -> list[str]:
    errors: list[str] = []
    for match in re.finditer(r"\bALTER\s+TABLE\s+(?!IF\s+EXISTS\b)", rollback_sql, re.IGNORECASE):
        line_number = rollback_sql.count("\n", 0, match.start()) + 1
        errors.append(
            f"Migration {migration.version} rollback line {line_number} uses "
            "ALTER TABLE without IF EXISTS"
        )
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
