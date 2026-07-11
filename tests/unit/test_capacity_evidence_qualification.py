from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from app.application.capacity_evidence_qualification import (
    DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
    LOAD_SOAK_SCENARIO_THRESHOLDS,
    LOAD_SOAK_SIGNER_WORKFLOW,
    RESOURCE_SIGNER_WORKFLOW,
    TRUSTED_REPOSITORY,
    TRUSTED_SIGNER_WORKFLOW,
    TRUSTED_SOURCE_REF,
    VerifiedArtifactAttestation,
    qualify_dependency_recovery_evidence,
    qualify_load_soak_evidence,
    qualify_postgres_capacity_threshold_evidence,
    qualify_resource_evidence,
)
from app.application.postgres_capacity_threshold_proof import (
    execute_postgres_capacity_threshold_proof,
)
from app.domain.capacity_posture import evaluate_postgres_capacity_posture


class ThresholdPort:
    def __init__(self) -> None:
        self._values = iter([0.2, 0.9, 0.2])

    def read_posture(self):  # type: ignore[no-untyped-def]
        return evaluate_postgres_capacity_posture(next(self._values))

    def acquire_load_connection(self) -> None:
        pass

    def release_load_connections(self) -> None:
        pass

    def close(self) -> None:
        pass


def _proof() -> dict[str, object]:
    return execute_postgres_capacity_threshold_proof(
        stress_port=ThresholdPort(),
        environment_profile="test",
        generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        commit_sha="a" * 40,
        branch="main",
        run_id="threshold-1",
        maximum_load_connections=5,
    )


def _attestation(**overrides: str) -> VerifiedArtifactAttestation:
    values = {
        "subject_sha256": "b" * 64,
        "repository": TRUSTED_REPOSITORY,
        "signer_workflow": TRUSTED_SIGNER_WORKFLOW,
        "source_ref": TRUSTED_SOURCE_REF,
        "source_commit_sha": "a" * 40,
    }
    values.update(overrides)
    return VerifiedArtifactAttestation(**values)


def _dependency_proof() -> dict[str, object]:
    return {
        "schemaVersion": "lotus-idea.service-capacity-baseline.v1",
        "repository": "lotus-idea",
        "proofScope": "source_safe_service_capacity_baseline",
        "claimPosture": "report_only_baseline",
        "environmentProfile": "production-like",
        "commitSha": "a" * 40,
        "branch": "main",
        "runId": "dependency-proof-1",
        "scenarios": [
            {
                "scenario": "dependency_failure",
                "sampleCount": 2,
                "acceptedCount": 2,
                "errorCount": 0,
                "conflictCount": 0,
                "recoverySampleCount": 1,
                "recoverySuccessRate": 1.0,
            }
        ],
        "supportedFeaturePromoted": False,
    }


def _dependency_attestation(**overrides: str) -> VerifiedArtifactAttestation:
    return _attestation(
        signer_workflow=DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
        **overrides,
    )


def _load_soak_proof() -> dict[str, object]:
    proof = _dependency_proof()
    proof["runId"] = "load-soak-proof-1"
    proof["observedWindowSeconds"] = 3_600.0
    proof["scenarios"] = [
        {
            "scenario": scenario,
            "sampleCount": 1_000,
            "acceptedCount": 1_000,
            "errorCount": 0,
            "conflictCount": 0,
            "errorRate": 0.0,
            "latencyP95Seconds": thresholds[1],
            "latencyP99Seconds": thresholds[2],
            "observationSpanSeconds": 3_600.0,
        }
        for scenario, thresholds in LOAD_SOAK_SCENARIO_THRESHOLDS.items()
    ]
    return proof


def _load_soak_attestation() -> VerifiedArtifactAttestation:
    return _attestation(signer_workflow=LOAD_SOAK_SIGNER_WORKFLOW)


def _resource_proof() -> dict[str, object]:
    return {
        "schemaVersion": "lotus-idea.service-resource-baseline.v1",
        "repository": "lotus-idea",
        "proofScope": "source_safe_process_resource_observation",
        "claimPosture": "report_only_resource_observation",
        "environmentProfile": "production-like",
        "commitSha": "a" * 40,
        "branch": "main",
        "runId": "resource-proof-1",
        "observedWindowSeconds": 3_600.0,
        "sampleCount": 61,
        "cpuCoreSecondsPerSecondAverage": 0.5,
        "residentMemoryBytesAverage": 100,
        "residentMemoryBytesMax": 120,
        "virtualMemoryBytesMax": 200,
        "openFileDescriptorUtilizationMax": 0.1,
        "costAttributionVerified": False,
        "resourceAttestationVerified": False,
        "certificationReady": False,
        "certificationBlockers": [
            "production_like_resource_attestation_missing",
            "cost_attribution_evidence_missing",
        ],
        "supportedFeaturePromoted": False,
    }


