from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any


MESH_POLICY_PROOF_ENV = "LOTUS_IDEA_MESH_POLICY_PROOF"
MESH_POLICY_PROOF_SCHEMA_VERSION = "lotus-idea.mesh-policy-proof.v1"

MESH_POLICY_BLOCKERS_CLEARED = (
    "mesh_slo_policy_certification_missing",
    "mesh_access_policy_certification_missing",
    "mesh_evidence_policy_certification_missing",
)

REMAINING_MESH_POLICY_BLOCKERS = (
    "data_mesh_not_certified",
    "producer_products_not_active",
    "certified_runtime_trust_telemetry_missing",
    "platform_source_manifest_inclusion_missing",
    "platform_catalog_inclusion_missing",
    "gateway_workbench_discovery_proof_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_MESH_POLICY_EVIDENCE_REFS = (
    "contracts/domain-data-products/mesh-readiness.v1.json",
    "contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json",
    "contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json",
    "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json",
    "make data-mesh-contract-gate",
    "make mesh-policy-proof-contract-gate",
    "GET /api/v1/data-mesh/readiness",
    "GET /api/v1/implementation-proof/readiness",
)

PRODUCT_ID = "lotus-idea:IdeaCandidate:v1"


def build_mesh_policy_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    readiness = _optional_json(
        repository_root / "contracts/domain-data-products/mesh-readiness.v1.json"
    )
    slo = _optional_json(
        repository_root / "contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json"
    )
    access = _optional_json(
        repository_root / "contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json"
    )
    evidence = _optional_json(
        repository_root
        / "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json"
    )
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_MESH_POLICY_EVIDENCE_REFS,
    )
    readiness_references_policies = _readiness_references_policies(readiness)
    slo_policy_valid = _slo_policy_valid(slo)
    access_policy_valid = _access_policy_valid(access)
    evidence_policy_valid = _evidence_policy_valid(evidence)
    proof_valid = (
        timezone_aware_generated_at_utc
        and file_evidence_present
        and readiness_references_policies
        and slo_policy_valid
        and access_policy_valid
        and evidence_policy_valid
    )
    return {
        "schemaVersion": MESH_POLICY_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "mesh_policy_contract",
        "proofScope": "repo_owned_slo_access_evidence_policy_validation",
        "meshPolicyProofValid": proof_valid,
        "aggregateBlockersCleared": MESH_POLICY_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_MESH_POLICY_EVIDENCE_REFS,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "fileEvidencePresent": file_evidence_present,
            "readinessReferencesPolicies": readiness_references_policies,
            "sloPolicyValid": slo_policy_valid,
            "accessPolicyValid": access_policy_valid,
            "evidencePolicyValid": evidence_policy_valid,
        },
        "remainingCertificationBlockers": REMAINING_MESH_POLICY_BLOCKERS,
        "platformMeshCertified": False,
        "producerProductsActive": False,
        "gatewayWorkbenchDiscoveryCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def mesh_policy_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != MESH_POLICY_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "mesh_policy_contract":
        return False
    if payload.get("proofScope") != "repo_owned_slo_access_evidence_policy_validation":
        return False
    if payload.get("meshPolicyProofValid") is not True:
        return False
    if payload.get("platformMeshCertified") is not False:
        return False
    if payload.get("producerProductsActive") is not False:
        return False
    if payload.get("gatewayWorkbenchDiscoveryCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != MESH_POLICY_BLOCKERS_CLEARED:
        return False
    if tuple(payload.get("evidenceRefs") or ()) != REQUIRED_MESH_POLICY_EVIDENCE_REFS:
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_MESH_POLICY_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return all(
        proof_checks.get(check_name) is True
        for check_name in (
            "timezoneAwareGeneratedAtUtc",
            "fileEvidencePresent",
            "readinessReferencesPolicies",
            "sloPolicyValid",
            "accessPolicyValid",
            "evidencePolicyValid",
        )
    )


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _readiness_references_policies(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    source_of_truth = payload.get("source_of_truth")
    if not isinstance(source_of_truth, Mapping):
        return False
    return (
        source_of_truth.get("slo_policy")
        == "contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json"
        and source_of_truth.get("access_policy")
        == "contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json"
        and source_of_truth.get("evidence_policy")
        == "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json"
    )


def _slo_policy_valid(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    return (
        payload.get("contract_id") == "lotus-mesh-slo-policy"
        and payload.get("product_id") == PRODUCT_ID
        and payload.get("producer_repository") == "lotus-idea"
        and payload.get("freshness", {}).get("violation_severity") == "blocking"
        and payload.get("lineage", {}).get("lineage_materialized_required") is True
        and payload.get("escalation", {}).get("owner_repository") == "lotus-idea"
    )


def _access_policy_valid(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    allowed_consumers = payload.get("allowed_consumers")
    return (
        payload.get("contract_id") == "lotus-mesh-access-policy"
        and payload.get("product_id") == PRODUCT_ID
        and payload.get("producer_repository") == "lotus-idea"
        and payload.get("default_posture") == "restricted"
        and isinstance(allowed_consumers, list)
        and any(
            isinstance(consumer, Mapping)
            and consumer.get("consumer_repository") == "lotus-gateway"
            and {"operator", "advisor"} <= set(consumer.get("roles", ()))
            for consumer in allowed_consumers
        )
        and payload.get("denial_posture", {}).get("operator_visible_state")
        == "restricted_with_reason"
    )


def _evidence_policy_valid(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    required_manifest_sections = payload.get("required_manifest_sections")
    field_access_classes = payload.get("field_access_classes")
    return (
        payload.get("contract_id") == "lotus-mesh-evidence-pack-policy"
        and payload.get("product_id") == PRODUCT_ID
        and payload.get("producer_repository") == "lotus-idea"
        and isinstance(required_manifest_sections, list)
        and "runtime_telemetry" in required_manifest_sections
        and "validation_lanes" in required_manifest_sections
        and isinstance(field_access_classes, Mapping)
        and field_access_classes.get("source_artifacts") == "operator_only"
        and field_access_classes.get("internal_debug") == "internal_only"
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith(("GET ", "POST ", "make ")):
            continue
        if not (repository_root / ref).is_file():
            return False
    return True


def _is_timezone_aware_datetime_text(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None
