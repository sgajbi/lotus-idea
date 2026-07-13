from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import cast

import psycopg
import pytest

from app.domain.deployment_migrations import (
    DeploymentEnvironmentClass,
    DeploymentMigrationCommand,
    DeploymentMigrationError,
    DeploymentMigrationOperation,
    MigrationReleaseIdentity,
)
from app.infrastructure.postgres_deployment_migrations import (
    DeploymentMigrationConnection,
    PostgresDeploymentMigrationExecutor,
)
from app.infrastructure.postgres_schema_fingerprint import postgres_idea_schema_fingerprint
from app.infrastructure.migrations import (
    MigrationDirection,
    discover_migrations,
    migration_bundle_sha256,
)
from scripts.deployment_migration_evidence_gate import (
    validate_deployment_migration_evidence,
)
from tests.integration.postgres_runtime_support import execute_migrations


ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = ROOT / "migrations"
MIGRATION_BUNDLE_SHA256 = migration_bundle_sha256(discover_migrations(MIGRATIONS_DIR))


def test_existing_schema_requires_validated_adoption_and_rejects_drift(
    postgres_database_url: str,
) -> None:
    _drop_deployment_history(postgres_database_url)
    with psycopg.connect(postgres_database_url) as connection:
        executor = _executor(connection)
        with pytest.raises(
            DeploymentMigrationError,
            match="existing Idea schema requires explicit validated adoption",
        ):
            executor.execute(_command(DeploymentMigrationOperation.APPLY))
        with connection.cursor() as cursor:
            expected_fingerprint = postgres_idea_schema_fingerprint(cursor)
            cursor.execute("ALTER TABLE idea_candidate_record ADD COLUMN adoption_drift TEXT")
        connection.commit()
        with pytest.raises(
            DeploymentMigrationError,
            match="does not match the approved adoption fingerprint",
        ):
            executor.execute(
                _command(
                    DeploymentMigrationOperation.ADOPT,
                    expected_schema_fingerprint=expected_fingerprint,
                )
            )
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE idea_candidate_record DROP COLUMN adoption_drift")
        connection.commit()
        adoption = executor.execute(
            _command(
                DeploymentMigrationOperation.ADOPT,
                expected_schema_fingerprint=expected_fingerprint,
            )
        )
        replay = executor.execute(_command(DeploymentMigrationOperation.APPLY, run_id="123457"))

    assert adoption.adopted_versions == tuple(f"{index:03d}" for index in range(1, 16))
    assert replay.applied_versions == ()
    assert replay.current_version == "015"


def test_fresh_apply_is_atomic_and_rollback_reapply_updates_history(
    postgres_database_url: str,
) -> None:
    _prepare_empty_database(postgres_database_url)
    with psycopg.connect(postgres_database_url) as connection:
        executor = _executor(connection)
        applied = executor.execute(_command(DeploymentMigrationOperation.APPLY))
        rolled_back = executor.execute(
            _command(DeploymentMigrationOperation.ROLLBACK, rollback_count=1, run_id="123457")
        )
        reapplied = executor.execute(_command(DeploymentMigrationOperation.APPLY, run_id="123458"))
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT operation, migration_version FROM lotus_idea_schema_migration_event "
                "WHERE migration_version = '015' ORDER BY migration_event_id"
            )
            events = cursor.fetchall()

    assert applied.applied_versions == tuple(f"{index:03d}" for index in range(1, 16))
    assert rolled_back.rolled_back_versions == ("015",)
    assert rolled_back.current_version == "014"
    assert reapplied.applied_versions == ("015",)
    assert [tuple(row) for row in events] == [
        ("apply", "015"),
        ("rollback", "015"),
        ("apply", "015"),
    ]


def test_failed_fresh_plan_rolls_back_schema_and_history(
    postgres_database_url: str,
    tmp_path: Path,
) -> None:
    _prepare_empty_database(postgres_database_url)
    altered_migrations = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, altered_migrations)
    migration = altered_migrations / "015_archive_lifecycle_receipt.sql"
    migration.write_text(
        f"{migration.read_text(encoding='utf-8')}\nSELECT missing_deployment_function();\n",
        encoding="utf-8",
    )
    with psycopg.connect(postgres_database_url) as connection:
        executor = PostgresDeploymentMigrationExecutor(
            cast(DeploymentMigrationConnection, connection),
            migrations_dir=altered_migrations,
        )
        with pytest.raises(psycopg.errors.UndefinedFunction):
            executor.execute(
                _command(
                    DeploymentMigrationOperation.APPLY,
                    expected_migration_bundle_sha256=migration_bundle_sha256(
                        discover_migrations(altered_migrations)
                    ),
                )
            )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_regclass('public.idea_candidate_record'), "
                "to_regclass('public.lotus_idea_schema_migration'), "
                "to_regprocedure('public.lotus_idea_reject_schema_migration_event_mutation()')"
            )
            row = cursor.fetchone()

    assert row == (None, None, None)


