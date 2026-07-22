from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.domain.proof_evidence import EvidenceClass


OWNER_MAINLINE_EVIDENCE_CONTRACT_REF = (
    "contracts/implementation-proof/rfc0002-slice11-owner-mainline-evidence.v1.json"
)
OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION = "lotus-idea.rfc0002.slice11-owner-mainline-evidence.v1"

OWNER_MAINLINE_EVIDENCE_SLICE_IDS = (
    "RFC-0002/slice-11",
    "RFC-0002/slice-16",
    "RFC-0002/slice-17",
)

OWNER_MAINLINE_EVIDENCE_TRACKING_ISSUES = (
    {
        "repository": "lotus-idea",
        "issueNumber": 685,
        "issueUrl": "https://github.com/sgajbi/lotus-idea/issues/685",
        "role": "slice_11_owner_reconciliation",
    },
    {
        "repository": "lotus-idea",
        "issueNumber": 686,
        "issueUrl": "https://github.com/sgajbi/lotus-idea/issues/686",
        "role": "slice_11_supportability_reconciliation",
    },
)

OWNER_MAINLINE_EVIDENCE_OWNER_PROOFS = (
    {
        "ownerRepository": "lotus-gateway",
        "ownerIssueNumber": 505,
        "ownerIssueUrl": "https://github.com/sgajbi/lotus-gateway/issues/505",
        "ownerPullRequestNumber": 508,
        "ownerPullRequestUrl": "https://github.com/sgajbi/lotus-gateway/pull/508",
        "mergedMainCommitSha": "98a3240d8e951463be69995f50c52b216d3eda4a",
        "mainReleasabilityRunId": 29686511139,
        "mainReleasabilityRunUrl": (
            "https://github.com/sgajbi/lotus-gateway/actions/runs/29686511139"
        ),
        "mainReleasabilityCheckName": "Main Releasability Gate",
        "mainReleasabilityConclusion": "success",
        "proofStatus": "merged_main_validated",
    },
    {
        "ownerRepository": "lotus-workbench",
        "ownerIssueNumber": 484,
        "ownerIssueUrl": "https://github.com/sgajbi/lotus-workbench/issues/484",
        "ownerPullRequestNumber": 497,
        "ownerPullRequestUrl": "https://github.com/sgajbi/lotus-workbench/pull/497",
        "mergedMainCommitSha": "55cb94ddb33469b58e32308551c84f0c3c4c9e3a",
        "mainReleasabilityRunId": 29686864889,
        "mainReleasabilityRunUrl": (
            "https://github.com/sgajbi/lotus-workbench/actions/runs/29686864889"
        ),
        "mainReleasabilityCheckName": "Main Releasability Gate",
        "mainReleasabilityConclusion": "success",
        "proofStatus": "merged_main_validated",
    },
)

OWNER_MAINLINE_EVIDENCE_DEPENDENCY_POSTURE = (
    {
        "repository": "lotus-platform",
        "issueNumber": 563,
        "issueUrl": "https://github.com/sgajbi/lotus-platform/issues/563",
        "dependency": "authenticated_bff_principal_session_contract",
        "status": "open",
    },
    {
        "repository": "lotus-idea",
        "issueNumber": 687,
        "issueUrl": "https://github.com/sgajbi/lotus-idea/issues/687",
        "dependency": "production_identity_provider_proof",
        "status": "open",
    },
    {
        "repository": "lotus-idea",
        "issueNumber": 699,
        "issueUrl": "https://github.com/sgajbi/lotus-idea/issues/699",
        "dependency": "full_live_opportunity_journey_validation",
        "status": "open",
    },
    {
        "repository": "lotus-idea",
        "issueNumber": 380,
        "issueUrl": "https://github.com/sgajbi/lotus-idea/issues/380",
        "dependency": "data_product_certification_and_supported_feature_promotion",
        "status": "open",
    },
)

OWNER_MAINLINE_EVIDENCE_LOCAL_REFS = (
    OWNER_MAINLINE_EVIDENCE_CONTRACT_REF,
    "src/app/application/workbench/owner_mainline_evidence.py",
    "scripts/workbench/owner_mainline_evidence_gate.py",
    (
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-11-workbench-product-realization.md"
    ),
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Validation-and-CI.md",
    "make gateway-workbench-owner-mainline-evidence-gate",
)

REMAINING_OWNER_MAINLINE_CERTIFICATION_BLOCKERS = (
    "gateway_workbench_proof_missing",
    "workbench_product_proof_missing",
    "gateway_workbench_discovery_proof_missing",
    "workbench_panel_missing",
    "workbench_gateway_bff_consumption_proof_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "opportunity_archetype_workbench_product_proof_missing",
    "data_product_certification_missing",
    "supported_feature_promotion_missing",
)

