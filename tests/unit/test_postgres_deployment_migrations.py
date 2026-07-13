from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

import pytest

from app.domain.deployment_migrations import (
    DeploymentEnvironmentClass,
    DeploymentMigrationCommand,
    DeploymentMigrationError,
    DeploymentMigrationOperation,
    MigrationReleaseIdentity,
)
from app.infrastructure.migrations import discover_migrations, migration_bundle_sha256
from app.infrastructure.postgres_deployment_migrations import PostgresDeploymentMigrationExecutor
from app.infrastructure.postgres_schema_fingerprint import postgres_idea_schema_fingerprint


class FakeMigrationCursor:
    def __init__(
        self,
        *,
        idea_schema_exists: bool = False,
        server_version_num: str = "180000",
        fail_on: str | None = None,
    ) -> None:
        self.relations = {
            "public.idea_candidate_record": idea_schema_exists,
            "public.lotus_idea_schema_migration": False,
        }
        self.server_version_num = server_version_num
        self.fail_on = fail_on
        self.history: list[tuple[str, str, str]] = []
        self.events: list[tuple[object, ...]] = []
        self.executed: list[tuple[str, Sequence[object] | None]] = []
        self.trigger_exists = False
        self._one: Sequence[Any] | None = None
        self._all: Sequence[Sequence[Any]] = ()

    def execute(
        self,
        query: str,
        params: Sequence[object] | None = None,
    ) -> object:
        if self.fail_on and self.fail_on in query:
            raise RuntimeError("synthetic migration failure")
        self.executed.append((query, params))
        normalized = " ".join(query.split())
        if normalized == "SHOW server_version_num":
            self._one = (self.server_version_num,)
        elif "SELECT to_regclass(%s) IS NOT NULL" in normalized:
            assert params is not None
            self._one = (self.relations[str(params[0])],)
        elif normalized.startswith("CREATE TABLE IF NOT EXISTS lotus_idea_schema_migration ("):
            self.relations["public.lotus_idea_schema_migration"] = True
        elif "FROM pg_trigger" in normalized:
            self._one = (self.trigger_exists,)
        elif normalized.startswith("CREATE TRIGGER trg_lotus_idea_schema_migration_event"):
            self.trigger_exists = True
        elif normalized.startswith("SELECT migration_version, migration_name, content_sha256"):
            self._all = tuple(self.history)
        elif normalized.startswith("INSERT INTO lotus_idea_schema_migration ("):
            assert params is not None
            self.history.append((str(params[0]), str(params[1]), str(params[2])))
        elif normalized.startswith("INSERT INTO lotus_idea_schema_migration_event ("):
            assert params is not None
            self.events.append(tuple(params))
        elif normalized.startswith("DELETE FROM lotus_idea_schema_migration"):
            assert params is not None
            self.history = [row for row in self.history if row[0] != params[0]]
        return None

    def fetchone(self) -> Sequence[Any] | None:
        return self._one

    def fetchall(self) -> Sequence[Sequence[Any]]:
        return self._all

    def __enter__(self) -> FakeMigrationCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeMigrationConnection:
    def __init__(self, cursor: FakeMigrationCursor) -> None:
        self.cursor_value = cursor
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self) -> FakeMigrationCursor:
        return self.cursor_value

    def commit(self) -> object:
        self.commit_count += 1
        return None

    def rollback(self) -> object:
        self.rollback_count += 1
        return None


def test_executor_applies_replays_and_rolls_back_release_history(tmp_path: Path) -> None:
    migrations = _single_migration(tmp_path)
    cursor = FakeMigrationCursor()
    connection = FakeMigrationConnection(cursor)
    executor = _executor(connection, migrations)

    applied = executor.execute(_command(DeploymentMigrationOperation.APPLY, migrations))
    replayed = executor.execute(_command(DeploymentMigrationOperation.APPLY, migrations))
    rolled_back = executor.execute(
        _command(DeploymentMigrationOperation.ROLLBACK, migrations, rollback_count=1)
    )

    assert applied.applied_versions == ("001",)
    assert replayed.applied_versions == ()
    assert rolled_back.rolled_back_versions == ("001",)
    assert rolled_back.previous_version == "001"
    assert rolled_back.current_version is None
    assert cursor.history == []
    assert [event[0] for event in cursor.events] == ["apply", "rollback"]
    assert cursor.events[0][8:11] == ("staging", "CHG-123456", "lotus-release")
    assert connection.commit_count == 3
    assert connection.rollback_count == 0
    assert cursor.trigger_exists is True


def test_executor_requires_explicit_exact_legacy_adoption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migrations = _single_migration(tmp_path)
    cursor = FakeMigrationCursor(idea_schema_exists=True)
    connection = FakeMigrationConnection(cursor)
    executor = _executor(connection, migrations)

    with pytest.raises(DeploymentMigrationError, match="explicit validated adoption"):
        executor.execute(_command(DeploymentMigrationOperation.APPLY, migrations))
    cursor = FakeMigrationCursor(idea_schema_exists=True)
    executor = _executor(FakeMigrationConnection(cursor), migrations)
    monkeypatch.setattr(
        "app.infrastructure.postgres_deployment_migrations.postgres_idea_schema_fingerprint",
        lambda _cursor: f"sha256:{'f' * 64}",
    )
    adopted = executor.execute(
        _command(
            DeploymentMigrationOperation.ADOPT,
            migrations,
            schema_fingerprint=f"sha256:{'f' * 64}",
        )
    )

    assert adopted.adopted_versions == ("001",)
    with pytest.raises(DeploymentMigrationError, match="valid only when Idea tables exist"):
        executor.execute(
            _command(
                DeploymentMigrationOperation.ADOPT,
                migrations,
                schema_fingerprint=f"sha256:{'f' * 64}",
            )
        )


