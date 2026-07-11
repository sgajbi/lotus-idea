from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
import math
from typing import Any, Iterable

from app.application.postgres_capacity_threshold_proof import (
    validate_postgres_capacity_threshold_proof,
)
from app.application.capacity_evidence_qualification import (
    VerifiedArtifactAttestation,
    qualify_dependency_recovery_evidence,
    qualify_load_soak_evidence,
    qualify_postgres_capacity_threshold_evidence,
    qualify_resource_evidence,
)
from app.application.service_resource_baseline import validate_service_resource_baseline


SCHEMA_VERSION = "lotus-idea.service-capacity-baseline.v1"
SCENARIOS = (
    "api",
    "source_ingestion",
    "outbox_delivery",
    "downstream_submission",
    "dependency_failure",
    "postgresql",
)
ENVIRONMENT_PROFILES = frozenset({"test", "production-like", "production"})
OUTCOMES = frozenset({"accepted", "conflict", "failed", "rejected", "timeout"})
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
    observed_offset_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIOS:
            raise ValueError("scenario must use the governed capacity vocabulary")
        if self.outcome not in OUTCOMES:
            raise ValueError("outcome must use the governed capacity vocabulary")
        if not math.isfinite(self.duration_seconds) or self.duration_seconds < 0:
            raise ValueError("duration_seconds must be finite and not negative")
        if self.item_count < 0:
            raise ValueError("item_count must not be negative")
        if self.queue_age_seconds is not None and (
            not math.isfinite(self.queue_age_seconds) or self.queue_age_seconds < 0
        ):
            raise ValueError("queue_age_seconds must be finite and not negative")
        if self.retry_count < 0:
            raise ValueError("retry_count must not be negative")
        if self.observed_offset_seconds is not None and (
            not math.isfinite(self.observed_offset_seconds) or self.observed_offset_seconds < 0
        ):
            raise ValueError("observed_offset_seconds must be finite and not negative")
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
    postgres_threshold_proof: dict[str, Any] | None = None,
    postgres_threshold_attestation: VerifiedArtifactAttestation | None = None,
    dependency_recovery_proof: dict[str, Any] | None = None,
    dependency_recovery_attestation: VerifiedArtifactAttestation | None = None,
    load_soak_proof: dict[str, Any] | None = None,
    load_soak_attestation: VerifiedArtifactAttestation | None = None,
    postgres_max_connection_utilization_fraction: float | None = None,
    resource_baseline: dict[str, Any] | None = None,
    resource_attestation: VerifiedArtifactAttestation | None = None,
) -> dict[str, Any]:
    if environment_profile not in ENVIRONMENT_PROFILES:
        raise ValueError("environment_profile must be test, production-like, or production")
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    if not math.isfinite(observed_window_seconds) or observed_window_seconds <= 0:
        raise ValueError("observed_window_seconds must be finite and positive")
    if postgres_max_connection_utilization_fraction is not None and (
        not math.isfinite(postgres_max_connection_utilization_fraction)
        or not 0 <= postgres_max_connection_utilization_fraction <= 1
    ):
        raise ValueError(
            "postgres_max_connection_utilization_fraction must be finite and between zero and one"
        )
    for name, value in (("commit_sha", commit_sha), ("branch", branch), ("run_id", run_id)):
        if not value.strip():
            raise ValueError(f"{name} must not be blank")

    grouped: dict[str, list[CapacityMeasurement]] = {scenario: [] for scenario in SCENARIOS}
    for measurement in measurements:
        grouped[measurement.scenario].append(measurement)
    scenarios = [_scenario_summary(scenario, grouped[scenario]) for scenario in SCENARIOS]
    postgres_threshold_proof_validated = _postgres_threshold_proof_is_valid(
        postgres_threshold_proof,
        commit_sha=commit_sha,
        branch=branch,
    )
    postgres_qualification = _postgres_threshold_qualification(
        proof=postgres_threshold_proof,
        attestation=postgres_threshold_attestation,
        generated_at_utc=generated_at_utc,
        run_id=run_id,
    )
    postgres_saturation_measured = postgres_qualification is not None
    dependency_recovery_qualification = _dependency_recovery_qualification(
        proof=dependency_recovery_proof,
        attestation=dependency_recovery_attestation,
        generated_at_utc=generated_at_utc,
        run_id=run_id,
        commit_sha=commit_sha,
    )
    load_soak_qualification = _load_soak_qualification(
        proof=load_soak_proof,
        attestation=load_soak_attestation,
        generated_at_utc=generated_at_utc,
        run_id=run_id,
        commit_sha=commit_sha,
    )
    resource_baseline_validated = _resource_baseline_is_valid(
        resource_baseline,
        commit_sha=commit_sha,
        branch=branch,
    )
    resource_qualification = _resource_qualification(
        proof=resource_baseline,
        attestation=resource_attestation,
        generated_at_utc=generated_at_utc,
        run_id=run_id,
        commit_sha=commit_sha,
    )
    blockers = _certification_blockers(
        load_soak_attested=load_soak_qualification is not None,
        postgres_saturation_measured=postgres_saturation_measured,
        dependency_recovery_attested=dependency_recovery_qualification is not None,
        production_like_resource_attested=resource_qualification is not None,
        cost_attribution_verified=False,
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
        "resourceEvidence": _resource_evidence(
            scenarios=scenarios,
            load_soak_qualification=load_soak_qualification,
            dependency_recovery_qualification=dependency_recovery_qualification,
            postgres_saturation_measured=postgres_saturation_measured,
            postgres_threshold_proof_validated=postgres_threshold_proof_validated,
            postgres_threshold_proof=postgres_threshold_proof,
            postgres_qualification=postgres_qualification,
            postgres_max_connection_utilization_fraction=(
                postgres_max_connection_utilization_fraction
            ),
            resource_baseline_validated=resource_baseline_validated,
            resource_baseline=resource_baseline,
            resource_qualification=resource_qualification,
        ),
        "certificationReady": not blockers,
        "certificationBlockers": blockers,
        "supportedFeaturePromoted": False,
    }
    errors = validate_service_capacity_baseline(artifact)
    if errors:
        raise ValueError("; ".join(errors))
    return artifact


