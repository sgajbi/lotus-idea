# ruff: noqa: E402
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.deployment_migration_contract import (
    load_deployment_migration_contract,
)
from app.domain.deployment_migrations import (
    DEPLOYMENT_MIGRATION_CONTRACT_VERSION,
    MIGRATION_EVIDENCE_SCHEMA_VERSION,
    MIGRATION_HISTORY_SCHEMA_VERSION,
    SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR,
)
from app.infrastructure.migrations import discover_migrations, migration_bundle_sha256


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = Path("contracts/operations/lotus-idea-deployment-migrations.v1.json")
WORKFLOW_RELATIVE_PATH = Path(".github/workflows/deployment-migration-evidence.yml")

_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_BLOCKERS = (
    "protected_environment_execution_attestation_missing",
    "deployment_rollout_health_proof_missing",
    "production_change_approval_missing",
)
_REQUIRED_WORKFLOW_FRAGMENTS = (
    "permissions:\n  contents: read\n  packages: read\n  attestations: write\n  id-token: write",
    "group: lotus-idea-deployment-migrations-${{ inputs.environment_class }}",
    "cancel-in-progress: false",
    "runs-on: ubuntu-latest",
    "environment: lotus-idea-${{ inputs.environment_class }}",
    "LOTUS_IDEA_DATABASE_URL: ${{ secrets.LOTUS_IDEA_DATABASE_URL }}",
    'gh attestation verify "oci://${IMAGE_DIGEST_REFERENCE}" -R "$GITHUB_REPOSITORY"',
    'cosign verify "$IMAGE_DIGEST_REFERENCE"',
    "main-releasability.yml@refs/heads/main",
    'docker pull "$IMAGE_DIGEST_REFERENCE"',
    "python scripts/run_deployment_migrations.py",
    "python scripts/deployment_migration_evidence_gate.py",
    "actions/attest-build-provenance@0f67c3f4856b2e3261c31976d6725780e5e4c373",
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "retention-days: 90",
)
_PROHIBITED_WORKFLOW_FRAGMENTS = (
    "continue-on-error:",
    "docker build ",
    "docker buildx build ",
    "docker push ",
    ":latest",
    "LOTUS_IDEA_DATABASE_URL: ${{ inputs.",
    "self-hosted",
    "lotus-deployment",
)


def validate_deployment_migration_contract(
    root: Path = ROOT,
    *,
    contract_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    resolved_contract_path = contract_path or root / CONTRACT_RELATIVE_PATH
    try:
        payload = json.loads(resolved_contract_path.read_text(encoding="utf-8"))
        contract = load_deployment_migration_contract(resolved_contract_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"deployment migration contract unreadable: {exc}"]
    if not isinstance(payload, Mapping):
        return ["deployment migration contract must be an object"]

    migrations = discover_migrations(root / "migrations")
    expected_bundle = migration_bundle_sha256(migrations)
    if contract.migration_bundle_sha256 != expected_bundle:
        errors.append("migrationBundleSha256 does not match the repository migration bundle")
    if contract.migration_count != len(migrations):
        errors.append("migrationCount does not match the repository migration count")
    current_version = migrations[-1].version if migrations else ""
    if contract.current_migration_version != current_version:
        errors.append("currentMigrationVersion does not match the latest repository migration")
    if contract.schema_version != DEPLOYMENT_MIGRATION_CONTRACT_VERSION:
        errors.append("schemaVersion does not match the code-owned contract version")
    if contract.evidence_schema_version != MIGRATION_EVIDENCE_SCHEMA_VERSION:
        errors.append("evidenceSchemaVersion does not match the code-owned evidence version")
    if contract.postgres_major_version != SUPPORTED_DEPLOYMENT_POSTGRES_MAJOR:
        errors.append("postgresMajorVersion does not match the code-owned PostgreSQL version")
    if contract.remaining_certification_blockers != _REQUIRED_BLOCKERS:
        errors.append("remainingBlockers must preserve truthful deployment certification posture")

    _validate_fixed_contract_fields(payload, errors)
    _validate_source_paths(root, payload.get("sourceOfTruth"), errors)
    _validate_source_contracts(root, errors)
    workflow_path = root / WORKFLOW_RELATIVE_PATH
    if not workflow_path.exists():
        errors.append(f"missing deployment workflow: {WORKFLOW_RELATIVE_PATH.as_posix()}")
    else:
        errors.extend(validate_deployment_migration_workflow(workflow_path.read_text("utf-8")))
    workflow_sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in (root / ".github" / "workflows").glob("*.yml")
    }
    errors.extend(validate_production_migration_entrypoints(workflow_sources))
    return errors