def test_concurrent_fresh_deploys_are_serialized(postgres_database_url: str) -> None:
    _prepare_empty_database(postgres_database_url)

    def execute(run_id: str) -> tuple[str, ...]:
        with psycopg.connect(postgres_database_url) as connection:
            return (
                _executor(connection)
                .execute(_command(DeploymentMigrationOperation.APPLY, run_id=run_id))
                .applied_versions
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(execute, ("123456", "123457")))

    assert sorted(len(outcome) for outcome in outcomes) == [0, 15]
    with psycopg.connect(postgres_database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM lotus_idea_schema_migration")
            assert cursor.fetchone() == (15,)
            cursor.execute(
                "SELECT count(*) FROM lotus_idea_schema_migration_event WHERE operation = 'apply'"
            )
            assert cursor.fetchone() == (15,)


def test_applied_content_drift_fails_before_schema_mutation(
    postgres_database_url: str,
    tmp_path: Path,
) -> None:
    _prepare_empty_database(postgres_database_url)
    with psycopg.connect(postgres_database_url) as connection:
        _executor(connection).execute(_command(DeploymentMigrationOperation.APPLY))
    altered_migrations = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, altered_migrations)
    rollback = altered_migrations / "001_idea_repository_foundation.rollback.sql"
    rollback.write_text(
        f"{rollback.read_text(encoding='utf-8')}\n-- changed history\n",
        encoding="utf-8",
    )
    with psycopg.connect(postgres_database_url) as connection:
        executor = PostgresDeploymentMigrationExecutor(
            cast(DeploymentMigrationConnection, connection),
            migrations_dir=altered_migrations,
        )
        with pytest.raises(DeploymentMigrationError, match="immutable image bundle"):
            executor.execute(
                _command(
                    DeploymentMigrationOperation.APPLY,
                    run_id="123457",
                    expected_migration_bundle_sha256=migration_bundle_sha256(
                        discover_migrations(altered_migrations)
                    ),
                )
            )
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM lotus_idea_schema_migration_event")
            assert cursor.fetchone() == (15,)


def test_exact_cli_persists_release_lineage_and_emits_validated_evidence(
    postgres_database_url: str,
    tmp_path: Path,
) -> None:
    _prepare_empty_database(postgres_database_url)
    evidence_path = tmp_path / "deployment-migration-evidence.json"
    env = {
        **os.environ,
        "LOTUS_IDEA_DATABASE_URL": postgres_database_url,
        "GITHUB_REPOSITORY": "sgajbi/lotus-idea",
        "GITHUB_SHA": "1" * 40,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ID": "123456",
        "GITHUB_ACTOR": "lotus-release",
        "LOTUS_RELEASE_IMAGE_DIGEST_REFERENCE": (f"ghcr.io/sgajbi/lotus-idea@sha256:{'a' * 64}"),
        "LOTUS_DEPLOYMENT_CHANGE_REFERENCE": "CHG-123456",
    }

    completed = subprocess.run(
        (
            sys.executable,
            "scripts/run_deployment_migrations.py",
            "--operation",
            "apply",
            "--environment-class",
            "staging",
            "--evidence-output",
            str(evidence_path),
        ),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert validate_deployment_migration_evidence(payload) == []
    with psycopg.connect(postgres_database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT environment_class, change_reference, deployment_actor, "
                "count(*) FROM lotus_idea_schema_migration "
                "GROUP BY environment_class, change_reference, deployment_actor"
            )
            assert cursor.fetchone() == ("staging", "CHG-123456", "lotus-release", 15)


@pytest.mark.parametrize("statement", ["UPDATE", "DELETE"])
def test_migration_event_history_rejects_mutation(
    postgres_database_url: str,
    statement: str,
) -> None:
    _prepare_empty_database(postgres_database_url)
    with psycopg.connect(postgres_database_url) as connection:
        _executor(connection).execute(_command(DeploymentMigrationOperation.APPLY))
        with connection.cursor() as cursor:
            query = (
                "UPDATE lotus_idea_schema_migration_event SET migration_name = 'changed' "
                "WHERE migration_event_id = 1"
                if statement == "UPDATE"
                else "DELETE FROM lotus_idea_schema_migration_event WHERE migration_event_id = 1"
            )
            with pytest.raises(
                psycopg.errors.ObjectNotInPrerequisiteState,
                match="append-only",
            ):
                cursor.execute(query)


def _executor(connection: psycopg.Connection[object]) -> PostgresDeploymentMigrationExecutor:
    return PostgresDeploymentMigrationExecutor(
        cast(DeploymentMigrationConnection, connection),
        migrations_dir=MIGRATIONS_DIR,
    )


def _command(
    operation: DeploymentMigrationOperation,
    *,
    run_id: str = "123456",
    rollback_count: int = 0,
    expected_schema_fingerprint: str | None = None,
    expected_migration_bundle_sha256: str = MIGRATION_BUNDLE_SHA256,
) -> DeploymentMigrationCommand:
    return DeploymentMigrationCommand(
        operation=operation,
        release=MigrationReleaseIdentity(
            repository="sgajbi/lotus-idea",
            git_commit_sha="1" * 40,
            git_ref="refs/heads/main",
            ci_run_id=run_id,
            image_digest_reference=f"ghcr.io/sgajbi/lotus-idea@sha256:{'a' * 64}",
            environment_class=DeploymentEnvironmentClass.STAGING,
            change_reference="CHG-123456",
            deployment_actor="lotus-release",
        ),
        expected_migration_bundle_sha256=expected_migration_bundle_sha256,
        rollback_count=rollback_count,
        expected_schema_fingerprint=expected_schema_fingerprint,
    )


def _prepare_empty_database(database_url: str) -> None:
    _drop_deployment_history(database_url)
    execute_migrations(database_url, MigrationDirection.ROLLBACK)


def _drop_deployment_history(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS lotus_idea_schema_migration_event")
            cursor.execute("DROP TABLE IF EXISTS lotus_idea_schema_migration")
            cursor.execute(
                "DROP FUNCTION IF EXISTS lotus_idea_reject_schema_migration_event_mutation()"
            )