def _resource_evidence(
    *,
    scenarios: list[dict[str, Any]],
    load_soak_qualification: dict[str, Any] | None,
    dependency_recovery_qualification: dict[str, Any] | None,
    postgres_saturation_measured: bool,
    postgres_threshold_proof_validated: bool,
    postgres_threshold_proof: dict[str, Any] | None,
    postgres_qualification: dict[str, Any] | None,
    postgres_max_connection_utilization_fraction: float | None,
    resource_baseline_validated: bool,
    resource_baseline: dict[str, Any] | None,
    resource_qualification: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "loadSoakAttestationVerified": load_soak_qualification is not None,
        "loadSoakProofRunId": (
            load_soak_qualification.get("capacityProofRunId")
            if load_soak_qualification is not None
            else None
        ),
        "dependencyRecoveryObserved": _dependency_recovery_observed(scenarios),
        "dependencyRecoveryAttestationVerified": dependency_recovery_qualification is not None,
        "dependencyRecoveryProofRunId": (
            dependency_recovery_qualification.get("capacityProofRunId")
            if dependency_recovery_qualification is not None
            else None
        ),
        "postgresSaturationMeasured": postgres_saturation_measured,
        "postgresThresholdProofValidated": postgres_threshold_proof_validated,
        "postgresThresholdProofRunId": (
            postgres_threshold_proof.get("runId")
            if postgres_threshold_proof_validated and postgres_threshold_proof is not None
            else None
        ),
        "postgresThresholdAttestationVerified": postgres_saturation_measured,
        "postgresThresholdQualificationRunId": (
            postgres_qualification.get("qualificationRunId")
            if postgres_qualification is not None
            else None
        ),
        "postgresMaxConnectionUtilizationFraction": (postgres_max_connection_utilization_fraction),
        "resourceAttestationVerified": resource_qualification is not None,
        "resourceQualificationRunId": (
            resource_qualification.get("qualificationRunId")
            if resource_qualification is not None
            else None
        ),
        "costAttributionVerified": False,
        "resourceBaselineValidated": resource_baseline_validated,
        "resourceBaselineRunId": (
            resource_baseline.get("runId")
            if resource_baseline_validated and resource_baseline is not None
            else None
        ),
    }


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
    observation_offsets = [
        item.observed_offset_seconds
        for item in measurements
        if item.observed_offset_seconds is not None
    ]
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
        "observationSpanSeconds": (
            max(observation_offsets) - min(observation_offsets)
            if len(observation_offsets) == sample_count and sample_count > 1
            else None
        ),
    }


