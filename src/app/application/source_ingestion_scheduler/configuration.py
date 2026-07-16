from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    SourceIngestionWorkerPlan,
)


SCHEDULED_WORKER_SCHEMA_VERSION = "lotus-idea.source-ingestion.scheduled-worker.v1"
SCHEDULED_WORKER_ENTRYPOINT = "scripts/run_scheduled_source_ingestion_worker.py"
RUN_ONCE_WORKER_ENTRYPOINT = "scripts/run_source_ingestion_worker.py"
DOCKER_COMPOSE_WORKER_SERVICE = "lotus-idea-source-ingestion-worker"
DEFAULT_SCHEDULE_INTERVAL_SECONDS = 300
DEFAULT_SCHEDULE_MAX_RUNS = 1
SCHEDULE_INTERVAL_SECONDS_ENV = "LOTUS_IDEA_SOURCE_INGESTION_SCHEDULE_INTERVAL_SECONDS"
SCHEDULE_MAX_RUNS_ENV = "LOTUS_IDEA_SOURCE_INGESTION_SCHEDULE_MAX_RUNS"


@dataclass(frozen=True)
class SourceIngestionScheduleConfig:
    interval_seconds: int
    max_runs: int
    run_on_start: bool = True
    run_forever: bool = False


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
            "runForever": schedule.run_forever,
        },
        "runOnceManifest": plan.check_summary(),
        "supportedFeaturePromoted": False,
    }


def scheduled_worker_check_summary_is_valid(summary: object) -> bool:
    if not isinstance(summary, dict):
        return False
    if set(summary) != {
        "schemaVersion",
        "mode",
        "sourceAuthority",
        "opportunityFamily",
        "runOnceManifestSchemaVersion",
        "schedulerEntrypoint",
        "runOnceWorkerEntrypoint",
        "dockerComposeService",
        "schedulePolicy",
        "runOnceManifest",
        "supportedFeaturePromoted",
    }:
        return False
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
    if not isinstance(schedule_policy, dict):
        return False
    if set(schedule_policy) != {
        "intervalSeconds",
        "maxRuns",
        "runOnStart",
        "runForever",
    }:
        return False
    if not _is_positive_int(schedule_policy.get("intervalSeconds")):
        return False
    if not _is_positive_int(schedule_policy.get("maxRuns")):
        return False
    if schedule_policy.get("runOnStart") is not True:
        return False
    if not isinstance(schedule_policy.get("runForever"), bool):
        return False
    run_once_manifest = summary.get("runOnceManifest")
    if not isinstance(run_once_manifest, dict):
        return False
    return run_once_manifest.get("schemaVersion") == MANIFEST_SCHEMA_VERSION


def source_ingestion_schedule_config_from_values(
    *,
    interval_seconds: object,
    max_runs: object,
    run_forever: object = False,
) -> SourceIngestionScheduleConfig:
    return SourceIngestionScheduleConfig(
        interval_seconds=_positive_int(
            interval_seconds,
            "intervalSeconds",
            default=DEFAULT_SCHEDULE_INTERVAL_SECONDS,
        ),
        max_runs=_positive_int(max_runs, "maxRuns", default=DEFAULT_SCHEDULE_MAX_RUNS),
        run_forever=_boolean(run_forever, "runForever"),
    )


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


def _boolean(value: object, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in {"true", "True", "1"}:
        return True
    if value in {"false", "False", "0", None, ""}:
        return False
    raise ValueError(f"{field_name} must be a boolean")