def _validate_fixed_contract_fields(payload: Mapping[str, Any], errors: list[str]) -> None:
    expected = {
        "repository": "sgajbi/lotus-idea",
        "owner": "lotus-idea",
        "databaseBoundary": "one_lotus_idea_owned_postgresql_database",
        "runtimeTopology": "existing_api_and_optional_worker_roles_only",
        "migrationHistorySchemaVersion": MIGRATION_HISTORY_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} must be {value}")

    adoption = payload.get("legacyAdoption")
    if not isinstance(adoption, Mapping):
        errors.append("legacyAdoption must be an object")
    else:
        fingerprint = adoption.get("schemaFingerprintSha256")
        if not isinstance(fingerprint, str) or not _SHA256_PATTERN.fullmatch(fingerprint):
            errors.append("legacyAdoption schemaFingerprintSha256 must be a SHA-256 digest")
        expected_adoption = {
            "allowedOnlyWhenHistoryIsAbsent": True,
            "schemaFingerprintAlgorithm": "postgresql-structural-inventory-v1",
            "silentAdoptionAllowed": False,
        }
        for key, value in expected_adoption.items():
            if adoption.get(key) != value:
                errors.append(f"legacyAdoption {key} must be {value}")
        for key in ("ideaTableCount", "columnCount", "constraintCount", "indexCount"):
            value = adoption.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"legacyAdoption {key} must be a positive integer")

    execution = payload.get("executionPolicy")
    expected_execution = {
        "requiredGitRef": "refs/heads/main",
        "requiredImageRepository": "ghcr.io/sgajbi/lotus-idea",
        "immutableDigestRequired": True,
        "advisoryTransactionLockRequired": True,
        "pendingOnlyApplyRequired": True,
        "contentDriftFailsClosed": True,
        "atomicPlanRequired": True,
        "serviceStartupSchemaMutationAllowed": False,
        "databaseUrlCliArgumentAllowed": False,
        "databaseCredentialsInEvidenceAllowed": False,
        "rollbackIsDatabaseRestore": False,
    }
    if not isinstance(execution, Mapping):
        errors.append("executionPolicy must be an object")
    else:
        for key, value in expected_execution.items():
            if execution.get(key) != value:
                errors.append(f"executionPolicy {key} must be {value}")

    certification = payload.get("certificationPosture")
    if not isinstance(certification, Mapping):
        errors.append("certificationPosture must be an object")
    else:
        if certification.get("productionCertified") is not False:
            errors.append("certificationPosture productionCertified must be false")
        if certification.get("supportedFeaturePromoted") is not False:
            errors.append("certificationPosture supportedFeaturePromoted must be false")


def _validate_source_paths(
    root: Path,
    source_paths: Any,
    errors: list[str],
) -> None:
    if not isinstance(source_paths, Mapping):
        errors.append("sourceOfTruth must be an object")
        return
    required_keys = {
        "domainContract",
        "applicationUseCase",
        "executorPort",
        "postgresAdapter",
        "schemaFingerprint",
        "operatorCli",
        "evidenceGate",
        "migrations",
        "contractGate",
        "workflow",
    }
    if set(source_paths) != required_keys:
        errors.append("sourceOfTruth keys must exactly match the governed implementation surfaces")
    for key, relative_path in source_paths.items():
        if not isinstance(relative_path, str) or not relative_path:
            errors.append(f"sourceOfTruth {key} must be a non-empty repository path")
        elif not (root / relative_path).exists():
            errors.append(f"sourceOfTruth {key} path does not exist: {relative_path}")


def _validate_source_contracts(root: Path, errors: list[str]) -> None:
    required_fragments: dict[str, tuple[str, ...]] = {
        "src/app/infrastructure/postgres_deployment_migrations.py": (
            "pg_advisory_xact_lock",
            "lotus_idea_schema_migration",
            "lotus_idea_schema_migration_event",
            "trg_lotus_idea_schema_migration_event_append_only",
            "migration_bundle_contract_mismatch",
            "deployment_postgres_version_unsupported",
        ),
        "scripts/run_deployment_migrations.py": (
            'os.getenv("LOTUS_IDEA_DATABASE_URL", "")',
            "load_deployment_migration_contract",
            "expected_migration_bundle_sha256",
        ),
        "Dockerfile": (
            "COPY contracts ./contracts",
            "COPY migrations ./migrations",
            "COPY scripts/run_deployment_migrations.py",
            "COPY scripts/deployment_migration_evidence_gate.py",
        ),
    }
    for relative_path, fragments in required_fragments.items():
        content = (root / relative_path).read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{relative_path} missing `{fragment}`")
    cli = (root / "scripts/run_deployment_migrations.py").read_text(encoding="utf-8")
    if '"--database-url"' in cli or "'--database-url'" in cli:
        errors.append("deployment migration CLI must not accept a database URL argument")


def validate_deployment_migration_workflow(workflow: str) -> list[str]:
    errors = [
        f"deployment migration workflow missing `{fragment}`"
        for fragment in _REQUIRED_WORKFLOW_FRAGMENTS
        if fragment not in workflow
    ]
    errors.extend(
        f"deployment migration workflow must not contain `{fragment}`"
        for fragment in _PROHIBITED_WORKFLOW_FRAGMENTS
        if fragment in workflow
    )
    for run_block in _workflow_run_blocks(workflow):
        if "${{ inputs." in run_block or "${{ secrets." in run_block:
            errors.append(
                "deployment migration shell blocks must consume untrusted inputs and secrets "
                "through job environment variables"
            )
            break
    return errors


def validate_production_migration_entrypoints(
    workflows: Mapping[str, str],
) -> list[str]:
    disposable_fixture_workflows = {
        "postgres-disaster-recovery-drill.yml",
        "scheduled-data-lifecycle-review.yml",
    }
    errors: list[str] = []
    for name, workflow in workflows.items():
        if name in disposable_fixture_workflows:
            continue
        if name == WORKFLOW_RELATIVE_PATH.name:
            continue
        if "make migrate" in workflow or "scripts/run_migrations.py" in workflow:
            errors.append(
                f"{name} must use the governed exact-image deployment migration workflow; "
                "direct migration execution is reserved for approved disposable fixtures"
            )
    return errors


def _workflow_run_blocks(workflow: str) -> tuple[str, ...]:
    lines = workflow.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(?P<indent>\s*)run:\s*\|\s*$", lines[index])
        if not match:
            index += 1
            continue
        indentation = len(match.group("indent"))
        block: list[str] = []
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.strip() and len(line) - len(line.lstrip()) <= indentation:
                break
            block.append(line)
            index += 1
        blocks.append("\n".join(block))
    return tuple(blocks)


def main() -> int:
    errors = validate_deployment_migration_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Deployment migration contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
