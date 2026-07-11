from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable


SCHEMA_VERSION = "lotus-idea.service-resource-baseline.v1"
MINIMUM_RESOURCE_SAMPLES = 2


@dataclass(frozen=True)
class ProcessResourceSnapshot:
    observed_at_utc: datetime
    cpu_seconds_total: float
    resident_memory_bytes: int
    virtual_memory_bytes: int | None = None
    open_file_descriptors: int | None = None
    max_file_descriptors: int | None = None

    def __post_init__(self) -> None:
        if self.observed_at_utc.tzinfo is None or self.observed_at_utc.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        if self.cpu_seconds_total < 0:
            raise ValueError("cpu_seconds_total must not be negative")
        if self.resident_memory_bytes < 0:
            raise ValueError("resident_memory_bytes must not be negative")
        if self.virtual_memory_bytes is not None and self.virtual_memory_bytes < 0:
            raise ValueError("virtual_memory_bytes must not be negative")
        if (self.open_file_descriptors is None) != (self.max_file_descriptors is None):
            raise ValueError("file descriptor measurements must be present together")
        if self.open_file_descriptors is not None:
            if self.open_file_descriptors < 0:
                raise ValueError("open_file_descriptors must not be negative")
            if self.max_file_descriptors is None or self.max_file_descriptors <= 0:
                raise ValueError("max_file_descriptors must be positive")
            if self.open_file_descriptors > self.max_file_descriptors:
                raise ValueError("open_file_descriptors must not exceed max_file_descriptors")


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
    if environment_profile != "test":
        raise ValueError("resource baseline measurement requires the test profile")
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
        "claimPosture": "controlled_test_resource_evidence_only",
        "environmentProfile": environment_profile,
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "commitSha": commit_sha,
        "branch": branch,
        "runId": run_id,
        "observedWindowSeconds": window_seconds,
        "sampleCount": len(ordered),
        "cpuCoreSecondsPerSecondAverage": cpu_delta / window_seconds,
        "residentMemoryBytesAverage": sum(
            snapshot.resident_memory_bytes for snapshot in ordered
        )
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
        "costEvidencePresent": False,
        "productionLikeAttestationVerified": False,
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
    if artifact.get("claimPosture") != "controlled_test_resource_evidence_only":
        errors.append("claimPosture must remain controlled_test_resource_evidence_only")
    if artifact.get("environmentProfile") != "test":
        errors.append("environmentProfile must remain test")
    if artifact.get("costEvidencePresent") is not False:
        errors.append("resource observation must not claim cost evidence")
    if artifact.get("productionLikeAttestationVerified") is not False:
        errors.append("resource observation must not claim production-like attestation")
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


def _validate_sequence(snapshots: list[ProcessResourceSnapshot]) -> None:
    for previous, current in zip(snapshots, snapshots[1:]):
        if current.observed_at_utc <= previous.observed_at_utc:
            raise ValueError("resource snapshot timestamps must be strictly increasing")
        if current.cpu_seconds_total < previous.cpu_seconds_total:
            raise ValueError("cpu_seconds_total must be monotonic")
