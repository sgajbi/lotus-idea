from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.source_authority import (
    SourceAuthoritySource,
    build_source_authority_records,
    source_authority_records_are_valid,
)
from app.application.source_safe_cross_repo_proof import is_timezone_aware_datetime_text
from app.domain.proof_evidence import EvidenceClass


MESH_POLICY_SOURCE_CONTRACT_ENV = "LOTUS_IDEA_MESH_POLICY_SOURCE_CONTRACT_PROOF"
MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION = "lotus-idea.mesh-policy-source-contract.v2"

MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED: tuple[str, ...] = ()

REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS = (
    "mesh_slo_policy_certification_missing",
    "mesh_access_policy_certification_missing",
    "mesh_evidence_policy_certification_missing",
    "data_mesh_not_certified",
    "producer_products_not_active",
    "certified_runtime_trust_telemetry_missing",
    "platform_source_manifest_inclusion_missing",
    "platform_catalog_inclusion_missing",
    "gateway_workbench_discovery_proof_missing",
    "supported_feature_promotion_missing",
)

MESH_POLICY_SOURCE_AUTHORITY_REFS = (
    "contracts/domain-data-products/mesh-readiness.v1.json",
    "contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json",
    "contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json",
    "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json",
)

REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS = (
    *MESH_POLICY_SOURCE_AUTHORITY_REFS,
    "make data-mesh-contract-gate",
    "make mesh-policy-source-contract-proof-gate",
    "GET /api/v1/data-mesh/readiness",
    "GET /api/v1/implementation-proof/readiness",
)

PRODUCT_ID = "lotus-idea:IdeaCandidate:v1"

_SOURCE_CONTRACT_FIELDS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "proofType",
        "proofScope",
        "evidenceClass",
        "sourceContractValid",
        "sourceContractBlockersSatisfied",
        "evidenceRefs",
        "sourceAuthority",
        "contractChecks",
        "remainingCertificationBlockers",
        "policyCertificationObserved",
        "platformMeshCertified",
        "producerProductsActive",
        "gatewayWorkbenchDiscoveryCertified",
        "deploymentObserved",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    }
)

_CONTRACT_CHECK_FIELDS = frozenset(
    {
        "timezoneAwareGeneratedAtUtc",
        "sourceAuthorityDigestBound",
        "readinessReferencesPolicies",
        "sloPolicyValid",
        "accessPolicyValid",
        "evidencePolicyValid",
    }
)


def build_mesh_policy_source_contract_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    timezone_aware_generated_at_utc = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    readiness = _optional_json(repository_root / MESH_POLICY_SOURCE_AUTHORITY_REFS[0])
    slo = _optional_json(repository_root / MESH_POLICY_SOURCE_AUTHORITY_REFS[1])
    access = _optional_json(repository_root / MESH_POLICY_SOURCE_AUTHORITY_REFS[2])
    evidence = _optional_json(repository_root / MESH_POLICY_SOURCE_AUTHORITY_REFS[3])
    source_authority = _source_authority(repository_root)
    source_authority_digest_bound = all(
        isinstance(item["sha256"], str) for item in source_authority
    )
    readiness_references_policies = _readiness_references_policies(readiness)
    slo_policy_valid = _slo_policy_valid(slo)
    access_policy_valid = _access_policy_valid(access)
    evidence_policy_valid = _evidence_policy_valid(evidence)
    source_contract_valid = (
        timezone_aware_generated_at_utc
        and source_authority_digest_bound
        and readiness_references_policies
        and slo_policy_valid
        and access_policy_valid
        and evidence_policy_valid
    )
    return {
        "schemaVersion": MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "mesh_policy_source_contract",
        "proofScope": "repo_owned_slo_access_and_evidence_policy_sources",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": source_contract_valid,
        "sourceContractBlockersSatisfied": MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED,
        "evidenceRefs": REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS,
        "sourceAuthority": source_authority,
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": timezone_aware_generated_at_utc,
            "sourceAuthorityDigestBound": source_authority_digest_bound,
            "readinessReferencesPolicies": readiness_references_policies,
            "sloPolicyValid": slo_policy_valid,
            "accessPolicyValid": access_policy_valid,
            "evidencePolicyValid": evidence_policy_valid,
        },
        "remainingCertificationBlockers": REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS,
        "policyCertificationObserved": False,
        "platformMeshCertified": False,
        "producerProductsActive": False,
        "gatewayWorkbenchDiscoveryCertified": False,
        "deploymentObserved": False,
        "productionCertificationGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }


def mesh_policy_source_contract_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (
        _SOURCE_CONTRACT_FIELDS,
        _SOURCE_CONTRACT_FIELDS | {AGGREGATE_PROOF_PROVENANCE_KEY},
    ):
        return False
    if payload.get("schemaVersion") != MESH_POLICY_SOURCE_CONTRACT_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "mesh_policy_source_contract":
        return False
    if payload.get("proofScope") != "repo_owned_slo_access_and_evidence_policy_sources":
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("sourceContractValid") is not True:
        return False
    for false_claim in (
        "policyCertificationObserved",
        "platformMeshCertified",
        "producerProductsActive",
        "gatewayWorkbenchDiscoveryCertified",
        "deploymentObserved",
        "productionCertificationGranted",
        "supportedFeaturePromoted",
        "certificationClosed",
    ):
        if payload.get(false_claim) is not False:
            return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("sourceContractBlockersSatisfied") or ()) != (
        MESH_POLICY_SOURCE_CONTRACT_BLOCKERS_SATISFIED
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != (
        REQUIRED_MESH_POLICY_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_MESH_POLICY_CERTIFICATION_BLOCKERS
    ):
        return False
    if not _source_authority_is_valid(payload.get("sourceAuthority")):
        return False
    contract_checks = payload.get("contractChecks")
    if not isinstance(contract_checks, Mapping) or set(contract_checks) != _CONTRACT_CHECK_FIELDS:
        return False
    return all(contract_checks.get(check_name) is True for check_name in _CONTRACT_CHECK_FIELDS)


def _source_authority(repository_root: Path) -> tuple[dict[str, str | None], ...]:
    return build_source_authority_records(_source_authority_sources(repository_root))


def _source_authority_is_valid(value: object) -> bool:
    return source_authority_records_are_valid(
        value,
        expected_sources=_source_authority_sources(Path()),
    )


def _source_authority_sources(repository_root: Path) -> tuple[SourceAuthoritySource, ...]:
    return tuple(
        SourceAuthoritySource("lotus-idea", ref, repository_root / ref)
        for ref in MESH_POLICY_SOURCE_AUTHORITY_REFS
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
        source_of_truth.get("slo_policy") == MESH_POLICY_SOURCE_AUTHORITY_REFS[1]
        and source_of_truth.get("access_policy") == MESH_POLICY_SOURCE_AUTHORITY_REFS[2]
        and source_of_truth.get("evidence_policy") == MESH_POLICY_SOURCE_AUTHORITY_REFS[3]
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
