from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


WORKBENCH_READ_PATH_PROOF_ENV = "LOTUS_IDEA_WORKBENCH_READ_PATH_PROOF"
WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION = "lotus-idea.workbench-read-path-proof.v1"

REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS = (
    "README.md",
    "REPOSITORY-ENGINEERING-CONTEXT.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-11-workbench-product-realization.md",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-17-implementation-proof-and-live-validation.md",
    "wiki/Supported-Features.md",
    "make workbench-read-path-proof-contract-gate",
    "make implementation-proof-readiness-check",
)

REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS = (
    "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
    "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}",
    "lotus-workbench PR #391",
    "lotus-workbench main 56ce0614875e8b6ecd4df259ef14a1631ea8a4ac",
)

REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS = (
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "data_product_certification_missing",
    "supported_feature_promotion_missing",
)


def build_workbench_read_path_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
) -> dict[str, Any]:
    local_evidence_refs = tuple(REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS)
    file_evidence_present = _required_file_evidence_present(
        repository_root=repository_root,
        evidence_refs=local_evidence_refs,
    )
    make_target_evidence_present = _required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=local_evidence_refs,
    )
    proof_valid = (
        generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None
        and file_evidence_present
        and make_target_evidence_present
    )
    return {
        "schemaVersion": WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "workbench_gateway_read_path_contract",
        "proofScope": "bounded_read_only_queue_detail_consumption",
        "workbenchReadPathProofValid": proof_valid,
        "aggregateBlockersCleared": ("workbench_gateway_bff_consumption_proof_missing",),
        "localEvidenceRefs": local_evidence_refs,
        "externalEvidenceRefs": REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": generated_at_utc.tzinfo is not None
            and generated_at_utc.utcoffset() is not None,
            "fileEvidencePresent": file_evidence_present,
            "makeTargetEvidencePresent": make_target_evidence_present,
            "readOnlyQueueRouteRecorded": "lotus-gateway GET /api/v1/ideas/review-queues/advisor",
            "readOnlyDetailRouteRecorded": "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}",
            "workbenchMergedPrRecorded": "lotus-workbench PR #391",
        },
        "remainingCertificationBlockers": REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS,
        "fullWorkbenchProductCertified": False,
        "canonicalDemoRuntimeCertified": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def workbench_read_path_proof_is_valid(payload: Mapping[str, Any]) -> bool:
    if payload.get("schemaVersion") != WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("proofType") != "workbench_gateway_read_path_contract":
        return False
    if payload.get("proofScope") != "bounded_read_only_queue_detail_consumption":
        return False
    if payload.get("workbenchReadPathProofValid") is not True:
        return False
    if payload.get("fullWorkbenchProductCertified") is not False:
        return False
    if payload.get("canonicalDemoRuntimeCertified") is not False:
        return False
    if payload.get("supportedFeaturePromoted") is not False:
        return False
    if payload.get("proofClosed") is not False:
        return False
    if not _is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        return False
    if tuple(payload.get("aggregateBlockersCleared") or ()) != (
        "workbench_gateway_bff_consumption_proof_missing",
    ):
        return False
    if tuple(payload.get("localEvidenceRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("externalEvidenceRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS
    ):
        return False
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        return False
    if proof_checks.get("timezoneAwareGeneratedAtUtc") is not True:
        return False
    if proof_checks.get("fileEvidencePresent") is not True:
        return False
    if proof_checks.get("makeTargetEvidencePresent") is not True:
        return False
    if proof_checks.get("readOnlyQueueRouteRecorded") != (
        "lotus-gateway GET /api/v1/ideas/review-queues/advisor"
    ):
        return False
    if proof_checks.get("readOnlyDetailRouteRecorded") != (
        "lotus-gateway GET /api/v1/ideas/candidates/{candidate_id}"
    ):
        return False
    return proof_checks.get("workbenchMergedPrRecorded") == "lotus-workbench PR #391"


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
    makefile_path = repository_root / "Makefile"
    try:
        makefile_text = makefile_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for ref in evidence_refs:
        if not ref.startswith("make "):
            continue
        target = f"{ref.removeprefix('make ')}:"
        if target not in makefile_text:
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
