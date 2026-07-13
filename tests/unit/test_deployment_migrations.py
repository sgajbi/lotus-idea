from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.deployment_migrations import deployment_migration_evidence
from app.domain.deployment_migrations import (
    MIGRATION_EVIDENCE_SCHEMA_VERSION,
    DeploymentEnvironmentClass,
    DeploymentMigrationCommand,
    DeploymentMigrationOperation,
    DeploymentMigrationResult,
    MigrationReleaseIdentity,
)
from app.infrastructure.migrations import discover_migrations, migration_bundle_sha256


ROOT = Path(__file__).resolve().parents[2]


def test_release_identity_requires_exact_main_and_immutable_idea_digest() -> None:
    identity = _release_identity()

    assert identity.git_ref == "refs/heads/main"

    with pytest.raises(ValueError, match="git_ref must be refs/heads/main"):
        _release_identity(git_ref="refs/heads/feature")
    with pytest.raises(ValueError, match="immutable Lotus Idea GHCR digest"):
        _release_identity(image_digest_reference="ghcr.io/sgajbi/lotus-idea:latest")


def test_rollback_and_adoption_inputs_are_explicit_and_bounded() -> None:
    release = _release_identity()

    with pytest.raises(ValueError, match="rollback_count must be between 1 and 15"):
        DeploymentMigrationCommand(
            operation=DeploymentMigrationOperation.ROLLBACK,
            release=release,
        )
    with pytest.raises(ValueError, match="expected_schema_fingerprint is required"):
        DeploymentMigrationCommand(
            operation=DeploymentMigrationOperation.ADOPT,
            release=release,
        )


def test_migration_bundle_hash_binds_forward_and_rollback_content(tmp_path: Path) -> None:
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    forward = migrations_dir / "001_foundation.sql"
    rollback = migrations_dir / "001_foundation.rollback.sql"
    forward.write_text("CREATE TABLE idea_record(id text);", encoding="utf-8")
    rollback.write_text("DROP TABLE idea_record;", encoding="utf-8")
    original = migration_bundle_sha256(discover_migrations(migrations_dir))

    rollback.write_text("DROP TABLE IF EXISTS idea_record;", encoding="utf-8")

    assert migration_bundle_sha256(discover_migrations(migrations_dir)) != original


def test_deployment_evidence_is_release_bound_and_source_safe() -> None:
    result = DeploymentMigrationResult(
        operation=DeploymentMigrationOperation.APPLY,
        release=_release_identity(),
        migration_bundle_sha256=f"sha256:{'b' * 64}",
        previous_version="014",
        current_version="015",
        applied_versions=("015",),
        rolled_back_versions=(),
        adopted_versions=(),
        executed_at_utc=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
    )

    evidence = deployment_migration_evidence(result)

    assert evidence["schemaVersion"] == MIGRATION_EVIDENCE_SCHEMA_VERSION
    assert evidence["imageDigestReference"] == result.release.image_digest_reference
    assert evidence["appliedVersions"] == ["015"]
    assert evidence["productionCertified"] is False
    rendered = str(evidence).lower()
    assert "database_url" not in rendered
    assert "password" not in rendered
    assert "hostname" not in rendered


def _release_identity(
    *,
    git_ref: str = "refs/heads/main",
    image_digest_reference: str = f"ghcr.io/sgajbi/lotus-idea@sha256:{'a' * 64}",
    run_id: str = "123456",
) -> MigrationReleaseIdentity:
    return MigrationReleaseIdentity(
        repository="sgajbi/lotus-idea",
        git_commit_sha="1" * 40,
        git_ref=git_ref,
        ci_run_id=run_id,
        image_digest_reference=image_digest_reference,
        environment_class=DeploymentEnvironmentClass.STAGING,
    )
