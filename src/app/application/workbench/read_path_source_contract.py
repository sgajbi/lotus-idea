from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.domain.proof_evidence import EvidenceClass


WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV = (
    "LOTUS_IDEA_WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF"
)
WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION = (
    "lotus-idea.workbench-read-path-source-contract-proof.v2"
)
WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED: tuple[str, ...] = ()

REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS = (
    "src/app/application/workbench/read_path_source_contract.py",
    "scripts/workbench/generate_read_path_source_contract.py",
    "scripts/workbench/read_path_source_contract_gate.py",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-11-workbench-product-realization.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-17-implementation-proof-and-live-validation.md",
    "wiki/Supported-Features.md",
    "make workbench-read-path-source-contract-proof-gate",
    "make implementation-proof-readiness-check",
)

REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS = (
    "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
    "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}",
)

REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS = (
    "workbench_gateway_bff_consumption_proof_missing",
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "data_product_certification_missing",
    "supported_feature_promotion_missing",
)


def build_workbench_read_path_source_contract_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    local_evidence_refs = REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS
    file_evidence_present = required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=local_evidence_refs,
        non_file_ref_prefixes=("make ",),
    )
    make_target_evidence_present = required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=local_evidence_refs,
    )
    timestamp_valid = (
        generated_at_utc.tzinfo is not None and generated_at_utc.utcoffset() is not None
    )
    proof_valid = timestamp_valid and file_evidence_present and make_target_evidence_present
    return {
        "schemaVersion": WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "workbench_gateway_read_path_source_contract",
        "proofScope": "bounded_read_only_queue_detail_declaration",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "workbenchReadPathSourceContractValid": proof_valid,
        "aggregateBlockersCleared": WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED,
        "localEvidenceRefs": local_evidence_refs,
        "declaredRouteRefs": REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": timestamp_valid,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "readOnlyQueueRouteDeclared": REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS[0],
            "readOnlyDetailRouteDeclared": REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS[1],
        },
        "remainingCertificationBlockers": REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS,
        "gatewayServingObserved": False,
        "workbenchConsumptionObserved": False,
        "entitlementEnforcementObserved": False,
        "runtimeExecutionObserved": False,
        "browserAccessibilityCertified": False,
        "canonicalDemoRuntimeCertified": False,
        "fullWorkbenchProductCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def workbench_read_path_source_contract_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "workbench_gateway_read_path_source_contract":
        return False
    if payload.get("proofScope") != "bounded_read_only_queue_detail_declaration":
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("workbenchReadPathSourceContractValid") is not True:
        return False
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        return False
    if tuple(payload.get("localEvidenceRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_SOURCE_CONTRACT_LOCAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("declaredRouteRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS
    ):
        return False
    if any(
        payload.get(field) is not False
        for field in (
            "gatewayServingObserved",
            "workbenchConsumptionObserved",
            "entitlementEnforcementObserved",
            "runtimeExecutionObserved",
            "browserAccessibilityCertified",
            "canonicalDemoRuntimeCertified",
            "fullWorkbenchProductCertified",
            "supportedFeaturePromoted",
            "proofClosed",
        )
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return (
        proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("fileEvidencePresent") is True
        and proof_checks.get("makeTargetEvidencePresent") is True
        and proof_checks.get("readOnlyQueueRouteDeclared")
        == REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS[0]
        and proof_checks.get("readOnlyDetailRouteDeclared")
        == REQUIRED_WORKBENCH_READ_PATH_ROUTE_DECLARATIONS[1]
    )
