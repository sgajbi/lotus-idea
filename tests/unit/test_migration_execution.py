from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.infrastructure.migrations import (
    MigrationDirection,
    build_migration_plan,
    discover_migrations,
    dry_run_migration_plan,
    execute_migration_plan,
)


ROOT = Path(__file__).resolve().parents[2]


class RecordingCursor:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, query: str) -> None:
        self.statements.append(query)

    def __enter__(self) -> RecordingCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class RecordingConnection:
    def __init__(self) -> None:
        self.cursor_instance = RecordingCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FailingCursor(RecordingCursor):
    def execute(self, query: str) -> None:
        super().execute(query)
        raise RuntimeError("database rejected statement")


class FailingConnection(RecordingConnection):
    def __init__(self) -> None:
        super().__init__()
        self.cursor_instance = FailingCursor()


def test_discover_migrations_requires_rollbacks() -> None:
    migrations = discover_migrations(ROOT / "migrations")

    assert [migration.version for migration in migrations] == [
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
    ]
    assert migrations[0].rollback_path.name == "001_idea_repository_foundation.rollback.sql"
    assert migrations[1].rollback_path.name == "002_ai_explanation_lineage.rollback.sql"
    assert migrations[2].rollback_path.name == "003_outbox_event_contract_constraints.rollback.sql"


def test_dry_run_reports_apply_and_rollback_statement_counts() -> None:
    apply_plan = build_migration_plan(ROOT / "migrations", MigrationDirection.APPLY)
    rollback_plan = build_migration_plan(ROOT / "migrations", MigrationDirection.ROLLBACK)

    apply_records = dry_run_migration_plan(apply_plan)
    rollback_records = dry_run_migration_plan(rollback_plan)

    assert apply_records[0].direction is MigrationDirection.APPLY
    assert apply_records[0].statement_count > 0
    assert rollback_records[0].direction is MigrationDirection.ROLLBACK
    assert rollback_records[0].statement_count > 0


def test_candidate_state_rollback_is_safe_when_the_foundation_table_is_absent() -> None:
    rollback_sql = (ROOT / "migrations" / "005_candidate_state_policy.rollback.sql").read_text(
        encoding="utf-8"
    )

    assert "ALTER TABLE IF EXISTS idea_candidate_record" in rollback_sql


def test_conversion_outcome_migration_quarantines_without_deleting_legacy_history() -> None:
    apply_sql = (
        ROOT / "migrations" / "006_conversion_outcome_lifecycle.sql"
    ).read_text(encoding="utf-8")

    assert "idea_conversion_outcome_quarantine" in apply_sql
    assert "invalid_legacy_conversion_outcome_history" in apply_sql
    assert "DELETE FROM idea_conversion_outcome" not in apply_sql.upper()


def test_execute_migration_plan_commits_after_all_statements() -> None:
    connection = RecordingConnection()
    plan = build_migration_plan(ROOT / "migrations", MigrationDirection.APPLY)

    records = execute_migration_plan(connection, plan)

    assert [record.version for record in records] == [
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
    ]
    assert sum(record.statement_count for record in records) == len(
        connection.cursor_instance.statements
    )
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.cursor_instance.statements[0].startswith(
        "CREATE TABLE IF NOT EXISTS idea_candidate_record"
    )


def test_execute_migration_plan_rolls_back_on_error() -> None:
    connection = FailingConnection()
    plan = build_migration_plan(ROOT / "migrations", MigrationDirection.APPLY)

    with pytest.raises(RuntimeError, match="database rejected statement"):
        execute_migration_plan(connection, plan)

    assert connection.committed is False
    assert connection.rolled_back is True


def test_run_migrations_dry_run_cli_does_not_require_database_url() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_migrations.py"),
            "--direction",
            "apply",
            "--dry-run",
        ],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "apply 001_idea_repository_foundation" in result.stdout
    assert "apply 002_ai_explanation_lineage" in result.stdout
    assert "apply 003_outbox_event_contract_constraints" in result.stdout
    assert "Migration dry run passed" in result.stdout
