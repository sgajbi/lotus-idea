from __future__ import annotations

from datetime import UTC, datetime
import math
from typing import Any, Iterable, TypeGuard

from app.ports.resource_probe import ProcessResourceSnapshot

SCHEMA_VERSION = "lotus-idea.service-resource-baseline.v1"
MINIMUM_RESOURCE_SAMPLES = 2
RESOURCE_ENVIRONMENT_PROFILES = frozenset({"test", "production-like"})


def build_service_resource_baseline(
    *,
    snapshots: Iterable[ProcessResourceSnapshot],
    environment_profile: str,
    generated_at_utc: datetime,
    commit_sha: str,
    branch: str,
    run_id: str,
) -> dict[str, Any]:
    ordered = list(snapshots)
    if len(ordered) < MINIMUM_RESOURCE_SAMPLES:
        raise ValueError("resource baseline requires at least two snapshots")
    if environment_profile not in RESOURCE_ENVIRONMENT_PROFILES:
        raise ValueError("resource baseline measurement requires test or production-like profile")
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    for name, value in (("commit_sha", commit_sha), ("branch", branch), ("run_id", run_id)):
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    _validate_sequence(ordered)
    window_seconds = (ordered[-1].observed_at_utc - ordered[0].observed_at_utc).total_seconds()
    cpu_delta = ordered[-1].cpu_seconds_total - ordered[0].cpu_seconds_total
    fd_utilizations = [
        snapshot.open_file_descriptors / snapshot.max_file_descriptors
        for snapshot in ordered
        if snapshot.open_file_descriptors is not None and snapshot.max_file_descriptors is not None
    ]
    artifact = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "source_safe_process_resource_observation",
        "claimPosture": "report_only_resource_observation",
        "environmentProfile": environment_profile,
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "commitSha": commit_sha,
        "branch": branch,
        "runId": run_id,
        "observedWindowSeconds": window_seconds,
        "sampleCount": len(ordered),
        "cpuCoreSecondsPerSecondAverage": cpu_delta / window_seconds,
        "residentMemoryBytesAverage": sum(snapshot.resident_memory_bytes for snapshot in ordered)
        / len(ordered),
        "residentMemoryBytesMax": max(snapshot.resident_memory_bytes for snapshot in ordered),
        "virtualMemoryBytesMax": max(
            (
                snapshot.virtual_memory_bytes
                for snapshot in ordered
                if snapshot.virtual_memory_bytes is not None
            ),
            default=None,
        ),
        "openFileDescriptorUtilizationMax": max(fd_utilizations, default=None),
        "costAttributionVerified": False,
        "resourceAttestationVerified": False,
        "certificationReady": False,
        "certificationBlockers": [
            "production_like_resource_attestation_missing",
            "cost_attribution_evidence_missing",
        ],
        "supportedFeaturePromoted": False,
    }
    errors = validate_service_resource_baseline(artifact)
    if errors:
        raise ValueError("; ".join(errors))
    return artifact


def validate_service_resource_baseline(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")
    if artifact.get("proofScope") != "source_safe_process_resource_observation":
        errors.append("proofScope must remain process-resource-observation only")
    if artifact.get("claimPosture") != "report_only_resource_observation":
        errors.append("claimPosture must remain report_only_resource_observation")
    if artifact.get("environmentProfile") not in RESOURCE_ENVIRONMENT_PROFILES:
        errors.append("environmentProfile must be test or production-like")
    if artifact.get("repository") != "lotus-idea":
        errors.append("repository must be lotus-idea")
    for name in ("commitSha", "branch", "runId"):
        value = artifact.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} must be a non-blank string")
    _validate_measurements(artifact, errors)
    if artifact.get("costAttributionVerified") is not False:
        errors.append("resource observation must not claim cost attribution")
    if artifact.get("resourceAttestationVerified") is not False:
        errors.append("resource observation must not claim resource attestation")
    if artifact.get("certificationReady") is not False:
        errors.append("resource observation must remain non-certifying")
    if artifact.get("supportedFeaturePromoted") is not False:
        errors.append("resource observation must not promote a supported feature")
    expected_blockers = {
        "production_like_resource_attestation_missing",
        "cost_attribution_evidence_missing",
    }
    if set(artifact.get("certificationBlockers", [])) != expected_blockers:
        errors.append("resource observation certification blockers must remain explicit")
    return errors


def _validate_measurements(artifact: dict[str, Any], errors: list[str]) -> None:
    sample_count = artifact.get("sampleCount")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < MINIMUM_RESOURCE_SAMPLES
    ):
        errors.append("sampleCount must contain at least two samples")
    for name in (
        "observedWindowSeconds",
        "cpuCoreSecondsPerSecondAverage",
        "residentMemoryBytesAverage",
        "residentMemoryBytesMax",
    ):
        value = artifact.get(name)
        if not _non_negative_number(value) or (name == "observedWindowSeconds" and value == 0):
            errors.append(f"{name} must be a finite non-negative measurement")
    for name in ("virtualMemoryBytesMax", "openFileDescriptorUtilizationMax"):
        value = artifact.get(name)
        if value is not None and not _non_negative_number(value):
            errors.append(f"{name} must be null or a finite non-negative measurement")
    fd_utilization = artifact.get("openFileDescriptorUtilizationMax")
    if _non_negative_number(fd_utilization) and fd_utilization > 1:
        errors.append("openFileDescriptorUtilizationMax must not exceed one")


def _non_negative_number(value: object) -> TypeGuard[int | float]:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
    )


def _validate_sequence(snapshots: list[ProcessResourceSnapshot]) -> None:
    for previous, current in zip(snapshots, snapshots[1:]):
        if current.observed_at_utc <= previous.observed_at_utc:
            raise ValueError("resource snapshot timestamps must be strictly increasing")
        if current.cpu_seconds_total < previous.cpu_seconds_total:
            raise ValueError("cpu_seconds_total must be monotonic")
