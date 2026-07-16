from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.application.source_ingestion_scheduler import (
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deployment_evidence_payload,
    build_scheduled_worker_source_contract_payload,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
)


GENERATED_AT = datetime(2026, 7, 16, 10, 10, tzinfo=UTC)
ROLLOUT_COMPLETED_AT = datetime(2026, 7, 16, 10, 9, tzinfo=UTC)
SOURCE_COMMIT_SHA = "a" * 40
IMAGE_DIGEST = f"sha256:{'b' * 64}"


def source_contract(*, repository_root: Path) -> dict[str, Any]:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "tenantId": "default",
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "workItems": [
                {
                    "portfolioId": "PB_SG_GLOBAL_BAL_001",
                    "asOfDate": "2026-06-21",
                }
            ],
        }
    )
    return build_scheduled_worker_source_contract_payload(
        generated_at_utc=GENERATED_AT,
        check_summary=build_scheduled_worker_check_summary(
            plan=plan,
            schedule=source_ingestion_schedule_config_from_values(
                interval_seconds=300,
                max_runs=1,
            ),
        ),
        repository_root=repository_root,
    )


def deployment_evidence(
    *,
    repository_root: Path,
    source_commit_sha: str = SOURCE_COMMIT_SHA,
) -> dict[str, Any]:
    contract = source_contract(repository_root=repository_root)
    return build_scheduled_worker_deployment_evidence_payload(
        generated_at_utc=GENERATED_AT,
        source_commit_sha=source_commit_sha,
        image_digest=IMAGE_DIGEST,
        target_environment="integration-sg",
        environment_class="test",
        controller_workflow="deploy-integration",
        controller_run_id="29489107377",
        controller_run_attempt=1,
        deployment_actor="github-actions",
        workload_identity="lotus-idea-source-ingestion-worker",
        rollout_completed_at_utc=ROLLOUT_COMPLETED_AT,
        scheduler_configuration_digest=str(contract["schedulerConfigurationDigest"]),
        source_contract_digest=str(contract["sourceContractDigest"]),
    )
