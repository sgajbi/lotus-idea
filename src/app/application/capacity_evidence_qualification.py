from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.application.postgres_capacity_threshold_proof import (
    validate_postgres_capacity_threshold_proof,
)
from app.application.service_resource_baseline import validate_service_resource_baseline


SCHEMA_VERSION = "lotus-idea.capacity-evidence-qualification.v1"
TRUSTED_REPOSITORY = "sgajbi/lotus-idea"
POSTGRES_CAPACITY_SIGNER_WORKFLOW = (
    "sgajbi/lotus-idea/.github/workflows/postgres-capacity-evidence.yml"
)
DEPENDENCY_RECOVERY_SIGNER_WORKFLOW = (
    "sgajbi/lotus-idea/.github/workflows/service-dependency-recovery-evidence.yml"
)
LOAD_SOAK_SIGNER_WORKFLOW = "sgajbi/lotus-idea/.github/workflows/service-load-soak-evidence.yml"
RESOURCE_SIGNER_WORKFLOW = LOAD_SOAK_SIGNER_WORKFLOW
TRUSTED_SIGNER_WORKFLOW = POSTGRES_CAPACITY_SIGNER_WORKFLOW
TRUSTED_SOURCE_REF = "refs/heads/main"
MINIMUM_LOAD_SOAK_SAMPLES = 1_000
MINIMUM_LOAD_SOAK_SECONDS = 3_600.0
MINIMUM_RESOURCE_SAMPLES = 61
MINIMUM_RESOURCE_SECONDS = 3_600.0
LOAD_SOAK_SCENARIO_THRESHOLDS = {
    "api": (0.001, 0.5, 1.5),
    "source_ingestion": (0.01, 300.0, 600.0),
    "outbox_delivery": (0.001, 60.0, 300.0),
    "downstream_submission": (0.01, 2.0, 5.0),
    "postgresql": (0.001, 0.1, 0.5),
}


@dataclass(frozen=True)
class VerifiedArtifactAttestation:
    subject_sha256: str
    repository: str
    signer_workflow: str
    source_ref: str
    source_commit_sha: str


