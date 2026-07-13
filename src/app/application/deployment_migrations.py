from __future__ import annotations

from typing import Any

from app.domain.deployment_migrations import (
    DEPLOYMENT_MIGRATION_CONTRACT_VERSION,
    MIGRATION_EVIDENCE_SCHEMA_VERSION,
    DeploymentMigrationCommand,
    DeploymentMigrationResult,
)
from app.ports.deployment_migrations import DeploymentMigrationExecutor


def run_deployment_migrations(
    command: DeploymentMigrationCommand,
    *,
    executor: DeploymentMigrationExecutor,
) -> DeploymentMigrationResult:
    return executor.execute(command)


def deployment_migration_evidence(result: DeploymentMigrationResult) -> dict[str, Any]:
    return {
        "schemaVersion": MIGRATION_EVIDENCE_SCHEMA_VERSION,
        "migrationContractVersion": DEPLOYMENT_MIGRATION_CONTRACT_VERSION,
        "repository": result.release.repository,
        "proofScope": "deployment_migration_execution",
        "operation": result.operation.value,
        "environmentClass": result.release.environment_class.value,
        "gitCommitSha": result.release.git_commit_sha,
        "gitRef": result.release.git_ref,
        "ciRunId": result.release.ci_run_id,
        "imageDigestReference": result.release.image_digest_reference,
        "changeReference": result.release.change_reference,
        "deploymentActor": result.release.deployment_actor,
        "migrationBundleSha256": result.migration_bundle_sha256,
        "postgresMajorVersion": result.postgres_major_version,
        "previousVersion": result.previous_version,
        "currentVersion": result.current_version,
        "appliedVersions": list(result.applied_versions),
        "rolledBackVersions": list(result.rolled_back_versions),
        "adoptedVersions": list(result.adopted_versions),
        "executedAtUtc": result.executed_at_utc.isoformat().replace("+00:00", "Z"),
        "migrationHistoryBacked": True,
        "advisoryLockHeld": result.advisory_lock_held,
        "databaseIdentityDisclosed": False,
        "databaseCredentialsDisclosed": False,
        "schemaMutationOnServiceStartup": False,
        "productionCertified": False,
        "supportedFeaturePromoted": False,
        "remainingCertificationBlockers": [
            "protected_environment_execution_attestation_missing",
            "deployment_rollout_health_proof_missing",
            "production_change_approval_missing",
        ],
    }
