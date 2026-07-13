from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path
from types import ModuleType

from app.application.deployment_migrations import deployment_migration_evidence
from app.application.deployment_migration_contract import load_deployment_migration_contract
from app.domain.deployment_migrations import (
    DeploymentEnvironmentClass,
    DeploymentMigrationOperation,
    DeploymentMigrationResult,
    MigrationReleaseIdentity,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "contracts" / "operations" / "lotus-idea-deployment-migrations.v1.json"


def test_evidence_gate_accepts_source_safe_apply_result() -> None:
    module = _load_gate()
    payload = _evidence()

    assert module.validate_deployment_migration_evidence(payload) == []


def test_evidence_gate_rejects_digest_substitution_and_sensitive_fields() -> None:
    module = _load_gate()
    payload = _evidence()
    payload["imageDigestReference"] = "ghcr.io/sgajbi/lotus-idea:latest"
    payload["databaseUrl"] = "postgresql://secret"

    errors = module.validate_deployment_migration_evidence(payload)

    assert any(error.startswith("release identity invalid") for error in errors)
    assert "evidence contains ungoverned keys: databaseUrl" in errors
    assert "$.databaseUrl is a forbidden evidence field" in errors


def test_evidence_gate_rejects_optimistic_certification_and_mixed_operation() -> None:
    module = _load_gate()
    payload = _evidence()
    payload["productionCertified"] = True
    payload["rolledBackVersions"] = ["015"]

    errors = module.validate_deployment_migration_evidence(payload)

    assert "productionCertified must be false" in errors
    assert "apply evidence cannot contain rollback or adoption versions" in errors


def test_evidence_gate_rejects_contract_and_transition_drift() -> None:
    module = _load_gate()
    payload = _evidence()
    payload["migrationContractVersion"] = "lotus-idea.deployment-migrations.v2"
    payload["appliedVersions"] = ["013", "015"]
    payload["previousVersion"] = "011"

    errors = module.validate_deployment_migration_evidence(payload)

    assert "migrationContractVersion must match the governed migration contract" in errors
    assert "apply evidence versions must be a contiguous ascending range" in errors
    assert "apply evidence version transition is inconsistent" in errors


def _evidence() -> dict[str, object]:
    contract = load_deployment_migration_contract(CONTRACT_PATH)
    return deployment_migration_evidence(
        DeploymentMigrationResult(
            operation=DeploymentMigrationOperation.APPLY,
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
            migration_bundle_sha256=contract.migration_bundle_sha256,
            previous_version="014",
            current_version="015",
            applied_versions=("015",),
            rolled_back_versions=(),
            adopted_versions=(),
            executed_at_utc=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        )
    )


def _load_gate() -> ModuleType:
    script = ROOT / "scripts" / "deployment_migration_evidence_gate.py"
    spec = importlib.util.spec_from_file_location("deployment_migration_evidence_gate", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