OWNER_MAINLINE_AGGREGATE_BLOCKERS_CLEARED: tuple[str, ...] = ()

_EXPECTED_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "recordedAtUtc",
        "rfc",
        "sliceIds",
        "proofType",
        "proofScope",
        "evidenceClass",
        "ownerMainlineEvidenceValid",
        "trackingIssues",
        "ownerEvidence",
        "dependencyPosture",
        "localEvidenceRefs",
        "remainingCertificationBlockers",
        "aggregateBlockersCleared",
        "gatewayOwnerMainlineValidated",
        "workbenchOwnerMainlineValidated",
        "productionIdentityImplemented",
        "canonicalRuntimeCertified",
        "browserAccessibilityCertified",
        "dataProductCertified",
        "supportedFeaturePromoted",
        "runtimeExecutionObserved",
        "proofClosed",
    }
)


def owner_mainline_evidence_contract_is_valid(
    payload: Mapping[str, Any],
    *,
    repository_root: Path | None = None,
) -> bool:
    return not validate_owner_mainline_evidence_contract(
        payload,
        repository_root=repository_root,
    )


def validate_owner_mainline_evidence_contract(
    payload: Mapping[str, Any],
    *,
    repository_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    _validate_top_level_claims(payload, errors)
    _validate_exact_sequence(
        payload,
        "sliceIds",
        OWNER_MAINLINE_EVIDENCE_SLICE_IDS,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "trackingIssues",
        OWNER_MAINLINE_EVIDENCE_TRACKING_ISSUES,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "ownerEvidence",
        OWNER_MAINLINE_EVIDENCE_OWNER_PROOFS,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "dependencyPosture",
        OWNER_MAINLINE_EVIDENCE_DEPENDENCY_POSTURE,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "localEvidenceRefs",
        OWNER_MAINLINE_EVIDENCE_LOCAL_REFS,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "remainingCertificationBlockers",
        REMAINING_OWNER_MAINLINE_CERTIFICATION_BLOCKERS,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "aggregateBlockersCleared",
        OWNER_MAINLINE_AGGREGATE_BLOCKERS_CLEARED,
        errors,
    )
    _validate_local_refs(repository_root, errors)
    return errors


def _validate_top_level_claims(payload: Mapping[str, Any], errors: list[str]) -> None:
    unknown_keys = sorted(set(payload) - _EXPECTED_TOP_LEVEL_KEYS)
    if unknown_keys:
        errors.append(f"unknown top-level owner-mainline evidence fields: {unknown_keys}")
    if payload.get("schemaVersion") != OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION:
        errors.append("schemaVersion must be the RFC-0002 Slice 11 owner-mainline schema")
    if payload.get("repository") != "lotus-idea":
        errors.append("repository must be lotus-idea")
    if not is_timezone_aware_datetime_text(payload.get("recordedAtUtc")):
        errors.append("recordedAtUtc must be timezone-aware")
    if payload.get("rfc") != "RFC-0002":
        errors.append("rfc must be RFC-0002")
    if payload.get("proofType") != "rfc0002_slice11_owner_mainline_evidence":
        errors.append("proofType must be rfc0002_slice11_owner_mainline_evidence")
    if payload.get("proofScope") != "owner_repo_mainline_evidence_index":
        errors.append("proofScope must be owner_repo_mainline_evidence_index")
    if payload.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("evidenceClass must be source_contract")
    for field_name in (
        "ownerMainlineEvidenceValid",
        "gatewayOwnerMainlineValidated",
        "workbenchOwnerMainlineValidated",
    ):
        if payload.get(field_name) is not True:
            errors.append(f"{field_name} must be true")
    for field_name in (
        "productionIdentityImplemented",
        "canonicalRuntimeCertified",
        "browserAccessibilityCertified",
        "dataProductCertified",
        "supportedFeaturePromoted",
        "runtimeExecutionObserved",
        "proofClosed",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"{field_name} must be false")


def _validate_exact_sequence(
    payload: Mapping[str, Any],
    field_name: str,
    expected: Sequence[object],
    errors: list[str],
) -> None:
    value = payload.get(field_name)
    if not isinstance(value, list):
        errors.append(f"{field_name} must be a JSON array")
        return
    if tuple(value) != tuple(expected):
        errors.append(f"{field_name} must match the governed owner-mainline evidence contract")


def _validate_local_refs(repository_root: Path | None, errors: list[str]) -> None:
    if repository_root is None:
        return
    if not required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=OWNER_MAINLINE_EVIDENCE_LOCAL_REFS,
        non_file_ref_prefixes=("make ",),
    ):
        errors.append("localEvidenceRefs must point to existing repository evidence")
    if not required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=OWNER_MAINLINE_EVIDENCE_LOCAL_REFS,
    ):
        errors.append("localEvidenceRefs must include an implemented Make target")