def qualify_postgres_capacity_threshold_evidence(
    *,
    threshold_proof: dict[str, Any],
    verified_attestation: VerifiedArtifactAttestation,
    generated_at_utc: datetime,
    qualification_run_id: str,
) -> dict[str, Any]:
    proof_errors = validate_postgres_capacity_threshold_proof(threshold_proof)
    if proof_errors:
        raise ValueError("; ".join(proof_errors))
    _validate_qualification_inputs(generated_at_utc, qualification_run_id)
    _validate_attestation(
        verified_attestation,
        threshold_proof,
        trusted_signer_workflow=POSTGRES_CAPACITY_SIGNER_WORKFLOW,
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "attested_postgres_capacity_threshold_environment_qualification",
        "claimPosture": "production_like_environment_qualified",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "qualificationRunId": qualification_run_id,
        "thresholdProofRunId": threshold_proof["runId"],
        "thresholdProofSha256": verified_attestation.subject_sha256,
        "commitSha": verified_attestation.source_commit_sha,
        "sourceRef": verified_attestation.source_ref,
        "signerWorkflow": verified_attestation.signer_workflow,
        "attestationRepository": verified_attestation.repository,
        "attestationVerified": True,
        "environmentProfile": "production-like",
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def qualify_dependency_recovery_evidence(
    *,
    capacity_proof: dict[str, Any],
    verified_attestation: VerifiedArtifactAttestation,
    generated_at_utc: datetime,
    qualification_run_id: str,
) -> dict[str, Any]:
    _validate_qualification_inputs(generated_at_utc, qualification_run_id)
    _validate_dependency_recovery_proof(capacity_proof)
    _validate_attestation(
        verified_attestation,
        capacity_proof,
        trusted_signer_workflow=DEPENDENCY_RECOVERY_SIGNER_WORKFLOW,
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "attested_dependency_recovery_environment_qualification",
        "claimPosture": "production_like_environment_qualified",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "qualificationRunId": qualification_run_id,
        "capacityProofRunId": capacity_proof["runId"],
        "capacityProofSha256": verified_attestation.subject_sha256,
        "commitSha": verified_attestation.source_commit_sha,
        "sourceRef": verified_attestation.source_ref,
        "signerWorkflow": verified_attestation.signer_workflow,
        "attestationRepository": verified_attestation.repository,
        "attestationVerified": True,
        "environmentProfile": "production-like",
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def qualify_load_soak_evidence(
    *,
    capacity_proof: dict[str, Any],
    verified_attestation: VerifiedArtifactAttestation,
    generated_at_utc: datetime,
    qualification_run_id: str,
) -> dict[str, Any]:
    _validate_qualification_inputs(generated_at_utc, qualification_run_id)
    validate_load_soak_proof(capacity_proof)
    _validate_attestation(
        verified_attestation,
        capacity_proof,
        trusted_signer_workflow=LOAD_SOAK_SIGNER_WORKFLOW,
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "attested_service_load_soak_environment_qualification",
        "claimPosture": "production_like_environment_qualified",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "qualificationRunId": qualification_run_id,
        "capacityProofRunId": capacity_proof["runId"],
        "capacityProofSha256": verified_attestation.subject_sha256,
        "commitSha": verified_attestation.source_commit_sha,
        "sourceRef": verified_attestation.source_ref,
        "signerWorkflow": verified_attestation.signer_workflow,
        "attestationRepository": verified_attestation.repository,
        "attestationVerified": True,
        "environmentProfile": "production-like",
        "qualifiedScenarios": list(LOAD_SOAK_SCENARIO_THRESHOLDS),
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def qualify_resource_evidence(
    *,
    resource_proof: dict[str, Any],
    verified_attestation: VerifiedArtifactAttestation,
    generated_at_utc: datetime,
    qualification_run_id: str,
) -> dict[str, Any]:
    _validate_qualification_inputs(generated_at_utc, qualification_run_id)
    validate_resource_proof(resource_proof)
    _validate_attestation(
        verified_attestation,
        resource_proof,
        trusted_signer_workflow=RESOURCE_SIGNER_WORKFLOW,
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "attested_process_resource_environment_qualification",
        "claimPosture": "production_like_environment_qualified",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "qualificationRunId": qualification_run_id,
        "resourceProofRunId": resource_proof["runId"],
        "resourceProofSha256": verified_attestation.subject_sha256,
        "commitSha": verified_attestation.source_commit_sha,
        "sourceRef": verified_attestation.source_ref,
        "signerWorkflow": verified_attestation.signer_workflow,
        "attestationRepository": verified_attestation.repository,
        "attestationVerified": True,
        "environmentProfile": "production-like",
        "costAttributionVerified": False,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def _validate_attestation(
    attestation: VerifiedArtifactAttestation,
    proof: dict[str, Any],
    *,
    trusted_signer_workflow: str,
) -> None:
    if len(attestation.subject_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in attestation.subject_sha256
    ):
        raise ValueError("attestation subject_sha256 must be lowercase SHA-256")
    if attestation.repository != TRUSTED_REPOSITORY:
        raise ValueError("capacity evidence attestation repository is not trusted")
    if attestation.signer_workflow != trusted_signer_workflow:
        raise ValueError("capacity evidence signer workflow is not trusted")
    if attestation.source_ref != TRUSTED_SOURCE_REF:
        raise ValueError("capacity evidence must be attested from refs/heads/main")
    if attestation.source_commit_sha != proof.get("commitSha"):
        raise ValueError("capacity evidence attestation commit does not match threshold proof")
    if proof.get("branch") != "main":
        raise ValueError("capacity threshold proof must originate from main")


def _validate_qualification_inputs(generated_at_utc: datetime, qualification_run_id: str) -> None:
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    if not qualification_run_id.strip():
        raise ValueError("qualification_run_id must not be blank")


def _validate_dependency_recovery_proof(proof: dict[str, Any]) -> None:
    _validate_capacity_proof_header(proof, proof_name="dependency recovery proof")
    scenarios = proof.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("dependency recovery proof scenarios must be a list")
    dependency = next(
        (
            scenario
            for scenario in scenarios
            if isinstance(scenario, dict) and scenario.get("scenario") == "dependency_failure"
        ),
        None,
    )
    if dependency is None:
        raise ValueError("dependency recovery proof scenario is missing")
    recovery_count = dependency.get("recoverySampleCount")
    accepted_count = dependency.get("acceptedCount")
    if (
        not isinstance(recovery_count, int)
        or isinstance(recovery_count, bool)
        or recovery_count < 1
        or not isinstance(accepted_count, int)
        or isinstance(accepted_count, bool)
        or accepted_count <= recovery_count
        or dependency.get("recoverySuccessRate") != 1.0
        or dependency.get("errorCount") != 0
        or dependency.get("conflictCount") != 0
    ):
        raise ValueError("dependency recovery proof does not show fault and clean recovery")


def validate_load_soak_proof(proof: dict[str, Any]) -> None:
    _validate_capacity_proof_header(proof, proof_name="load soak proof")
    observed_window = proof.get("observedWindowSeconds")
    if (
        isinstance(observed_window, bool)
        or not isinstance(observed_window, (int, float))
        or observed_window < MINIMUM_LOAD_SOAK_SECONDS
    ):
        raise ValueError("load soak proof does not meet the minimum observation window")
    scenarios = proof.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("load soak proof scenarios must be a list")
    indexed = {
        scenario.get("scenario"): scenario for scenario in scenarios if isinstance(scenario, dict)
    }
    for scenario_name, thresholds in LOAD_SOAK_SCENARIO_THRESHOLDS.items():
        scenario = indexed.get(scenario_name)
        if not isinstance(scenario, dict):
            raise ValueError(f"load soak proof scenario {scenario_name} is missing")
        _validate_load_soak_scenario(scenario_name, scenario, thresholds)


def validate_resource_proof(proof: dict[str, Any]) -> None:
    errors = validate_service_resource_baseline(proof)
    if errors:
        raise ValueError("; ".join(errors))
    sample_count = proof.get("sampleCount")
    observed_window = proof.get("observedWindowSeconds")
    if proof.get("environmentProfile") != "production-like":
        raise ValueError("resource proof must be production-like")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < MINIMUM_RESOURCE_SAMPLES
    ):
        raise ValueError("resource proof does not meet the minimum sample count")
    if (
        isinstance(observed_window, bool)
        or not isinstance(observed_window, (int, float))
        or observed_window < MINIMUM_RESOURCE_SECONDS
    ):
        raise ValueError("resource proof does not meet the minimum observation window")


def _validate_load_soak_scenario(
    scenario_name: str,
    scenario: dict[str, Any],
    thresholds: tuple[float, float, float],
) -> None:
    error_budget, latency_p95, latency_p99 = thresholds
    sample_count = scenario.get("sampleCount")
    error_rate = scenario.get("errorRate")
    observed_p95 = scenario.get("latencyP95Seconds")
    observed_p99 = scenario.get("latencyP99Seconds")
    observation_span = scenario.get("observationSpanSeconds")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count < MINIMUM_LOAD_SOAK_SAMPLES
        or scenario.get("conflictCount") != 0
        or isinstance(error_rate, bool)
        or not isinstance(error_rate, (int, float))
        or isinstance(observed_p95, bool)
        or not isinstance(observed_p95, (int, float))
        or isinstance(observed_p99, bool)
        or not isinstance(observed_p99, (int, float))
        or isinstance(observation_span, bool)
        or not isinstance(observation_span, (int, float))
        or observation_span < MINIMUM_LOAD_SOAK_SECONDS
        or error_rate > error_budget
        or observed_p95 > latency_p95
        or observed_p99 > latency_p99
    ):
        raise ValueError(f"load soak proof scenario {scenario_name} breaches qualification")


def _validate_capacity_proof_header(proof: dict[str, Any], *, proof_name: str) -> None:
    if proof.get("schemaVersion") != "lotus-idea.service-capacity-baseline.v1":
        raise ValueError(f"{proof_name} schemaVersion is not supported")
    if proof.get("proofScope") != "source_safe_service_capacity_baseline":
        raise ValueError(f"{proof_name} must remain source-safe")
    if proof.get("claimPosture") != "report_only_baseline":
        raise ValueError(f"{proof_name} must remain report_only_baseline")
    if proof.get("environmentProfile") != "production-like":
        raise ValueError(f"{proof_name} must be production-like")
    if proof.get("supportedFeaturePromoted") is not False:
        raise ValueError(f"{proof_name} must not promote supported features")
