from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Protocol, Sequence

from app.domain.deployment_migrations import (
    MIGRATION_HISTORY_SCHEMA_VERSION,
    SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR,
    DeploymentMigrationCommand,
    DeploymentMigrationError,
    DeploymentMigrationOperation,
    DeploymentMigrationResult,
)
from app.infrastructure.migrations import (
    MigrationDirection,
    MigrationStep,
    discover_migrations,
    migration_bundle_sha256,
    migration_statements,
)
from app.infrastructure.postgres_schema_fingerprint import postgres_idea_schema_fingerprint


DEPLOYMENT_MIGRATION_ADVISORY_LOCK_ID = 4_684_603_740_237_098_264


class DeploymentMigrationCursor(Protocol):
    def execute(self, query: str, params: Sequence[object] | None = None) -> object: ...

    def fetchone(self) -> Sequence[Any] | None: ...

    def fetchall(self) -> Sequence[Sequence[Any]]: ...

    def __enter__(self) -> DeploymentMigrationCursor: ...

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> object: ...


class DeploymentMigrationConnection(Protocol):
    def cursor(self) -> DeploymentMigrationCursor: ...

    def commit(self) -> object: ...

    def rollback(self) -> object: ...


class PostgresDeploymentMigrationExecutor:
    def __init__(
        self,
        connection: DeploymentMigrationConnection,
        *,
        migrations_dir: Any,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._connection = connection
        self._migrations_dir = migrations_dir
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(self, command: DeploymentMigrationCommand) -> DeploymentMigrationResult:
        steps = discover_migrations(self._migrations_dir)
        bundle_sha256 = migration_bundle_sha256(steps)
        if bundle_sha256 != command.expected_migration_bundle_sha256:
            raise DeploymentMigrationError(
                "migration_bundle_contract_mismatch",
                "immutable image migration bundle does not match the governed contract",
            )
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(%s)",
                    (DEPLOYMENT_MIGRATION_ADVISORY_LOCK_ID,),
                )
                self._validate_postgres_version(cursor)
                history_exists = self._relation_exists(cursor, "lotus_idea_schema_migration")
                idea_schema_exists = self._relation_exists(cursor, "idea_candidate_record")
                cursor.execute(_CREATE_MIGRATION_HISTORY_SQL)
                cursor.execute(_CREATE_MIGRATION_EVENT_SQL)
                self._ensure_event_append_only(cursor)
                history = self._load_history(cursor)
                self._validate_history(history, steps)
                previous_version = history[-1][0] if history else None

                if not history and idea_schema_exists:
                    if command.operation is not DeploymentMigrationOperation.ADOPT:
                        raise DeploymentMigrationError(
                            "migration_history_missing_for_existing_schema",
                            "existing Idea schema requires explicit validated adoption",
                        )
                elif command.operation is DeploymentMigrationOperation.ADOPT:
                    raise DeploymentMigrationError(
                        "migration_adoption_not_required",
                        "schema adoption is valid only when Idea tables exist without history",
                    )

                applied_versions: tuple[str, ...] = ()
                rolled_back_versions: tuple[str, ...] = ()
                adopted_versions: tuple[str, ...] = ()
                if command.operation is DeploymentMigrationOperation.APPLY:
                    applied_versions = self._apply_pending(
                        cursor,
                        steps=steps,
                        applied_count=len(history),
                        command=command,
                        bundle_sha256=bundle_sha256,
                    )
                elif command.operation is DeploymentMigrationOperation.ROLLBACK:
                    rolled_back_versions = self._rollback_latest(
                        cursor,
                        steps=steps,
                        history=history,
                        command=command,
                        bundle_sha256=bundle_sha256,
                    )
                else:
                    adopted_versions = self._adopt_existing_schema(
                        cursor,
                        steps=steps,
                        command=command,
                        bundle_sha256=bundle_sha256,
                        history_existed=history_exists,
                    )

                current_history = self._load_history(cursor)
                current_version = current_history[-1][0] if current_history else None
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

        return DeploymentMigrationResult(
            operation=command.operation,
            release=command.release,
            migration_bundle_sha256=bundle_sha256,
            previous_version=previous_version,
            current_version=current_version,
            applied_versions=applied_versions,
            rolled_back_versions=rolled_back_versions,
            adopted_versions=adopted_versions,
            executed_at_utc=self._clock(),
        )

    @staticmethod
    def _validate_postgres_version(cursor: DeploymentMigrationCursor) -> None:
        cursor.execute("SHOW server_version_num")
        row = cursor.fetchone()
        major = int(str(row[0])) // 10_000 if row else 0
        if major != SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR:
            raise DeploymentMigrationError(
                "deployment_postgres_version_unsupported",
                f"deployment migrations require PostgreSQL {SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR}",
            )

    @staticmethod
    def _relation_exists(cursor: DeploymentMigrationCursor, relation_name: str) -> bool:
        cursor.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{relation_name}",))
        row = cursor.fetchone()
        return bool(row and row[0])

    @staticmethod
    def _ensure_event_append_only(cursor: DeploymentMigrationCursor) -> None:
        cursor.execute(_CREATE_EVENT_MUTATION_GUARD_FUNCTION_SQL)
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_trigger
                WHERE tgname = 'trg_lotus_idea_schema_migration_event_append_only'
                  AND tgrelid = 'public.lotus_idea_schema_migration_event'::regclass
                  AND NOT tgisinternal
            )
            """
        )
        row = cursor.fetchone()
        if not row or row[0] is not True:
            cursor.execute(_CREATE_EVENT_MUTATION_GUARD_TRIGGER_SQL)

    @staticmethod
    def _load_history(
        cursor: DeploymentMigrationCursor,
    ) -> list[tuple[str, str, str]]:
        cursor.execute(
            """
            SELECT migration_version, migration_name, content_sha256
            FROM lotus_idea_schema_migration
            ORDER BY migration_version
            """
        )
        return [(str(row[0]), str(row[1]), str(row[2])) for row in cursor.fetchall()]

    @staticmethod
    def _validate_history(
        history: list[tuple[str, str, str]],
        steps: tuple[MigrationStep, ...],
    ) -> None:
        if len(history) > len(steps):
            raise DeploymentMigrationError(
                "migration_history_ahead_of_image",
                "database migration history is ahead of the deployment image",
            )
        for index, (version, name, content_sha256) in enumerate(history):
            expected = steps[index]
            if version != expected.version:
                raise DeploymentMigrationError(
                    "migration_history_not_contiguous",
                    "database migration history is not a strict image prefix",
                )
            if name != expected.name or content_sha256 != expected.content_sha256:
                raise DeploymentMigrationError(
                    "migration_content_drift",
                    f"applied migration {version} does not match the immutable image bundle",
                )

    def _apply_pending(
        self,
        cursor: DeploymentMigrationCursor,
        *,
        steps: tuple[MigrationStep, ...],
        applied_count: int,
        command: DeploymentMigrationCommand,
        bundle_sha256: str,
    ) -> tuple[str, ...]:
        pending_steps = steps[applied_count:]
        for step in pending_steps:
            for statement in migration_statements(step, MigrationDirection.APPLY):
                cursor.execute(statement)
            self._insert_history(cursor, step, command, bundle_sha256, adopted=False)
            self._insert_event(cursor, step, command, bundle_sha256)
        return tuple(step.version for step in pending_steps)

    def _rollback_latest(
        self,
        cursor: DeploymentMigrationCursor,
        *,
        steps: tuple[MigrationStep, ...],
        history: list[tuple[str, str, str]],
        command: DeploymentMigrationCommand,
        bundle_sha256: str,
    ) -> tuple[str, ...]:
        if command.rollback_count > len(history):
            raise DeploymentMigrationError(
                "migration_rollback_exceeds_history",
                "rollback_count exceeds applied migration history",
            )
        rollback_steps = tuple(reversed(steps[: len(history)]))[: command.rollback_count]
        for step in rollback_steps:
            for statement in migration_statements(step, MigrationDirection.ROLLBACK):
                cursor.execute(statement)
            self._insert_event(cursor, step, command, bundle_sha256)
            cursor.execute(
                "DELETE FROM lotus_idea_schema_migration WHERE migration_version = %s",
                (step.version,),
            )
        return tuple(step.version for step in rollback_steps)

    def _adopt_existing_schema(
        self,
        cursor: DeploymentMigrationCursor,
        *,
        steps: tuple[MigrationStep, ...],
        command: DeploymentMigrationCommand,
        bundle_sha256: str,
        history_existed: bool,
    ) -> tuple[str, ...]:
        if history_existed:
            raise DeploymentMigrationError(
                "migration_adoption_history_already_exists",
                "schema adoption cannot replace existing migration history",
            )
        actual_fingerprint = postgres_idea_schema_fingerprint(cursor)
        if actual_fingerprint != command.expected_schema_fingerprint:
            raise DeploymentMigrationError(
                "migration_adoption_schema_mismatch",
                "existing Idea schema does not match the approved adoption fingerprint",
            )
        for step in steps:
            self._insert_history(cursor, step, command, bundle_sha256, adopted=True)
            self._insert_event(cursor, step, command, bundle_sha256)
        return tuple(step.version for step in steps)

    @staticmethod
    def _insert_history(
        cursor: DeploymentMigrationCursor,
        step: MigrationStep,
        command: DeploymentMigrationCommand,
        bundle_sha256: str,
        *,
        adopted: bool,
    ) -> None:
        cursor.execute(
            _INSERT_MIGRATION_HISTORY_SQL,
            (
                step.version,
                step.name,
                step.content_sha256,
                MIGRATION_HISTORY_SCHEMA_VERSION,
                command.release.git_commit_sha,
                command.release.git_ref,
                command.release.ci_run_id,
                command.release.image_digest_reference,
                command.release.environment_class.value,
                command.release.change_reference,
                command.release.deployment_actor,
                bundle_sha256,
                adopted,
            ),
        )

    @staticmethod
    def _insert_event(
        cursor: DeploymentMigrationCursor,
        step: MigrationStep,
        command: DeploymentMigrationCommand,
        bundle_sha256: str,
    ) -> None:
        cursor.execute(
            _INSERT_MIGRATION_EVENT_SQL,
            (
                command.operation.value,
                step.version,
                step.name,
                step.content_sha256,
                command.release.git_commit_sha,
                command.release.git_ref,
                command.release.ci_run_id,
                command.release.image_digest_reference,
                command.release.environment_class.value,
                command.release.change_reference,
                command.release.deployment_actor,
                bundle_sha256,
            ),
        )


_CREATE_MIGRATION_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS lotus_idea_schema_migration (
    migration_version TEXT PRIMARY KEY,
    migration_name TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    history_schema_version TEXT NOT NULL,
    applied_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    git_commit_sha TEXT NOT NULL,
    git_ref TEXT NOT NULL,
    ci_run_id TEXT NOT NULL,
    image_digest_reference TEXT NOT NULL,
    environment_class TEXT NOT NULL CHECK (environment_class IN ('staging', 'production')),
    change_reference TEXT NOT NULL,
    deployment_actor TEXT NOT NULL,
    migration_bundle_sha256 TEXT NOT NULL,
    adopted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT ck_lotus_idea_schema_migration_version
        CHECK (migration_version ~ '^[0-9]{3}$'),
    CONSTRAINT ck_lotus_idea_schema_migration_content_sha256
        CHECK (content_sha256 ~ '^sha256:[0-9a-f]{64}$')
)
"""

