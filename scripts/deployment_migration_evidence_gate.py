# ruff: noqa: E402
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.deployment_migration_contract import (
    load_deployment_migration_contract,
)
from app.domain.deployment_migrations import (
    DEPLOYMENT_MIGRATION_CONTRACT_VERSION,
    MIGRATION_EVIDENCE_SCHEMA_VERSION,
    DeploymentEnvironmentClass,
    MigrationReleaseIdentity,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "operations" / "lotus-idea-deployment-migrations.v1.json"

REQUIRED_KEYS = {
    "schemaVersion",
    "migrationContractVersion",
    "repository",
    "proofScope",
    "operation",
    "environmentClass",
    "gitCommitSha",
    "gitRef",
    "ciRunId",
    "imageDigestReference",
    "changeReference",
    "deploymentActor",
    "migrationBundleSha256",
    "postgresMajorVersion",
    "previousVersion",
    "currentVersion",
    "appliedVersions",
    "rolledBackVersions",
    "adoptedVersions",
    "executedAtUtc",
    "migrationHistoryBacked",
    "advisoryLockHeld",
    "databaseIdentityDisclosed",
    "databaseCredentialsDisclosed",
    "schemaMutationOnServiceStartup",
    "productionCertified",
    "supportedFeaturePromoted",
    "remainingCertificationBlockers",
}


def validate_deployment_migration_evidence(
    payload: Mapping[str, Any],
    *,
    contract_path: Path = CONTRACT_PATH,
) -> list[str]:
    errors: list[str] = []
    contract = load_deployment_migration_contract(contract_path)
    missing = sorted(REQUIRED_KEYS - set(payload))
    extra = sorted(set(payload) - REQUIRED_KEYS)
    if missing:
        errors.append("evidence missing keys: " + ", ".join(missing))
    if extra:
        errors.append("evidence contains ungoverned keys: " + ", ".join(extra))
    if payload.get("schemaVersion") != MIGRATION_EVIDENCE_SCHEMA_VERSION:
        errors.append("schemaVersion must match the governed evidence schema")
    if payload.get("migrationContractVersion") != DEPLOYMENT_MIGRATION_CONTRACT_VERSION:
        errors.append("migrationContractVersion must match the governed migration contract")
    if payload.get("migrationBundleSha256") != contract.migration_bundle_sha256:
        errors.append("migrationBundleSha256 must match the governed contract")
    if payload.get("postgresMajorVersion") != contract.postgres_major_version:
        errors.append("postgresMajorVersion must match the governed contract")
    _validate_release_identity(payload, errors)
    _validate_operation(
        payload,
        migration_count=contract.migration_count,
        current_migration_version=contract.current_migration_version,
        errors=errors,
    )
    _validate_posture(payload, contract.remaining_certification_blockers, errors)
    _validate_timestamp(payload.get("executedAtUtc"), errors)
    _validate_sensitive_keys(payload, path="$", errors=errors)
    return errors


def _validate_release_identity(payload: Mapping[str, Any], errors: list[str]) -> None:
    try:
        MigrationReleaseIdentity(
            repository=str(payload.get("repository", "")),
            git_commit_sha=str(payload.get("gitCommitSha", "")),
            git_ref=str(payload.get("gitRef", "")),
            ci_run_id=str(payload.get("ciRunId", "")),
            image_digest_reference=str(payload.get("imageDigestReference", "")),
            environment_class=DeploymentEnvironmentClass(str(payload.get("environmentClass", ""))),
            change_reference=str(payload.get("changeReference", "")),
            deployment_actor=str(payload.get("deploymentActor", "")),
        )
    except ValueError as exc:
        errors.append(f"release identity invalid: {exc}")


def _validate_operation(
    payload: Mapping[str, Any],
    *,
    migration_count: int,
    current_migration_version: str,
    errors: list[str],
) -> None:
    operation = payload.get("operation")
    applied = _version_list(payload.get("appliedVersions"), "appliedVersions", errors)
    rolled_back = _version_list(payload.get("rolledBackVersions"), "rolledBackVersions", errors)
    adopted = _version_list(payload.get("adoptedVersions"), "adoptedVersions", errors)
    previous = _optional_version(payload.get("previousVersion"), "previousVersion", errors)
    current = _optional_version(payload.get("currentVersion"), "currentVersion", errors)
    governed_versions = tuple(f"{number:03d}" for number in range(1, migration_count + 1))
    for field, versions in (
        ("appliedVersions", applied),
        ("rolledBackVersions", rolled_back),
        ("adoptedVersions", adopted),
    ):
        if any(version not in governed_versions for version in versions):
            errors.append(f"{field} contains a version outside the governed migration set")
    if operation == "apply":
        if rolled_back or adopted:
            errors.append("apply evidence cannot contain rollback or adoption versions")
        if applied and applied != _ascending_range(applied[0], applied[-1]):
            errors.append("apply evidence versions must be a contiguous ascending range")
        expected_previous = _predecessor(applied[0]) if applied else current
        expected_current = applied[-1] if applied else previous
        if previous != expected_previous or current != expected_current:
            errors.append("apply evidence version transition is inconsistent")
    elif operation == "rollback":
        if not rolled_back or applied or adopted:
            errors.append("rollback evidence must contain only rolledBackVersions")
        if rolled_back and rolled_back != tuple(
            reversed(_ascending_range(rolled_back[-1], rolled_back[0]))
        ):
            errors.append("rollback evidence versions must be a contiguous descending range")
        expected_current = _predecessor(rolled_back[-1]) if rolled_back else None
        if rolled_back and (previous != rolled_back[0] or current != expected_current):
            errors.append("rollback evidence version transition is inconsistent")
    elif operation == "adopt":
        if adopted != governed_versions or applied or rolled_back:
            errors.append("adopt evidence must bind the complete governed migration set")
        if previous is not None or current != current_migration_version:
            errors.append("adopt evidence version transition is inconsistent")
    else:
        errors.append("operation must be apply, rollback, or adopt")


def _version_list(value: Any, field: str, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        errors.append(f"{field} must be a list")
        return ()
    versions = tuple(str(item) for item in value)
    if any(len(version) != 3 or not version.isdigit() for version in versions):
        errors.append(f"{field} must contain three-digit migration versions")
    if len(set(versions)) != len(versions):
        errors.append(f"{field} must not contain duplicate versions")
    return versions


def _optional_version(value: Any, field: str, errors: list[str]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) != 3 or not value.isdigit():
        errors.append(f"{field} must be null or a three-digit migration version")
        return None
    return value


def _ascending_range(first: str, last: str) -> tuple[str, ...]:
    return tuple(f"{number:03d}" for number in range(int(first), int(last) + 1))


def _predecessor(version: str) -> str | None:
    number = int(version) - 1
    return f"{number:03d}" if number else None


def _validate_posture(
    payload: Mapping[str, Any],
    remaining_blockers: tuple[str, ...],
    errors: list[str],
) -> None:
    required_true = ("migrationHistoryBacked", "advisoryLockHeld")
    required_false = (
        "databaseIdentityDisclosed",
        "databaseCredentialsDisclosed",
        "schemaMutationOnServiceStartup",
        "productionCertified",
        "supportedFeaturePromoted",
    )
    for key in required_true:
        if payload.get(key) is not True:
            errors.append(f"{key} must be true")
    for key in required_false:
        if payload.get(key) is not False:
            errors.append(f"{key} must be false")
    if payload.get("remainingCertificationBlockers") != list(remaining_blockers):
        errors.append("remainingCertificationBlockers must preserve certification truth")


def _validate_timestamp(value: Any, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append("executedAtUtc must be UTC text")
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append("executedAtUtc must be ISO-8601 text")
        return
    if not value.endswith("Z") or parsed.utcoffset() is None:
        errors.append("executedAtUtc must be UTC text")


def _validate_sensitive_keys(value: Any, *, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).replace("_", "").lower()
            if any(
                token in normalized
                for token in ("databaseurl", "dsn", "password", "hostname", "databaseidentity")
            ) and normalized not in {
                "databaseidentitydisclosed",
                "databasecredentialsdisclosed",
            }:
                errors.append(f"{path}.{key} is a forbidden evidence field")
            _validate_sensitive_keys(nested, path=f"{path}.{key}", errors=errors)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, nested in enumerate(value):
            _validate_sensitive_keys(nested, path=f"{path}[{index}]", errors=errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deployment migration evidence.")
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"deployment migration evidence unreadable: {exc}")
        return 1
    if not isinstance(payload, Mapping):
        print("deployment migration evidence must be an object")
        return 1
    errors = validate_deployment_migration_evidence(payload)
    if errors:
        print("\n".join(errors))
        return 1
    print("Deployment migration evidence gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