def test_executor_rejects_version_bundle_history_and_rollback_drift(tmp_path: Path) -> None:
    migrations = _single_migration(tmp_path)
    step = discover_migrations(migrations)[0]
    cursor = FakeMigrationCursor(server_version_num="170006")
    executor = _executor(FakeMigrationConnection(cursor), migrations)

    with pytest.raises(DeploymentMigrationError, match="require PostgreSQL 18"):
        executor.execute(_command(DeploymentMigrationOperation.APPLY, migrations))
    with pytest.raises(DeploymentMigrationError, match="governed contract"):
        executor.execute(
            _command(
                DeploymentMigrationOperation.APPLY,
                migrations,
                bundle_sha256=f"sha256:{'0' * 64}",
            )
        )
    with pytest.raises(DeploymentMigrationError, match="ahead of the deployment image"):
        executor._validate_history(
            [("001", "foundation", step.content_sha256), ("002", "extra", "sha256:x")],
            (step,),
        )
    with pytest.raises(DeploymentMigrationError, match="not a strict image prefix"):
        executor._validate_history([("002", "foundation", step.content_sha256)], (step,))
    with pytest.raises(DeploymentMigrationError, match="does not match"):
        executor._validate_history([("001", "changed", step.content_sha256)], (step,))
    with pytest.raises(DeploymentMigrationError, match="exceeds applied migration history"):
        executor._rollback_latest(
            cursor,
            steps=(step,),
            history=[],
            command=_command(
                DeploymentMigrationOperation.ROLLBACK,
                migrations,
                rollback_count=1,
            ),
            bundle_sha256=migration_bundle_sha256((step,)),
        )


def test_executor_rolls_back_failed_plan_and_rejects_adoption_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migrations = _single_migration(tmp_path, forward="SELECT fail_me();")
    cursor = FakeMigrationCursor(fail_on="fail_me")
    connection = FakeMigrationConnection(cursor)
    executor = _executor(connection, migrations)

    with pytest.raises(RuntimeError, match="synthetic migration failure"):
        executor.execute(_command(DeploymentMigrationOperation.APPLY, migrations))
    assert connection.commit_count == 0
    assert connection.rollback_count == 1

    adopt_cursor = FakeMigrationCursor(idea_schema_exists=True)
    adopt_executor = _executor(FakeMigrationConnection(adopt_cursor), migrations)
    monkeypatch.setattr(
        "app.infrastructure.postgres_deployment_migrations.postgres_idea_schema_fingerprint",
        lambda _cursor: f"sha256:{'e' * 64}",
    )
    with pytest.raises(DeploymentMigrationError, match="approved adoption fingerprint"):
        adopt_executor.execute(
            _command(
                DeploymentMigrationOperation.ADOPT,
                migrations,
                schema_fingerprint=f"sha256:{'f' * 64}",
            )
        )


def test_schema_fingerprint_is_ordered_and_whitespace_stable() -> None:
    class InventoryCursor:
        def __init__(self, padded: bool) -> None:
            self.padded = padded
            self.rows: Sequence[Sequence[Any]] = ()
            self.query_count = 0

        def execute(self, query: str, params: Sequence[object] | None = None) -> object:
            self.query_count += 1
            marker = "  text   value  " if self.padded else "text value"
            self.rows = ((self.query_count, marker, None),)
            return None

        def fetchall(self) -> Sequence[Sequence[Any]]:
            return self.rows

    padded = InventoryCursor(padded=True)
    normalized = InventoryCursor(padded=False)

    assert postgres_idea_schema_fingerprint(padded) == postgres_idea_schema_fingerprint(normalized)
    assert padded.query_count == 3


def _single_migration(tmp_path: Path, *, forward: str = "SELECT 1;") -> Path:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_foundation.sql").write_text(forward, encoding="utf-8")
    (migrations / "001_foundation.rollback.sql").write_text("SELECT 2;", encoding="utf-8")
    return migrations


def _executor(
    connection: FakeMigrationConnection,
    migrations: Path,
) -> PostgresDeploymentMigrationExecutor:
    return PostgresDeploymentMigrationExecutor(
        connection,  # type: ignore[arg-type]
        migrations_dir=migrations,
        clock=lambda: datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
    )


def _command(
    operation: DeploymentMigrationOperation,
    migrations: Path,
    *,
    rollback_count: int = 0,
    schema_fingerprint: str | None = None,
    bundle_sha256: str | None = None,
) -> DeploymentMigrationCommand:
    return DeploymentMigrationCommand(
        operation=operation,
        release=MigrationReleaseIdentity(
            repository="sgajbi/lotus-idea",
            git_commit_sha="1" * 40,
            git_ref="refs/heads/main",
            ci_run_id="123456",
            image_digest_reference=f"ghcr.io/sgajbi/lotus-idea@sha256:{'a' * 64}",
            environment_class=DeploymentEnvironmentClass.STAGING,
            change_reference="CHG-123456",
            deployment_actor="lotus-release",
        ),
        expected_migration_bundle_sha256=(
            bundle_sha256 or migration_bundle_sha256(discover_migrations(migrations))
        ),
        rollback_count=rollback_count,
        expected_schema_fingerprint=schema_fingerprint,
    )
