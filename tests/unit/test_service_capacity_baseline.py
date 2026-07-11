from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.service_capacity_baseline import (
    CapacityMeasurement,
    SCENARIOS,
    build_service_capacity_baseline,
    validate_service_capacity_baseline,
)


GENERATED_AT = datetime(2026, 7, 11, 3, 0, tzinfo=UTC)


def _measurement(scenario: str, index: int) -> CapacityMeasurement:
    return CapacityMeasurement(
        scenario=scenario,
        duration_seconds=(index + 1) / 100,
        outcome="failed" if index == 9 else "accepted",
        item_count=100 if scenario in {"source_ingestion", "outbox_delivery"} else 1,
        queue_age_seconds=5.0 if scenario == "outbox_delivery" else None,
        retry_count=2 if scenario == "dependency_failure" else 0,
        recovered=True if scenario == "dependency_failure" else None,
    )


def test_builds_ordered_source_safe_report_only_baseline() -> None:
    measurements = [_measurement(scenario, index) for scenario in SCENARIOS for index in range(10)]

    artifact = build_service_capacity_baseline(
        measurements=measurements,
        environment_profile="test",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="feature/capacity",
        run_id="local-1",
        observed_window_seconds=30.0,
    )

    assert [item["scenario"] for item in artifact["scenarios"]] == list(SCENARIOS)
    source = artifact["scenarios"][0]
    assert source["sampleCount"] == 10
    assert source["errorCount"] == 1
    assert source["errorRate"] == 0.1
    assert source["latencyP95Seconds"] == 0.1
    assert artifact["claimPosture"] == "report_only_baseline"
    assert artifact["certificationReady"] is False
    assert artifact["supportedFeaturePromoted"] is False
    assert artifact["certificationBlockers"] == [
        "production_like_environment_missing",
        "minimum_sample_volume_missing",
        "minimum_soak_window_missing",
        "postgres_saturation_evidence_missing",
        "cost_resource_evidence_missing",
    ]
    assert validate_service_capacity_baseline(artifact) == []


def test_missing_scenarios_and_dependency_recovery_remain_explicit() -> None:
    artifact = build_service_capacity_baseline(
        measurements=[CapacityMeasurement("api", 0.01, "accepted")],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="ci-1",
        observed_window_seconds=3_600,
        postgres_saturation_measured=True,
        cost_resource_measured=True,
    )

    assert artifact["certificationBlockers"] == [
        "scenario_coverage_incomplete",
        "minimum_sample_volume_missing",
        "dependency_recovery_evidence_missing",
    ]


def test_validator_rejects_claim_inflation_and_sensitive_fields() -> None:
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="test",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="feature/capacity",
        run_id="local-1",
        observed_window_seconds=1.0,
    )
    artifact["claimPosture"] = "production_certified"
    artifact["supportedFeaturePromoted"] = True
    artifact["payload"] = {"tenant_id": "unsafe"}

    errors = validate_service_capacity_baseline(artifact)

    assert "claimPosture must remain report_only_baseline" in errors
    assert "capacity evidence must not promote a supported feature" in errors
    assert any("$.payload" in error and "$.payload.tenant_id" in error for error in errors)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"scenario": "unknown"}, "scenario must use"),
        ({"outcome": "unknown"}, "outcome must use"),
        ({"duration_seconds": -0.1}, "duration_seconds must not be negative"),
        ({"item_count": -1}, "item_count must not be negative"),
        ({"queue_age_seconds": -1.0}, "queue_age_seconds must not be negative"),
        ({"retry_count": -1}, "retry_count must not be negative"),
        ({"recovered": True}, "recovered is only valid"),
    ],
)
def test_measurement_rejects_invalid_or_misclassified_values(
    kwargs: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "scenario": "api",
        "duration_seconds": 0.1,
        "outcome": "accepted",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        CapacityMeasurement(**values)  # type: ignore[arg-type]


def test_build_rejects_ambiguous_provenance() -> None:
    with pytest.raises(ValueError, match="environment_profile"):
        build_service_capacity_baseline(
            measurements=[],
            environment_profile="local",
            generated_at_utc=GENERATED_AT,
            commit_sha="abc123",
            branch="main",
            run_id="run-1",
            observed_window_seconds=1.0,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        build_service_capacity_baseline(
            measurements=[],
            environment_profile="test",
            generated_at_utc=datetime(2026, 7, 11),
            commit_sha="abc123",
            branch="main",
            run_id="run-1",
            observed_window_seconds=1.0,
        )
