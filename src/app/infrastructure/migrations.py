from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
from typing import Any, Protocol, Sequence


LOCAL_MIGRATION_ADVISORY_LOCK_ID = 3_688_460_714_239_083_374


class MigrationDirection(StrEnum):
    APPLY = "apply"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class MigrationStep:
    version: str
    name: str
    forward_path: Path
    rollback_path: Path

    @property
    def content_sha256(self) -> str:
        digest = hashlib.sha256()
        for value in (
            self.version.encode("utf-8"),
            b"\0",
            self.name.encode("utf-8"),
            b"\0",
            self.forward_path.read_bytes(),
            b"\0",
            self.rollback_path.read_bytes(),
        ):
            digest.update(value)
        return f"sha256:{digest.hexdigest()}"


@dataclass(frozen=True)
class MigrationExecutionPlan:
    direction: MigrationDirection
    steps: tuple[MigrationStep, ...]


@dataclass(frozen=True)
class MigrationExecutionRecord:
    version: str
    name: str
    direction: MigrationDirection
    statement_count: int


class Cursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> object: ...

    def fetchall(self) -> Sequence[Sequence[Any]]: ...

    def __enter__(self) -> Cursor: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object: ...


class MigrationConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> Cursor: ...

    def commit(self) -> object: ...

    def rollback(self) -> object: ...


def discover_migrations(migrations_dir: Path) -> tuple[MigrationStep, ...]:
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Missing migrations directory: {migrations_dir}")

    steps: list[MigrationStep] = []
    for forward_path in sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql")):
        if forward_path.name.endswith(".rollback.sql"):
            continue
        version, name = _parse_migration_identity(forward_path)
        rollback_path = forward_path.with_name(f"{forward_path.stem}.rollback.sql")
        if not rollback_path.exists():
            raise FileNotFoundError(f"Missing rollback migration: {rollback_path}")
        steps.append(
            MigrationStep(
                version=version,
                name=name,
                forward_path=forward_path,
                rollback_path=rollback_path,
            )
        )
    return tuple(steps)


def build_migration_plan(
    migrations_dir: Path,
    direction: MigrationDirection,
) -> MigrationExecutionPlan:
    steps = discover_migrations(migrations_dir)
    if direction is MigrationDirection.ROLLBACK:
        steps = tuple(reversed(steps))
    return MigrationExecutionPlan(direction=direction, steps=steps)


def migration_bundle_sha256(steps: tuple[MigrationStep, ...]) -> str:
    digest = hashlib.sha256()
    for step in steps:
        digest.update(step.content_sha256.encode("ascii"))
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"


def migration_statements(
    step: MigrationStep,
    direction: MigrationDirection,
) -> tuple[str, ...]:
    sql_path = step.forward_path if direction is MigrationDirection.APPLY else step.rollback_path
    return _sql_statements(sql_path.read_text(encoding="utf-8"))


def execute_migration_plan(
    connection: MigrationConnection,
    plan: MigrationExecutionPlan,
) -> tuple[MigrationExecutionRecord, ...]:
    records: list[MigrationExecutionRecord] = []
    try:
        for step in plan.steps:
            statements = migration_statements(step, plan.direction)
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
            records.append(
                MigrationExecutionRecord(
                    version=step.version,
                    name=step.name,
                    direction=plan.direction,
                    statement_count=len(statements),
                )
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return tuple(records)


def execute_tracked_migration_plan(
    connection: MigrationConnection,
    plan: MigrationExecutionPlan,
) -> tuple[MigrationExecutionRecord, ...]:
    """Execute pending local migrations with durable checksum tracking."""
    records: list[MigrationExecutionRecord] = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (LOCAL_MIGRATION_ADVISORY_LOCK_ID,),
            )
            cursor.execute(_CREATE_LOCAL_MIGRATION_HISTORY_SQL)
            cursor.execute(
                """
                SELECT migration_version, migration_name, content_sha256
                FROM lotus_idea_local_schema_migration
                ORDER BY migration_version
                """
            )
            history = tuple(
                (str(row[0]), str(row[1]), str(row[2])) for row in cursor.fetchall()
            )
            ascending_steps = (
                plan.steps
                if plan.direction is MigrationDirection.APPLY
                else tuple(reversed(plan.steps))
            )
            _validate_tracked_history(history, ascending_steps)
            history_versions = {version for version, _, _ in history}
            steps = (
                plan.steps[len(history) :]
                if plan.direction is MigrationDirection.APPLY
                else tuple(step for step in plan.steps if step.version in history_versions)
            )
            for step in steps:
                statements = migration_statements(step, plan.direction)
                for statement in statements:
                    cursor.execute(statement)
                if plan.direction is MigrationDirection.APPLY:
                    cursor.execute(
                        """
                        INSERT INTO lotus_idea_local_schema_migration (
                            migration_version, migration_name, content_sha256
                        ) VALUES (%s, %s, %s)
                        """,
                        (step.version, step.name, step.content_sha256),
                    )
                else:
                    cursor.execute(
                        """
                        DELETE FROM lotus_idea_local_schema_migration
                        WHERE migration_version = %s
                        """,
                        (step.version,),
                    )
                records.append(
                    MigrationExecutionRecord(
                        version=step.version,
                        name=step.name,
                        direction=plan.direction,
                        statement_count=len(statements),
                    )
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return tuple(records)


def dry_run_migration_plan(plan: MigrationExecutionPlan) -> tuple[MigrationExecutionRecord, ...]:
    records: list[MigrationExecutionRecord] = []
    for step in plan.steps:
        statements = migration_statements(step, plan.direction)
        records.append(
            MigrationExecutionRecord(
                version=step.version,
                name=step.name,
                direction=plan.direction,
                statement_count=len(statements),
            )
        )
    return tuple(records)


def _parse_migration_identity(path: Path) -> tuple[str, str]:
    version, _, name = path.stem.partition("_")
    if not version or not name:
        raise ValueError(f"Invalid migration filename: {path.name}")
    return version, name


def _validate_tracked_history(
    history: tuple[tuple[str, str, str], ...],
    steps: tuple[MigrationStep, ...],
) -> None:
    if len(history) > len(steps):
        raise ValueError("local migration history is ahead of the current image")
    for index, actual in enumerate(history):
        expected = steps[index]
        if actual[0] != expected.version:
            raise ValueError("local migration history is not a contiguous image prefix")
        if actual[1:] != (expected.name, expected.content_sha256):
            raise ValueError(f"local migration {actual[0]} content drift detected")


def _sql_statements(sql: str) -> tuple[str, ...]:
    cleaned_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        cleaned_lines.append(line)
    cleaned_sql = "\n".join(cleaned_lines)
    statements = [statement.strip() for statement in cleaned_sql.split(";")]
    return tuple(f"{statement};" for statement in statements if statement)


_CREATE_LOCAL_MIGRATION_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS lotus_idea_local_schema_migration (
    migration_version TEXT PRIMARY KEY,
    migration_name TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    applied_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_lotus_idea_local_schema_migration_version
        CHECK (migration_version ~ '^[0-9]{3}$'),
    CONSTRAINT ck_lotus_idea_local_schema_migration_content_sha256
        CHECK (content_sha256 ~ '^sha256:[0-9a-f]{64}$')
)
"""
