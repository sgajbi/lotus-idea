from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from app.application.workbench_read_path_proof import (
    WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
    workbench_read_path_proof_is_valid,
)


GATEWAY_WORKBENCH_OPERATIONAL_PROOF_ENV = "LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF"
GATEWAY_WORKBENCH_OPERATIONAL_PROOF_SCHEMA_VERSION = (
    "lotus-idea.gateway-workbench-operational-proof.v1"
)

GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS_CLEARED = ("gateway_workbench_proof_missing",)

REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_LOCAL_EVIDENCE_REFS = (
    "src/app/application/workbench_read_path_proof.py",
    "scripts/generate_workbench_read_path_proof.py",
    "scripts/workbench_read_path_proof_contract_gate.py",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-11-workbench-product-realization.md",
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Supported-Features.md",
    "make workbench-read-path-proof-contract-gate",
    "make gateway-workbench-operational-proof-contract-gate",
    "make implementation-proof-readiness-check",
)

REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_EXTERNAL_EVIDENCE_REFS = (
    "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
    "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}",
    "lotus-workbench PR #391",
    "lotus-workbench main 56ce0614875e8b6ecd4df259ef14a1631ea8a4ac",
)

REMAINING_GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS = (
    "workbench_product_proof_missing",
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "gateway_workbench_discovery_proof_missing",
    "data_product_certification_missing",
    "supported_feature_promotion_missing",
)


def build_gateway_workbench_operational_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    workbench_read_path_proof: Mapping[str, Any] | None,
    workbench_read_path_proof_ref: str | None,
) -> dict[str, Any]:
    local_evidence_refs = REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_LOCAL_EVIDENCE_REFS
    workbench_read_path_valid = bool(
        workbench_read_path_proof and workbench_read_path_proof_is_valid(workbench_read_path_proof)
    )
    proof_valid = (
        generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None
        and _required_file_evidence_present(
            repository_root=repository_root,
            evidence_refs=local_evidence_refs,
        )
        and _required_make_target_evidence_present(
            repository_root=repository_root,
            evidence_refs=local_evidence_refs,
        )
        and workbench_read_path_valid
    )
    return {
        "schemaVersion": GATEWAY_WORKBENCH_OPERATIONAL_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "gateway_workbench_operational_contract",
        "proofScope": "bounded_queue_detail_gateway_bff_consumption",
        "gatewayWorkbenchOperationalProofValid": proof_valid,
        "aggregateBlockersCleared": GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS_CLEARED,
        "workbenchReadPathProofSchemaVersion": WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
        "workbenchReadPathProofRef": workbench_read_path_proof_ref,
        "localEvidenceRefs": local_evidence_refs,
        "externalEvidenceRefs": REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_EXTERNAL_EVIDENCE_REFS,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": generated_at_utc.tzinfo is not None
            and generated_at_utc.utcoffset() is not None,
            "fileEvidencePresent": _required_file_evidence_present(
                repository_root=repository_root,
                evidence_refs=local_evidence_refs,
            ),
            "makeTargetEvidencePresent": _required_make_target_evidence_present(
                repository_root=repository_root,
                evidence_refs=local_evidence_refs,
            ),
            "workbenchReadPathProofValid": workbench_read_path_valid,
            "readOnlyQueueRouteRecorded": "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
            "readOnlyDetailRouteRecorded": (
                "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}"
            ),
        },
        "remainingCertificationBlockers": REMAINING_GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS,
        "sourceIngestionSupported": False,
        "outboxDeliverySupported": False,
        "fullWorkbenchProductCertified": False,
        "gatewayWorkbenchDiscoveryCertified": False,
        "canonicalDemoRuntimeCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def gateway_workbench_operational_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != GATEWAY_WORKBENCH_OPERATIONAL_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "gateway_workbench_operational_contract":
        return False
    if payload.get("proofScope") != "bounded_queue_detail_gateway_bff_consumption":
        return False
    if payload.get("gatewayWorkbenchOperationalProofValid") is not True:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS_CLEARED
    ):
        return False
    if payload.get("workbenchReadPathProofSchemaVersion") != (
        WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION
    ):
        return False
    if not isinstance(payload.get("workbenchReadPathProofRef"), str):
        return False
    if tuple(payload.get("localEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_LOCAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("externalEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_EXTERNAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS
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
        and proof_checks.get("readOnlyQueueRouteRecorded")
        == "lotus-gateway GET /api/v1/ideas/review-queues/advisor"
        and proof_checks.get("readOnlyDetailRouteRecorded")
        == "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}"
    )


def _required_file_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    for ref in evidence_refs:
        if ref.startswith("make "):
            continue
        if not (repository_root / ref).is_file():
            return False
    return True


def _required_make_target_evidence_present(
    *,
    repository_root: Path,
    evidence_refs: tuple[str, ...],
) -> bool:
    try:
        makefile_text = (repository_root / "Makefile").read_text(encoding="utf-8")
    except OSError:
        return False
    for ref in evidence_refs:
        if not ref.startswith("make "):
            continue
        if f"{ref.removeprefix('make ')}:" not in makefile_text:
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
