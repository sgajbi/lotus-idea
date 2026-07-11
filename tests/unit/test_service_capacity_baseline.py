from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.service_capacity_baseline import (
    CapacityMeasurement,
    SCENARIOS,
    build_service_capacity_baseline,
    validate_service_capacity_baseline,
)
from app.application.postgres_capacity_threshold_proof import (
    execute_postgres_capacity_threshold_proof,
)
from app.domain.capacity_posture import evaluate_postgres_capacity_posture
import app.application.service_capacity_baseline as baseline_module


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


class ThresholdProofPort:
    def __init__(self) -> None:
        self._utilizations = iter([0.2, 0.9, 0.2])

    def read_posture(self):  # type: ignore[no-untyped-def]
        return evaluate_postgres_capacity_posture(next(self._utilizations))

    def acquire_load_connection(self) -> None:
        pass

    def release_load_connections(self) -> None:
        pass

    def close(self) -> None:
        pass


def _threshold_proof() -> dict[str, object]:
    return execute_postgres_capacity_threshold_proof(
        stress_port=ThresholdProofPort(),
        environment_profile="test",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="threshold-1",
        maximum_load_connections=5,
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
        postgres_threshold_proof=_threshold_proof(),
        cost_resource_measured=True,
    )

    assert artifact["certificationBlockers"] == [
        "scenario_coverage_incomplete",
        "minimum_sample_volume_missing",
        "dependency_recovery_evidence_missing",
        "postgres_saturation_evidence_missing",
    ]
    assert artifact["resourceEvidence"]["postgresSaturationMeasured"] is False
    assert artifact["resourceEvidence"]["postgresThresholdProofValidated"] is True


def test_test_profile_or_mismatched_threshold_proof_cannot_clear_saturation_blocker() -> None:
    test_proof = _threshold_proof()
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="test",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="run-1",
        observed_window_seconds=1.0,
        postgres_threshold_proof=test_proof,
    )
    assert artifact["resourceEvidence"]["postgresThresholdProofValidated"] is True
    assert artifact["resourceEvidence"]["postgresSaturationMeasured"] is False
    assert "postgres_saturation_evidence_missing" in artifact["certificationBlockers"]

    mismatched = dict(_threshold_proof())
    mismatched["commitSha"] = "different"
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="run-1",
        observed_window_seconds=1.0,
        postgres_threshold_proof=mismatched,
    )
    assert artifact["resourceEvidence"]["postgresThresholdProofValidated"] is False
    assert "postgres_saturation_evidence_missing" in artifact["certificationBlockers"]


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
    with pytest.raises(ValueError, match="postgres_max_connection_utilization_fraction"):
        build_service_capacity_baseline(
            measurements=[],
            environment_profile="test",
            generated_at_utc=GENERATED_AT,
            commit_sha="abc123",
            branch="main",
            run_id="run-1",
            observed_window_seconds=1.0,
            postgres_max_connection_utilization_fraction=1.1,
        )


def test_build_rejects_non_positive_window_and_blank_provenance() -> None:
    with pytest.raises(ValueError, match="observed_window_seconds must be positive"):
        build_service_capacity_baseline(
            measurements=[],
            environment_profile="test",
            generated_at_utc=GENERATED_AT,
            commit_sha="abc123",
            branch="main",
            run_id="run-1",
            observed_window_seconds=0,
        )
    with pytest.raises(ValueError, match="commit_sha must not be blank"):
        build_service_capacity_baseline(
            measurements=[],
            environment_profile="test",
            generated_at_utc=GENERATED_AT,
            commit_sha=" ",
            branch="main",
            run_id="run-1",
            observed_window_seconds=1.0,
        )


def test_validator_rejects_schema_scope_and_scenario_shape() -> None:
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="test",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="run-1",
        observed_window_seconds=1.0,
    )
    artifact["schemaVersion"] = "unknown"
    artifact["proofScope"] = "unsafe"
    artifact["scenarios"] = "not-a-list"

    errors = validate_service_capacity_baseline(artifact)

    assert any("schemaVersion must be" in error for error in errors)
    assert "proofScope must remain source-safe and capacity-baseline-only" in errors
    assert "scenarios must be a list" in errors

    artifact["scenarios"] = [{"scenario": "api"}]
    assert "scenarios must match the governed capacity vocabulary and order" in (
        validate_service_capacity_baseline(artifact)
    )


def test_builder_fails_closed_if_final_artifact_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        baseline_module,
        "validate_service_capacity_baseline",
        lambda artifact: ["forced contract failure"],
    )

    with pytest.raises(ValueError, match="forced contract failure"):
        build_service_capacity_baseline(
            measurements=[],
            environment_profile="test",
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
