from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import math
from typing import Any, Iterable


SCHEMA_VERSION = "lotus-idea.service-capacity-baseline.v1"
SCENARIOS = (
    "api",
    "source_ingestion",
    "outbox_delivery",
    "dependency_failure",
    "postgresql",
)
ENVIRONMENT_PROFILES = frozenset({"test", "production-like", "production"})
OUTCOMES = frozenset({"accepted", "conflict", "failed", "rejected", "timeout"})
MINIMUM_CERTIFICATION_SAMPLES_PER_SCENARIO = 1_000
MINIMUM_SOAK_SECONDS = 3_600.0
FORBIDDEN_ARTIFACT_KEYS = frozenset(
    {
        "account_number",
        "authorization",
        "candidate_id",
        "client_id",
        "connection_string",
        "correlation_id",
        "database_url",
        "event_id",
        "idempotency_key",
        "password",
        "payload",
        "portfolio_id",
        "request_body",
        "secret",
        "tenant_id",
        "token",
        "trace_id",
        "url",
    }
)


@dataclass(frozen=True)
class CapacityMeasurement:
    scenario: str
    duration_seconds: float
    outcome: str
    item_count: int = 1
    queue_age_seconds: float | None = None
    retry_count: int = 0
    recovered: bool | None = None

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError("scenario must use the governed capacity vocabulary")
        if self.outcome not in OUTCOMES:
            raise ValueError("outcome must use the governed capacity vocabulary")
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must not be negative")
        if self.item_count < 0:
            raise ValueError("item_count must not be negative")
        if self.queue_age_seconds is not None and self.queue_age_seconds < 0:
            raise ValueError("queue_age_seconds must not be negative")
        if self.retry_count < 0:
            raise ValueError("retry_count must not be negative")
        if self.scenario != "dependency_failure" and self.recovered is not None:
            raise ValueError("recovered is only valid for dependency_failure measurements")


def build_service_capacity_baseline(
    *,
    measurements: Iterable[CapacityMeasurement],
    environment_profile: str,
    generated_at_utc: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
    observed_window_seconds: float,
    postgres_saturation_measured: bool = False,
    postgres_max_connection_utilization_fraction: float | None = None,
    cost_resource_measured: bool = False,
) -> dict[str, Any]:
    if environment_profile not in ENVIRONMENT_PROFILES:
        raise ValueError("environment_profile must be test, production-like, or production")
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    if observed_window_seconds <= 0:
        raise ValueError("observed_window_seconds must be positive")
    if (
        postgres_max_connection_utilization_fraction is not None
        and not 0 <= postgres_max_connection_utilization_fraction <= 1
    ):
        raise ValueError(
            "postgres_max_connection_utilization_fraction must be between zero and one"
        )
    for name, value in (("commit_sha", commit_sha), ("branch", branch), ("run_id", run_id)):
        if not value.strip():
            raise ValueError(f"{name} must not be blank")

    grouped: dict[str, list[CapacityMeasurement]] = {scenario: [] for scenario in SCENARIOS}
    for measurement in measurements:
        grouped[measurement.scenario].append(measurement)
    scenarios = [_scenario_summary(scenario, grouped[scenario]) for scenario in SCENARIOS]
    blockers = _certification_blockers(
        environment_profile=environment_profile,
        scenarios=scenarios,
        observed_window_seconds=observed_window_seconds,
        postgres_saturation_measured=postgres_saturation_measured,
        cost_resource_measured=cost_resource_measured,
    )
    artifact = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "source_safe_service_capacity_baseline",
        "claimPosture": "report_only_baseline",
        "environmentProfile": environment_profile,
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "commitSha": commit_sha,
        "branch": branch,
        "runId": run_id,
        "observedWindowSeconds": observed_window_seconds,
        "scenarios": scenarios,
        "resourceEvidence": {
            "postgresSaturationMeasured": postgres_saturation_measured,
            "postgresMaxConnectionUtilizationFraction": (
                postgres_max_connection_utilization_fraction
            ),
            "costResourceMeasured": cost_resource_measured,
        },
        "certificationReady": not blockers,
        "certificationBlockers": blockers,
        "supportedFeaturePromoted": False,
    }
    errors = validate_service_capacity_baseline(artifact)
    if errors:
        raise ValueError("; ".join(errors))
    return artifact


