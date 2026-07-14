from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.domain.proof_evidence import EvidenceClass
from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.application.workbench_read_path_proof import (
    WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
    workbench_read_path_proof_is_valid,
)


_is_timezone_aware_datetime_text = is_timezone_aware_datetime_text
_required_file_evidence_present = required_file_evidence_present
_required_make_target_evidence_present = required_make_target_evidence_present

GATEWAY_WORKBENCH_CONTRACT_PROOF_ENV = "LOTUS_IDEA_GATEWAY_WORKBENCH_CONTRACT_PROOF"
GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION = "lotus-idea.gateway-workbench-contract-proof.v2"

GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED: tuple[str, ...] = ()

REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS = (
    "src/app/application/workbench/contract_proof.py",
    "scripts/workbench/generate_contract_proof.py",
    "scripts/workbench/contract_proof_gate.py",
    "src/app/application/workbench_read_path_proof.py",
    "scripts/generate_workbench_read_path_proof.py",
    "scripts/workbench_read_path_proof_contract_gate.py",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-11-workbench-product-realization.md",
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Supported-Features.md",
    "make workbench-read-path-proof-contract-gate",
    "make gateway-workbench-contract-proof-contract-gate",
    "make implementation-proof-readiness-check",
)

REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS = (
    "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
    "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}",
)

REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS = (
    "gateway_workbench_proof_missing",
    "workbench_product_proof_missing",
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "gateway_workbench_discovery_proof_missing",
    "data_product_certification_missing",
    "supported_feature_promotion_missing",
)


def build_gateway_workbench_contract_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    workbench_read_path_proof: Mapping[str, Any] | None,
    workbench_read_path_proof_ref: str | None,
) -> dict[str, Any]:
    local_evidence_refs = REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS
    workbench_read_path_valid = bool(
        workbench_read_path_proof and workbench_read_path_proof_is_valid(workbench_read_path_proof)
    )
    proof_valid = (
        generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None
        and _required_file_evidence_present(
            repository_root=repository_root,
            sibling_roots={},
            evidence_refs=local_evidence_refs,
            non_file_ref_prefixes=("make ",),
        )
        and _required_make_target_evidence_present(
            repository_root=repository_root,
            evidence_refs=local_evidence_refs,
        )
        and workbench_read_path_valid
    )
    return {
        "schemaVersion": GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "gateway_workbench_contract",
        "proofScope": "source_contract_declaration",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "gatewayWorkbenchContractProofValid": proof_valid,
        "aggregateBlockersCleared": GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED,
        "workbenchReadPathProofSchemaVersion": WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
        "workbenchReadPathProofRef": workbench_read_path_proof_ref,
        "localEvidenceRefs": local_evidence_refs,
        "declaredRouteRefs": REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": generated_at_utc.tzinfo is not None
            and generated_at_utc.utcoffset() is not None,
            "fileEvidencePresent": _required_file_evidence_present(
                repository_root=repository_root,
                sibling_roots={},
                evidence_refs=local_evidence_refs,
                non_file_ref_prefixes=("make ",),
            ),
            "makeTargetEvidencePresent": _required_make_target_evidence_present(
                repository_root=repository_root,
                evidence_refs=local_evidence_refs,
            ),
            "workbenchReadPathProofValid": workbench_read_path_valid,
            "readOnlyQueueRouteDeclared": "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
            "readOnlyDetailRouteDeclared": (
                "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}"
            ),
        },
        "remainingCertificationBlockers": REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS,
        "sourceIngestionSupported": False,
        "outboxDeliverySupported": False,
        "fullWorkbenchProductCertified": False,
        "gatewayWorkbenchDiscoveryCertified": False,
        "canonicalDemoRuntimeCertified": False,
        "runtimeExecutionObserved": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def gateway_workbench_contract_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != GATEWAY_WORKBENCH_CONTRACT_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "gateway_workbench_contract":
        return False
    if payload.get("proofScope") != "source_contract_declaration":
        return False
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        return False
    if payload.get("gatewayWorkbenchContractProofValid") is not True:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_CONTRACT_BLOCKERS_CLEARED
    ):
        return False
    if payload.get("workbenchReadPathProofSchemaVersion") != (
        WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION
    ):
        return False
    if not isinstance(payload.get("workbenchReadPathProofRef"), str):
        return False
    if tuple(payload.get("localEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_CONTRACT_LOCAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("declaredRouteRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_CONTRACT_ROUTE_DECLARATIONS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_GATEWAY_WORKBENCH_CONTRACT_BLOCKERS
    ):
        return False
    if payload.get("sourceIngestionSupported") is not False:
        return False
    if payload.get("outboxDeliverySupported") is not False:
        return False
    if payload.get("fullWorkbenchProductCertified") is not False:
        return False
    if payload.get("gatewayWorkbenchDiscoveryCertified") is not False:
        return False
    if payload.get("canonicalDemoRuntimeCertified") is not False:
        return False
    if payload.get("runtimeExecutionObserved") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    return (
        proof_checks.get("timezoneAwareGeneratedAtUtc") is True
        and proof_checks.get("fileEvidencePresent") is True
        and proof_checks.get("makeTargetEvidencePresent") is True
        and proof_checks.get("workbenchReadPathProofValid") is True
        and proof_checks.get("readOnlyQueueRouteDeclared")
        == "lotus-gateway GET /api/v1/ideas/review-queues/advisor"
        and proof_checks.get("readOnlyDetailRouteDeclared")
        == "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}"
    )