def _resource_attestation() -> VerifiedArtifactAttestation:
    return _attestation(signer_workflow=RESOURCE_SIGNER_WORKFLOW)


def test_qualifies_only_attested_mainline_threshold_evidence() -> None:
    qualification = qualify_postgres_capacity_threshold_evidence(
        threshold_proof=_proof(),
        verified_attestation=_attestation(),
        generated_at_utc=datetime(2026, 7, 11, 7, 0, tzinfo=UTC),
        qualification_run_id="qualification-1",
    )

    assert qualification["claimPosture"] == "production_like_environment_qualified"
    assert qualification["attestationVerified"] is True
    assert qualification["thresholdProofSha256"] == "b" * 64
    assert qualification["productionCapacityCertified"] is False
    assert qualification["supportedFeaturePromoted"] is False


def test_qualifies_only_attested_fault_and_clean_recovery_evidence() -> None:
    qualification = qualify_dependency_recovery_evidence(
        capacity_proof=_dependency_proof(),
        verified_attestation=_dependency_attestation(),
        generated_at_utc=datetime(2026, 7, 11, 7, 0, tzinfo=UTC),
        qualification_run_id="qualification-2",
    )

    assert qualification["proofScope"] == ("attested_dependency_recovery_environment_qualification")
    assert qualification["capacityProofRunId"] == "dependency-proof-1"
    assert qualification["attestationVerified"] is True
    assert qualification["productionCapacityCertified"] is False
    assert qualification["supportedFeaturePromoted"] is False


def test_qualifies_only_attested_load_soak_within_slo_thresholds() -> None:
    qualification = qualify_load_soak_evidence(
        capacity_proof=_load_soak_proof(),
        verified_attestation=_load_soak_attestation(),
        generated_at_utc=datetime(2026, 7, 11, 9, 0, tzinfo=UTC),
        qualification_run_id="qualification-3",
    )

    assert qualification["proofScope"] == ("attested_service_load_soak_environment_qualification")
    assert qualification["capacityProofRunId"] == "load-soak-proof-1"
    assert qualification["qualifiedScenarios"] == list(LOAD_SOAK_SCENARIO_THRESHOLDS)
    assert qualification["productionCapacityCertified"] is False
    assert qualification["supportedFeaturePromoted"] is False


def test_qualifies_attested_production_like_resource_observation_without_cost_claim() -> None:
    qualification = qualify_resource_evidence(
        resource_proof=_resource_proof(),
        verified_attestation=_resource_attestation(),
        generated_at_utc=datetime(2026, 7, 11, 9, 0, tzinfo=UTC),
        qualification_run_id="qualification-resource-1",
    )

    assert qualification["proofScope"] == "attested_process_resource_environment_qualification"
    assert qualification["resourceProofRunId"] == "resource-proof-1"
    assert qualification["attestationVerified"] is True
    assert qualification["costAttributionVerified"] is False
    assert qualification["productionCapacityCertified"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"environmentProfile": "test"}, "must be production-like"),
        ({"sampleCount": 60}, "minimum sample count"),
        ({"observedWindowSeconds": 3_599.9}, "minimum observation window"),
        ({"costAttributionVerified": True}, "must not claim cost attribution"),
    ],
)
def test_resource_qualification_rejects_unqualified_or_inflated_proof(
    mutation: dict[str, object], message: str
) -> None:
    proof = {**_resource_proof(), **mutation}

    with pytest.raises(ValueError, match=message):
        qualify_resource_evidence(
            resource_proof=proof,
            verified_attestation=_resource_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-resource-1",
        )


def test_resource_qualification_rejects_non_resource_producer_attestation() -> None:
    with pytest.raises(ValueError, match="workflow is not trusted"):
        qualify_resource_evidence(
            resource_proof=_resource_proof(),
            verified_attestation=_dependency_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-resource-1",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("observedWindowSeconds", 3_599.9, "minimum observation window"),
        ("observedWindowSeconds", True, "minimum observation window"),
        ("scenarios", {}, "scenarios must be a list"),
        ("scenarios", [], "scenario api is missing"),
    ],
)
def test_load_soak_qualification_rejects_incomplete_proof(
    field: str, value: object, message: str
) -> None:
    proof = {**_load_soak_proof(), field: value}

    with pytest.raises(ValueError, match=message):
        qualify_load_soak_evidence(
            capacity_proof=proof,
            verified_attestation=_load_soak_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-3",
        )