def validate_service_capacity_baseline(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")
    if artifact.get("proofScope") != "source_safe_service_capacity_baseline":
        errors.append("proofScope must remain source-safe and capacity-baseline-only")
    if artifact.get("claimPosture") != "report_only_baseline":
        errors.append("claimPosture must remain report_only_baseline")
    if artifact.get("supportedFeaturePromoted") is not False:
        errors.append("capacity evidence must not promote a supported feature")
    scenarios = artifact.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("scenarios must be a list")
    elif [item.get("scenario") for item in scenarios if isinstance(item, dict)] != list(SCENARIOS):
        errors.append("scenarios must match the governed capacity vocabulary and order")
    leaked = sorted(_forbidden_key_paths(artifact))
    if leaked:
        errors.append(f"artifact contains forbidden source fields: {', '.join(leaked)}")
    return errors


def _scenario_summary(
    scenario: str,
    measurements: list[CapacityMeasurement],
) -> dict[str, Any]:
    durations = sorted(item.duration_seconds for item in measurements)
    outcomes = Counter(item.outcome for item in measurements)
    sample_count = len(measurements)
    total_items = sum(item.item_count for item in measurements)
    total_duration = sum(durations)
    queue_ages = [
        item.queue_age_seconds for item in measurements if item.queue_age_seconds is not None
    ]
    recovery_samples = [item.recovered for item in measurements if item.recovered is not None]
    return {
        "scenario": scenario,
        "sampleCount": sample_count,
        "acceptedCount": outcomes["accepted"],
        "errorCount": sum(outcomes[outcome] for outcome in ("failed", "rejected", "timeout")),
        "conflictCount": outcomes["conflict"],
        "errorRate": _ratio(
            sum(outcomes[outcome] for outcome in ("failed", "rejected", "timeout")),
            sample_count,
        ),
        "latencyP50Seconds": _percentile(durations, 0.50),
        "latencyP95Seconds": _percentile(durations, 0.95),
        "latencyP99Seconds": _percentile(durations, 0.99),
        "observedItemCount": total_items,
        "observedItemsPerSecond": _ratio(total_items, total_duration),
        "maxQueueAgeSeconds": max(queue_ages, default=None),
        "maxRetryCount": max((item.retry_count for item in measurements), default=0),
        "recoverySampleCount": len(recovery_samples),
        "recoverySuccessRate": (
            _ratio(sum(recovered is True for recovered in recovery_samples), len(recovery_samples))
            if recovery_samples
            else None
        ),
    }


def _certification_blockers(
    *,
    environment_profile: str,
    scenarios: list[dict[str, Any]],
    observed_window_seconds: float,
    postgres_saturation_measured: bool,
    cost_resource_measured: bool,
) -> list[str]:
    blockers: list[str] = []
    if environment_profile == "test":
        blockers.append("production_like_environment_missing")
    if any(item["sampleCount"] == 0 for item in scenarios):
        blockers.append("scenario_coverage_incomplete")
    if any(item["sampleCount"] < MINIMUM_CERTIFICATION_SAMPLES_PER_SCENARIO for item in scenarios):
        blockers.append("minimum_sample_volume_missing")
    if observed_window_seconds < MINIMUM_SOAK_SECONDS:
        blockers.append("minimum_soak_window_missing")
    dependency = next(item for item in scenarios if item["scenario"] == "dependency_failure")
    if dependency["recoverySampleCount"] == 0:
        blockers.append("dependency_recovery_evidence_missing")
    if not postgres_saturation_measured:
        blockers.append("postgres_saturation_evidence_missing")
    if not cost_resource_measured:
        blockers.append("cost_resource_evidence_missing")
    return blockers


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    index = max(0, math.ceil(percentile * len(values)) - 1)
    return values[index]


def _ratio(numerator: int, denominator: int | float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _forbidden_key_paths(value: Any, path: str = "$") -> set[str]:
    leaked: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            child_path = f"{path}.{key}"
            if normalized in FORBIDDEN_ARTIFACT_KEYS:
                leaked.add(child_path)
            leaked.update(_forbidden_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaked.update(_forbidden_key_paths(child, f"{path}[{index}]"))
    return leaked
