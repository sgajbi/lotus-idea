from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.capacity_evidence_qualification import (
    DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
    VerifiedArtifactAttestation,
)
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
from app.application.service_resource_baseline import build_service_resource_baseline
from app.ports.resource_probe import ProcessResourceSnapshot
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


def _verified_attestation() -> VerifiedArtifactAttestation:
    return VerifiedArtifactAttestation(
        subject_sha256="b" * 64,
        repository=TRUSTED_REPOSITORY,
        signer_workflow=TRUSTED_SIGNER_WORKFLOW,
        source_ref=TRUSTED_SOURCE_REF,
        source_commit_sha="abc123",
    )


def _dependency_attestation() -> VerifiedArtifactAttestation:
    return VerifiedArtifactAttestation(
        subject_sha256="c" * 64,
        repository=TRUSTED_REPOSITORY,
        signer_workflow=DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
        source_ref=TRUSTED_SOURCE_REF,
        source_commit_sha="abc123",
    )


def _dependency_recovery_proof() -> dict[str, Any]:
    return build_service_capacity_baseline(
        measurements=[
            CapacityMeasurement("dependency_failure", 0.1, "accepted"),
            CapacityMeasurement("dependency_failure", 0.1, "accepted", recovered=True),
        ],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="dependency-proof-1",
        observed_window_seconds=10.0,
    )


def _resource_baseline() -> dict[str, object]:
    return build_service_resource_baseline(
        snapshots=[
            ProcessResourceSnapshot(GENERATED_AT, 1.0, 100),
            ProcessResourceSnapshot(GENERATED_AT + timedelta(seconds=1), 1.1, 200),
        ],
        environment_profile="test",
        generated_at_utc=GENERATED_AT + timedelta(seconds=2),
        commit_sha="abc123",
        branch="main",
        run_id="resource-1",
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
        "dependency_recovery_attestation_missing",
        "postgres_saturation_evidence_missing",
        "cost_resource_evidence_missing",
    ]
    assert validate_service_capacity_baseline(artifact) == []


def test_attested_mainline_proof_clears_only_saturation_blocker() -> None:
    artifact = build_service_capacity_baseline(
        measurements=[CapacityMeasurement("api", 0.01, "accepted")],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="ci-1",
        observed_window_seconds=3_600,
        postgres_threshold_proof=_threshold_proof(),
        postgres_threshold_attestation=_verified_attestation(),
    )

    assert artifact["certificationBlockers"] == [
        "scenario_coverage_incomplete",
        "minimum_sample_volume_missing",
        "dependency_recovery_attestation_missing",
        "cost_resource_evidence_missing",
    ]
    assert artifact["resourceEvidence"]["postgresSaturationMeasured"] is True
    assert artifact["resourceEvidence"]["postgresThresholdProofValidated"] is True
    assert artifact["resourceEvidence"]["postgresThresholdAttestationVerified"] is True


def test_local_recovery_observation_cannot_clear_attestation_blocker() -> None:
    proof = _dependency_recovery_proof()

    assert proof["resourceEvidence"]["dependencyRecoveryObserved"] is True
    assert proof["resourceEvidence"]["dependencyRecoveryAttestationVerified"] is False
    assert "dependency_recovery_attestation_missing" in proof["certificationBlockers"]


def test_attested_mainline_recovery_proof_clears_only_dependency_blocker() -> None:
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="aggregate-1",
        observed_window_seconds=1.0,
        dependency_recovery_proof=_dependency_recovery_proof(),
        dependency_recovery_attestation=_dependency_attestation(),
    )

    resource = artifact["resourceEvidence"]
    assert resource["dependencyRecoveryObserved"] is False
    assert resource["dependencyRecoveryAttestationVerified"] is True
    assert resource["dependencyRecoveryProofRunId"] == "dependency-proof-1"
    assert "dependency_recovery_attestation_missing" not in artifact["certificationBlockers"]


def test_mismatched_dependency_attestation_cannot_clear_blocker() -> None:
    attestation = VerifiedArtifactAttestation(
        **{**_dependency_attestation().__dict__, "source_commit_sha": "different"}
    )
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="aggregate-1",
        observed_window_seconds=1.0,
        dependency_recovery_proof=_dependency_recovery_proof(),
        dependency_recovery_attestation=attestation,
    )

    assert artifact["resourceEvidence"]["dependencyRecoveryAttestationVerified"] is False
    assert "dependency_recovery_attestation_missing" in artifact["certificationBlockers"]


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
    assert artifact["resourceEvidence"]["postgresThresholdAttestationVerified"] is False
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


def test_mismatched_attestation_cannot_clear_saturation_blocker() -> None:
    mismatched = VerifiedArtifactAttestation(
        **{**_verified_attestation().__dict__, "source_commit_sha": "different"}
    )
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="run-1",
        observed_window_seconds=1.0,
        postgres_threshold_proof=_threshold_proof(),
        postgres_threshold_attestation=mismatched,
    )

    assert artifact["resourceEvidence"]["postgresThresholdAttestationVerified"] is False
    assert "postgres_saturation_evidence_missing" in artifact["certificationBlockers"]


def test_links_resource_observation_without_claiming_cost_evidence() -> None:
    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="run-1",
        observed_window_seconds=1.0,
        resource_baseline=_resource_baseline(),
    )

    resource = artifact["resourceEvidence"]
    assert resource["resourceBaselineValidated"] is True
    assert resource["resourceBaselineRunId"] == "resource-1"
    assert resource["costResourceMeasured"] is False
    assert "cost_resource_evidence_missing" in artifact["certificationBlockers"]


def test_rejects_resource_observation_from_another_commit() -> None:
    resource_baseline = dict(_resource_baseline())
    resource_baseline["commitSha"] = "different"

    artifact = build_service_capacity_baseline(
        measurements=[],
        environment_profile="production-like",
        generated_at_utc=GENERATED_AT,
        commit_sha="abc123",
        branch="main",
        run_id="run-1",
        observed_window_seconds=1.0,
        resource_baseline=resource_baseline,
    )

    assert artifact["resourceEvidence"]["resourceBaselineValidated"] is False
    assert artifact["resourceEvidence"]["resourceBaselineRunId"] is None


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