def _certification_blockers(
    *,
    load_soak_attested: bool,
    postgres_saturation_measured: bool,
    dependency_recovery_attested: bool,
    production_like_resource_attested: bool,
    cost_attribution_verified: bool,
) -> list[str]:
    blockers: list[str] = []
    if not load_soak_attested:
        blockers.append("load_soak_attestation_missing")
    if not dependency_recovery_attested:
        blockers.append("dependency_recovery_attestation_missing")
    if not postgres_saturation_measured:
        blockers.append("postgres_saturation_evidence_missing")
    if not production_like_resource_attested:
        blockers.append("production_like_resource_attestation_missing")
    if not cost_attribution_verified:
        blockers.append("cost_attribution_evidence_missing")
    return blockers


def _postgres_threshold_proof_is_valid(
    proof: dict[str, Any] | None,
    *,
    commit_sha: str,
    branch: str,
) -> bool:
    return bool(
        proof is not None
        and not validate_postgres_capacity_threshold_proof(proof)
        and proof.get("commitSha") == commit_sha
        and proof.get("branch") == branch
    )


def _dependency_recovery_observed(scenarios: list[dict[str, Any]]) -> bool:
    dependency = next(item for item in scenarios if item["scenario"] == "dependency_failure")
    return bool(
        dependency["recoverySampleCount"] > 0
        and dependency["recoverySuccessRate"] == 1.0
        and dependency["acceptedCount"] > dependency["recoverySampleCount"]
        and dependency["errorCount"] == 0
        and dependency["conflictCount"] == 0
    )


def _dependency_recovery_qualification(
    *,
    proof: dict[str, Any] | None,
    attestation: VerifiedArtifactAttestation | None,
    generated_at_utc: datetime,
    run_id: str,
    commit_sha: str,
) -> dict[str, Any] | None:
    if proof is None or attestation is None or proof.get("commitSha") != commit_sha:
        return None
    try:
        return qualify_dependency_recovery_evidence(
            capacity_proof=proof,
            verified_attestation=attestation,
            generated_at_utc=generated_at_utc,
            qualification_run_id=run_id,
        )
    except ValueError:
        return None


def _load_soak_qualification(
    *,
    proof: dict[str, Any] | None,
    attestation: VerifiedArtifactAttestation | None,
    generated_at_utc: datetime,
    run_id: str,
    commit_sha: str,
) -> dict[str, Any] | None:
    if proof is None or attestation is None or proof.get("commitSha") != commit_sha:
        return None
    try:
        return qualify_load_soak_evidence(
            capacity_proof=proof,
            verified_attestation=attestation,
            generated_at_utc=generated_at_utc,
            qualification_run_id=run_id,
        )
    except ValueError:
        return None


def _postgres_threshold_qualification(
    *,
    proof: dict[str, Any] | None,
    attestation: VerifiedArtifactAttestation | None,
    generated_at_utc: datetime,
    run_id: str,
) -> dict[str, Any] | None:
    if proof is None or attestation is None:
        return None
    try:
        return qualify_postgres_capacity_threshold_evidence(
            threshold_proof=proof,
            verified_attestation=attestation,
            generated_at_utc=generated_at_utc,
            qualification_run_id=run_id,
        )
    except ValueError:
        return None


def _resource_baseline_is_valid(
    baseline: dict[str, Any] | None,
    *,
    commit_sha: str,
    branch: str,
) -> bool:
    return bool(
        baseline is not None
        and not validate_service_resource_baseline(baseline)
        and baseline.get("commitSha") == commit_sha
        and baseline.get("branch") == branch
    )


def _resource_qualification(
    *,
    proof: dict[str, Any] | None,
    attestation: VerifiedArtifactAttestation | None,
    generated_at_utc: datetime,
    run_id: str,
    commit_sha: str,
) -> dict[str, Any] | None:
    if proof is None or attestation is None or proof.get("commitSha") != commit_sha:
        return None
    try:
        return qualify_resource_evidence(
            resource_proof=proof,
            verified_attestation=attestation,
            generated_at_utc=generated_at_utc,
            qualification_run_id=run_id,
        )
    except ValueError:
        return None


def _percentile(samples: list[float], percentile: float) -> float | None:
    if not samples:
        return None
    index = max(0, math.ceil(percentile * len(samples)) - 1)
    return samples[index]


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
