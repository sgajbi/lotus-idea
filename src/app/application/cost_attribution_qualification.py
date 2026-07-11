from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any


PLATFORM_ARTIFACT_SCHEMA_VERSION = "lotus-platform.service-cost-attribution.v1"
QUALIFICATION_SCHEMA_VERSION = "lotus-idea.platform-cost-attribution-qualification.v1"
TRUSTED_REPOSITORY = "sgajbi/lotus-platform"
TRUSTED_SIGNER_WORKFLOW = (
    "sgajbi/lotus-platform/.github/workflows/service-cost-attribution-evidence.yml"
)
TRUSTED_SOURCE_REF = "refs/heads/main"
RESOURCE_SCHEMA_VERSION = "lotus-idea.service-resource-baseline.v1"


@dataclass(frozen=True)
class VerifiedPlatformCostAttestation:
    subject_sha256: str
    repository: str
    signer_workflow: str
    source_ref: str
    source_commit_sha: str


def qualify_platform_cost_attribution(
    *,
    artifact: dict[str, Any],
    attestation: VerifiedPlatformCostAttestation,
    resource_qualification: dict[str, Any],
    generated_at_utc: datetime,
    qualification_run_id: str,
) -> dict[str, Any]:
    _validate_platform_artifact(artifact)
    if generated_at_utc.tzinfo is None or generated_at_utc.utcoffset() is None:
        raise ValueError("generated_at_utc must be timezone-aware")
    if not qualification_run_id.strip():
        raise ValueError("qualification_run_id must not be blank")
    _validate_attestation(artifact, attestation)
    _validate_resource_binding(artifact, resource_qualification)
    return {
        "schemaVersion": QUALIFICATION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "proofScope": "verified_platform_cost_attribution_binding",
        "claimPosture": "platform_cost_attribution_verified",
        "generatedAtUtc": generated_at_utc.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "qualificationRunId": qualification_run_id,
        "platformArtifactSha256": attestation.subject_sha256,
        "platformSourceCommitSha": attestation.source_commit_sha,
        "platformSourceRef": attestation.source_ref,
        "platformSignerWorkflow": attestation.signer_workflow,
        "resourceProofRunId": resource_qualification["resourceProofRunId"],
        "resourceProofSha256": resource_qualification["resourceProofSha256"],
        "billingPeriod": artifact["billingPeriod"],
        "currency": artifact["currency"],
        "costAttributionVerified": True,
        "productionCapacityCertified": False,
        "supportedFeaturePromoted": False,
    }


def _validate_platform_artifact(artifact: dict[str, Any]) -> None:
    expected = {
        "schemaVersion": PLATFORM_ARTIFACT_SCHEMA_VERSION,
        "repository": "lotus-platform",
        "proofScope": "source_safe_service_cost_attribution",
        "claimPosture": "reconciled_not_attested",
        "costAttributionReconciled": True,
        "costAttributionCertified": False,
        "supportedFeaturePromoted": False,
    }
    for name, value in expected.items():
        if artifact.get(name) != value:
            raise ValueError(f"platform cost-attribution {name} is invalid")
    if artifact.get("certificationBlockers") != ["artifact_attestation_missing"]:
        raise ValueError("platform cost-attribution blockers are inconsistent")
    service = artifact.get("service")
    if not isinstance(service, dict) or service.get("repository") != "lotus-idea":
        raise ValueError("platform cost-attribution service repository must be lotus-idea")
    if service.get("serviceId") != "lotus-idea-api":
        raise ValueError("platform cost-attribution service id must be lotus-idea-api")
    if service.get("environment") not in {"production-like", "production"}:
        raise ValueError("platform cost-attribution environment is not qualifying")
    currency = artifact.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("platform cost-attribution currency is invalid")
    for name in ("provenance", "resourceObservation", "billingPeriod"):
        if not isinstance(artifact.get(name), dict):
            raise ValueError(f"platform cost-attribution {name} must be an object")


def _validate_attestation(
    artifact: dict[str, Any], attestation: VerifiedPlatformCostAttestation
) -> None:
    if len(attestation.subject_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in attestation.subject_sha256
    ):
        raise ValueError("platform cost-attribution subject digest must be lowercase SHA-256")
    if attestation.repository != TRUSTED_REPOSITORY:
        raise ValueError("platform cost-attribution repository is not trusted")
    if attestation.signer_workflow != TRUSTED_SIGNER_WORKFLOW:
        raise ValueError("platform cost-attribution signer workflow is not trusted")
    if attestation.source_ref != TRUSTED_SOURCE_REF:
        raise ValueError("platform cost-attribution must originate from refs/heads/main")
    provenance = artifact["provenance"]
    if provenance.get("sourceRef") != TRUSTED_SOURCE_REF:
        raise ValueError("platform cost-attribution artifact source ref must be refs/heads/main")
    if provenance.get("sourceCommitSha") != attestation.source_commit_sha:
        raise ValueError("platform cost-attribution attestation commit does not match artifact")


def _validate_resource_binding(
    artifact: dict[str, Any], resource_qualification: dict[str, Any]
) -> None:
    resource = artifact["resourceObservation"]
    if resource.get("schemaVersion") != RESOURCE_SCHEMA_VERSION:
        raise ValueError("platform cost-attribution resource schema is not trusted")
    if resource.get("sha256") != resource_qualification.get("resourceProofSha256"):
        raise ValueError("platform cost-attribution resource digest does not match Idea proof")
    if resource.get("runId") != resource_qualification.get("resourceProofRunId"):
        raise ValueError("platform cost-attribution resource run does not match Idea proof")
    if resource_qualification.get("attestationVerified") is not True:
        raise ValueError("Idea resource qualification must be attested")