@pytest.mark.parametrize(
    ("mutation", "scenario"),
    [
        ({"sampleCount": 999}, "api"),
        ({"observationSpanSeconds": 3_599.9}, "api"),
        ({"conflictCount": 1}, "source_ingestion"),
        ({"errorRate": 0.002}, "outbox_delivery"),
        ({"latencyP95Seconds": 2.01}, "downstream_submission"),
        ({"latencyP99Seconds": 0.51}, "postgresql"),
    ],
)
def test_load_soak_qualification_rejects_scenario_threshold_breach(
    mutation: dict[str, object], scenario: str
) -> None:
    proof = _load_soak_proof()
    source_scenarios = cast(list[dict[str, object]], proof["scenarios"])
    scenarios = [dict(item) for item in source_scenarios]
    target = next(item for item in scenarios if item["scenario"] == scenario)
    target.update(mutation)
    proof["scenarios"] = scenarios

    with pytest.raises(ValueError, match=f"scenario {scenario} breaches"):
        qualify_load_soak_evidence(
            capacity_proof=proof,
            verified_attestation=_load_soak_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-3",
        )


def test_load_soak_qualification_rejects_wrong_signer() -> None:
    with pytest.raises(ValueError, match="workflow is not trusted"):
        qualify_load_soak_evidence(
            capacity_proof=_load_soak_proof(),
            verified_attestation=_dependency_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-3",
        )


@pytest.mark.parametrize(
    ("mutations", "message"),
    [
        ({"schemaVersion": "unknown"}, "schemaVersion"),
        ({"proofScope": "raw_dependency_payload"}, "source-safe"),
        ({"claimPosture": "production_certified"}, "report_only_baseline"),
        ({"environmentProfile": "test"}, "production-like"),
        ({"branch": "feature/capacity"}, "originate from main"),
        ({"supportedFeaturePromoted": True}, "must not promote"),
        ({"scenarios": {}}, "scenarios must be a list"),
        ({"scenarios": []}, "scenario is missing"),
    ],
)
def test_rejects_unqualified_dependency_recovery_proof(
    mutations: dict[str, object], message: str
) -> None:
    proof = {**_dependency_proof(), **mutations}
    with pytest.raises(ValueError, match=message):
        qualify_dependency_recovery_evidence(
            capacity_proof=proof,
            verified_attestation=_dependency_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-2",
        )


@pytest.mark.parametrize(
    "dependency_mutation",
    [
        {"acceptedCount": 1},
        {"errorCount": 1},
        {"conflictCount": 1},
        {"recoverySampleCount": 0},
        {"recoverySuccessRate": 0.0},
    ],
)
def test_dependency_qualification_requires_fault_plus_clean_recovery(
    dependency_mutation: dict[str, object],
) -> None:
    proof = _dependency_proof()
    scenario = dict(proof["scenarios"][0])  # type: ignore[index]
    scenario.update(dependency_mutation)
    proof["scenarios"] = [scenario]

    with pytest.raises(ValueError, match="fault and clean recovery"):
        qualify_dependency_recovery_evidence(
            capacity_proof=proof,
            verified_attestation=_dependency_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-2",
        )


def test_dependency_qualification_rejects_wrong_signer() -> None:
    with pytest.raises(ValueError, match="workflow is not trusted"):
        qualify_dependency_recovery_evidence(
            capacity_proof=_dependency_proof(),
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-2",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"subject_sha256": "invalid"}, "lowercase SHA-256"),
        ({"repository": "other/repo"}, "repository is not trusted"),
        ({"signer_workflow": "other/workflow.yml"}, "workflow is not trusted"),
        ({"source_ref": "refs/heads/feature"}, "refs/heads/main"),
        ({"source_commit_sha": "c" * 40}, "commit does not match"),
    ],
)
def test_rejects_untrusted_or_mismatched_attestation(
    overrides: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=_proof(),
            verified_attestation=_attestation(**overrides),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-1",
        )


def test_rejects_non_main_proof_and_ambiguous_qualification_provenance() -> None:
    proof = _proof()
    proof["branch"] = "feature/capacity"
    with pytest.raises(ValueError, match="originate from main"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=proof,
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-1",
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=_proof(),
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11),
            qualification_run_id="qualification-1",
        )

    with pytest.raises(ValueError, match="qualification_run_id"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=_proof(),
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id=" ",
        )

    invalid_proof = _proof()
    invalid_proof["claimPosture"] = "production_certified"
    with pytest.raises(ValueError, match="claimPosture"):
        qualify_postgres_capacity_threshold_evidence(
            threshold_proof=invalid_proof,
            verified_attestation=_attestation(),
            generated_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
            qualification_run_id="qualification-1",
        )
