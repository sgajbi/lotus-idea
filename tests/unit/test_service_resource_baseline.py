from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import app.application.service_resource_baseline as baseline_module
from app.application.service_resource_baseline import (
    build_service_resource_baseline,
    validate_service_resource_baseline,
)
from app.ports.resource_probe import ProcessResourceSnapshot


START = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)


def _snapshot(
    seconds: int,
    cpu: float,
    rss: int,
    *,
    open_fds: int | None = 5,
    max_fds: int | None = 100,
) -> ProcessResourceSnapshot:
    return ProcessResourceSnapshot(
        observed_at_utc=START + timedelta(seconds=seconds),
        cpu_seconds_total=cpu,
        resident_memory_bytes=rss,
        virtual_memory_bytes=rss * 2,
        open_file_descriptors=open_fds,
        max_file_descriptors=max_fds,
    )


def _build(snapshots: list[ProcessResourceSnapshot]) -> dict[str, object]:
    return build_service_resource_baseline(
        snapshots=snapshots,
        environment_profile="test",
        generated_at_utc=START + timedelta(minutes=1),
        commit_sha="abc123",
        branch="feature/capacity",
        run_id="resource-1",
    )


def test_builds_bounded_non_certifying_resource_observation() -> None:
    artifact = _build([_snapshot(0, 10.0, 100), _snapshot(10, 12.5, 300)])

    assert artifact["cpuCoreSecondsPerSecondAverage"] == 0.25
    assert artifact["residentMemoryBytesAverage"] == 200
    assert artifact["residentMemoryBytesMax"] == 300
    assert artifact["virtualMemoryBytesMax"] == 600
    assert artifact["openFileDescriptorUtilizationMax"] == 0.05
    assert artifact["costEvidencePresent"] is False
    assert artifact["certificationReady"] is False
    assert validate_service_resource_baseline(artifact) == []


def test_supports_platforms_without_file_descriptor_metrics() -> None:
    artifact = _build(
        [
            _snapshot(0, 1.0, 100, open_fds=None, max_fds=None),
            _snapshot(1, 1.1, 100, open_fds=None, max_fds=None),
        ]
    )

    assert artifact["openFileDescriptorUtilizationMax"] is None


@pytest.mark.parametrize(
    ("snapshots", "message"),
    [
        ([_snapshot(0, 1.0, 100)], "at least two"),
        ([_snapshot(1, 1.0, 100), _snapshot(0, 2.0, 100)], "strictly increasing"),
        ([_snapshot(0, 2.0, 100), _snapshot(1, 1.0, 100)], "monotonic"),
    ],
)
def test_rejects_incomplete_or_invalid_sequences(
    snapshots: list[ProcessResourceSnapshot], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _build(snapshots)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"cpu_seconds_total": -1.0}, "cpu_seconds_total"),
        ({"resident_memory_bytes": -1}, "resident_memory_bytes"),
        ({"virtual_memory_bytes": -1}, "virtual_memory_bytes"),
        ({"open_file_descriptors": 1, "max_file_descriptors": None}, "present together"),
        ({"open_file_descriptors": -1, "max_file_descriptors": 10}, "must not be negative"),
        ({"open_file_descriptors": 11, "max_file_descriptors": 10}, "must not exceed"),
    ],
)
def test_snapshot_rejects_invalid_measurements(kwargs: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "observed_at_utc": START,
        "cpu_seconds_total": 1.0,
        "resident_memory_bytes": 1,
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=message):
        ProcessResourceSnapshot(**values)  # type: ignore[arg-type]


def test_validator_rejects_claim_inflation() -> None:
    artifact = _build([_snapshot(0, 1.0, 100), _snapshot(1, 1.1, 100)])
    artifact["costEvidencePresent"] = True
    artifact["productionLikeAttestationVerified"] = True
    artifact["certificationReady"] = True
    artifact["supportedFeaturePromoted"] = True
    artifact["certificationBlockers"] = []

    errors = validate_service_resource_baseline(artifact)

    assert "resource observation must not claim cost evidence" in errors
    assert "resource observation must not claim production-like attestation" in errors
    assert "resource observation must remain non-certifying" in errors
    assert "resource observation must not promote a supported feature" in errors
    assert "resource observation certification blockers must remain explicit" in errors


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schemaVersion", "unknown", "schemaVersion"),
        ("proofScope", "billing", "proofScope"),
        ("claimPosture", "certified", "claimPosture"),
        ("environmentProfile", "production", "environmentProfile"),
    ],
)
def test_validator_rejects_contract_identity_mutation(
    field: str, value: object, message: str
) -> None:
    artifact = _build([_snapshot(0, 1.0, 100), _snapshot(1, 1.1, 100)])
    artifact[field] = value

    assert any(message in error for error in validate_service_resource_baseline(artifact))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"environment_profile": "production-like"}, "requires the test profile"),
        ({"generated_at_utc": datetime(2026, 7, 11)}, "timezone-aware"),
        ({"commit_sha": " "}, "commit_sha must not be blank"),
    ],
)
def test_builder_rejects_ambiguous_provenance(overrides: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "snapshots": [_snapshot(0, 1.0, 100), _snapshot(1, 1.1, 100)],
        "environment_profile": "test",
        "generated_at_utc": START + timedelta(seconds=2),
        "commit_sha": "abc123",
        "branch": "main",
        "run_id": "resource-1",
    }
    values.update(overrides)
    with pytest.raises(ValueError, match=message):
        build_service_resource_baseline(**values)  # type: ignore[arg-type]


def test_builder_fails_closed_on_final_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        baseline_module,
        "validate_service_resource_baseline",
        lambda artifact: ["forced resource contract failure"],
    )
    with pytest.raises(ValueError, match="forced resource contract failure"):
        _build([_snapshot(0, 1.0, 100), _snapshot(1, 1.1, 100)])
