from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    SourceIngestionWorkerPlan,
)


_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text

SCHEDULED_WORKER_SCHEMA_VERSION = "lotus-idea.source-ingestion.scheduled-worker.v1"
SCHEDULED_WORKER_PROOF_SCHEMA_VERSION = "lotus-idea.source-ingestion.scheduled-worker-proof.v1"
SCHEDULED_WORKER_ENTRYPOINT = "scripts/run_scheduled_source_ingestion_worker.py"
RUN_ONCE_WORKER_ENTRYPOINT = "scripts/run_source_ingestion_worker.py"
DOCKER_COMPOSE_WORKER_SERVICE = "lotus-idea-source-ingestion-worker"
DEFAULT_SCHEDULE_INTERVAL_SECONDS = 300
DEFAULT_SCHEDULE_MAX_RUNS = 1


@dataclass(frozen=True)
class SourceIngestionScheduleConfig:
    interval_seconds: int
    max_runs: int
    run_on_start: bool = True


def build_scheduled_worker_check_summary(
    *,
    plan: SourceIngestionWorkerPlan,
    schedule: SourceIngestionScheduleConfig,
) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEDULED_WORKER_SCHEMA_VERSION,
        "mode": "check_only",
        "sourceAuthority": "lotus-core",
        "opportunityFamily": "high_cash",
        "runOnceManifestSchemaVersion": MANIFEST_SCHEMA_VERSION,
        "schedulerEntrypoint": SCHEDULED_WORKER_ENTRYPOINT,
        "runOnceWorkerEntrypoint": RUN_ONCE_WORKER_ENTRYPOINT,
        "dockerComposeService": DOCKER_COMPOSE_WORKER_SERVICE,
        "schedulePolicy": {
            "intervalSeconds": schedule.interval_seconds,
            "maxRuns": schedule.max_runs,
            "runOnStart": schedule.run_on_start,
        },
        "runOnceManifest": plan.check_summary(),
        "supportedFeaturePromoted": False,
    }


def build_scheduled_worker_deploy_proof_payload(
    *,
    generated_at_utc: datetime,
    check_summary: Mapping[str, Any],
    scheduler_entrypoint_present: bool,
    run_once_worker_entrypoint_present: bool,
    docker_compose_service_present: bool,
) -> dict[str, Any]:
    return {
        "schemaVersion": SCHEDULED_WORKER_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "sourceAuthority": "lotus-core",
        "opportunityFamily": "high_cash",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "scheduled_source_ingestion_worker_deploy_contract",
        "scheduledWorkerDeployProofValid": (
            generated_at_utc.tzinfo is not None
            and generated_at_utc.utcoffset() is not None
            and scheduler_entrypoint_present
            and run_once_worker_entrypoint_present
            and docker_compose_service_present
            and _scheduled_worker_check_summary_is_valid(check_summary)
        ),
        "deployment": {
            "schedulerEntrypoint": SCHEDULED_WORKER_ENTRYPOINT,
            "schedulerEntrypointPresent": scheduler_entrypoint_present,
            "runOnceWorkerEntrypoint": RUN_ONCE_WORKER_ENTRYPOINT,
            "runOnceWorkerEntrypointPresent": run_once_worker_entrypoint_present,
            "dockerComposeService": DOCKER_COMPOSE_WORKER_SERVICE,
            "dockerComposeServicePresent": docker_compose_service_present,
        },
        "checkSummary": dict(check_summary),
        "remainingCertificationBlockers": (
            "live_core_source_proof_missing",
            "data_mesh_runtime_telemetry_not_certified",
            "gateway_workbench_proof_missing",
        ),
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def scheduled_worker_deploy_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != SCHEDULED_WORKER_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("sourceAuthority") != "lotus-core":
        return False
    if payload.get("opportunityFamily") != "high_cash":
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if payload.get("scheduledWorkerDeployProofValid") is not True:
        return False
    deployment = payload.get("deployment")
    if not isinstance(deployment, Mapping):
        return False
    if deployment.get("schedulerEntrypoint") != SCHEDULED_WORKER_ENTRYPOINT:
        return False
    if deployment.get("schedulerEntrypointPresent") is not True:
        return False
    if deployment.get("runOnceWorkerEntrypoint") != RUN_ONCE_WORKER_ENTRYPOINT:
        return False
    if deployment.get("runOnceWorkerEntrypointPresent") is not True:
        return False
    if deployment.get("dockerComposeService") != DOCKER_COMPOSE_WORKER_SERVICE:
        return False
    if deployment.get("dockerComposeServicePresent") is not True:
        return False
    check_summary = payload.get("checkSummary")
    return isinstance(check_summary, Mapping) and _scheduled_worker_check_summary_is_valid(
        check_summary
    )


def source_ingestion_schedule_config_from_values(
    *,
    interval_seconds: object,
    max_runs: object,
) -> SourceIngestionScheduleConfig:
    return SourceIngestionScheduleConfig(
        interval_seconds=_positive_int(
            interval_seconds,
            "intervalSeconds",
            default=DEFAULT_SCHEDULE_INTERVAL_SECONDS,
        ),
        max_runs=_positive_int(max_runs, "maxRuns", default=DEFAULT_SCHEDULE_MAX_RUNS),
    )


def _scheduled_worker_check_summary_is_valid(summary: Mapping[str, Any]) -> bool:
    if summary.get("schemaVersion") != SCHEDULED_WORKER_SCHEMA_VERSION:
        return False
    if summary.get("mode") != "check_only":
        return False
    if summary.get("sourceAuthority") != "lotus-core":
        return False
    if summary.get("opportunityFamily") != "high_cash":
        return False
    if summary.get("runOnceManifestSchemaVersion") != MANIFEST_SCHEMA_VERSION:
        return False
    if summary.get("schedulerEntrypoint") != SCHEDULED_WORKER_ENTRYPOINT:
        return False
    if summary.get("runOnceWorkerEntrypoint") != RUN_ONCE_WORKER_ENTRYPOINT:
        return False
    if summary.get("dockerComposeService") != DOCKER_COMPOSE_WORKER_SERVICE:
        return False
    if summary.get("supportedFeaturePromoted") is not False:
        return False
    schedule_policy = summary.get("schedulePolicy")
    if not isinstance(schedule_policy, Mapping):
        return False
    if not _is_positive_int(schedule_policy.get("intervalSeconds")):
        return False
    if not _is_positive_int(schedule_policy.get("maxRuns")):
        return False
    if schedule_policy.get("runOnStart") is not True:
        return False
    run_once_manifest = summary.get("runOnceManifest")
    if not isinstance(run_once_manifest, Mapping):
        return False
    return run_once_manifest.get("schemaVersion") == MANIFEST_SCHEMA_VERSION


def _positive_int(value: object, field_name: str, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, str) and value.strip():
        try:
            value = int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a positive integer") from exc
    if not _is_positive_int(value):
        raise ValueError(f"{field_name} must be a positive integer")
    assert isinstance(value, int)
    return value


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
