from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.application.postgres_capacity_threshold_proof import (
    validate_postgres_capacity_threshold_proof,
)


SCHEMA_VERSION = "lotus-idea.capacity-evidence-qualification.v1"
TRUSTED_REPOSITORY = "sgajbi/lotus-idea"
TRUSTED_SIGNER_WORKFLOW = "sgajbi/lotus-idea/.github/workflows/postgres-capacity-evidence.yml"
TRUSTED_SOURCE_REF = "refs/heads/main"


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
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    if not qualification_run_id.strip():
        raise ValueError("qualification_run_id must not be blank")
    _validate_attestation(verified_attestation, threshold_proof)
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


def _validate_attestation(
    attestation: VerifiedArtifactAttestation,
    threshold_proof: dict[str, Any],
) -> None:
    if len(attestation.subject_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in attestation.subject_sha256
    ):
        raise ValueError("attestation subject_sha256 must be lowercase SHA-256")
    if attestation.repository != TRUSTED_REPOSITORY:
        raise ValueError("capacity evidence attestation repository is not trusted")
    if attestation.signer_workflow != TRUSTED_SIGNER_WORKFLOW:
        raise ValueError("capacity evidence signer workflow is not trusted")
    if attestation.source_ref != TRUSTED_SOURCE_REF:
        raise ValueError("capacity evidence must be attested from refs/heads/main")
    if attestation.source_commit_sha != threshold_proof.get("commitSha"):
        raise ValueError("capacity evidence attestation commit does not match threshold proof")
    if threshold_proof.get("branch") != "main":
        raise ValueError("capacity threshold proof must originate from main")