_CREATE_MIGRATION_EVENT_SQL = """
CREATE TABLE IF NOT EXISTS lotus_idea_schema_migration_event (
    migration_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation TEXT NOT NULL CHECK (operation IN ('apply', 'rollback', 'adopt')),
    migration_version TEXT NOT NULL,
    migration_name TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    occurred_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    git_commit_sha TEXT NOT NULL,
    git_ref TEXT NOT NULL,
    ci_run_id TEXT NOT NULL,
    image_digest_reference TEXT NOT NULL,
    environment_class TEXT NOT NULL CHECK (environment_class IN ('staging', 'production')),
    change_reference TEXT NOT NULL,
    deployment_actor TEXT NOT NULL,
    migration_bundle_sha256 TEXT NOT NULL
)
"""

_CREATE_EVENT_MUTATION_GUARD_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION lotus_idea_reject_schema_migration_event_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'lotus_idea_schema_migration_event is append-only'
        USING ERRCODE = '55000';
END;
$$
"""

_CREATE_EVENT_MUTATION_GUARD_TRIGGER_SQL = """
CREATE TRIGGER trg_lotus_idea_schema_migration_event_append_only
BEFORE UPDATE OR DELETE ON lotus_idea_schema_migration_event
FOR EACH ROW
EXECUTE FUNCTION lotus_idea_reject_schema_migration_event_mutation()
"""

_INSERT_MIGRATION_HISTORY_SQL = """
INSERT INTO lotus_idea_schema_migration (
    migration_version,
    migration_name,
    content_sha256,
    history_schema_version,
    git_commit_sha,
    git_ref,
    ci_run_id,
    image_digest_reference,
    environment_class,
    change_reference,
    deployment_actor,
    migration_bundle_sha256,
    adopted
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_INSERT_MIGRATION_EVENT_SQL = """
INSERT INTO lotus_idea_schema_migration_event (
    operation,
    migration_version,
    migration_name,
    content_sha256,
    git_commit_sha,
    git_ref,
    ci_run_id,
    image_digest_reference,
    environment_class,
    change_reference,
    deployment_actor,
    migration_bundle_sha256
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
