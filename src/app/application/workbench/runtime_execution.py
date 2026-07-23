from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from app.application.source_safe_cross_repo_proof import (
    is_timezone_aware_datetime_text,
    required_file_evidence_present,
    required_make_target_evidence_present,
)
from app.application.workbench.owner_mainline_evidence import (
    OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION,
    owner_mainline_evidence_contract_is_valid,
)
from app.domain.proof_evidence import EvidenceClass


GATEWAY_WORKBENCH_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_GATEWAY_WORKBENCH_RUNTIME_EXECUTION_PROOF"
GATEWAY_WORKBENCH_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.gateway-workbench-runtime-execution-proof.v1"
)

GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED = ("workbench_gateway_bff_consumption_proof_missing",)

REMAINING_GATEWAY_WORKBENCH_RUNTIME_CERTIFICATION_BLOCKERS = (
    "workbench_panel_missing",
    "browser_accessibility_proof_missing",
    "canonical_demo_runtime_proof_missing",
    "production_identity_provider_proof_missing",
    "data_product_certification_missing",
    "supported_feature_promotion_missing",
)

REQUIRED_GATEWAY_WORKBENCH_RUNTIME_LOCAL_REFS = (
    "src/app/application/workbench/runtime_execution.py",
    "scripts/workbench/generate_runtime_execution_proof.py",
    "scripts/workbench/runtime_execution_proof_gate.py",
    "src/app/application/workbench/owner_mainline_evidence.py",
    "contracts/implementation-proof/rfc0002-slice11-owner-mainline-evidence.v1.json",
    (
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-slice-11-workbench-product-realization.md"
    ),
    "docs/operations/implementation-proof-readiness.md",
    "wiki/Validation-and-CI.md",
    "wiki/Supported-Features.md",
    "make gateway-workbench-runtime-execution-proof-gate",
)

REQUIRED_GATEWAY_WORKBENCH_RUNTIME_SURFACES = (
    {
        "surfaceId": "workbench.idea.review_queue",
        "producer": "lotus-idea",
        "transport": "lotus-workbench-bff-to-lotus-gateway",
        "routeFamily": "GET /api/v1/ideas/review-queues/advisor",
        "requiredCapability": "idea.review.queue.read",
        "evidenceRole": "queue_rows_observed",
    },
    {
        "surfaceId": "workbench.idea.candidate_detail",
        "producer": "lotus-idea",
        "transport": "lotus-workbench-bff-to-lotus-gateway",
        "routeFamily": "GET /api/v1/ideas/candidates/{candidate_id}",
        "requiredCapability": "idea.candidate.detail.read",
        "evidenceRole": "source_safe_detail_observed",
    },
)

REQUIRED_GATEWAY_WORKBENCH_RUNTIME_NON_CLAIMS = (
    "production_identity_provider",
    "browser_accessibility_certification",
    "canonical_demo_runtime_certification",
    "data_product_certification",
    "supported_feature_promotion",
    "client_publication_authority",
    "suitability_or_execution_authority",
)

EXPECTED_TOP_LEVEL_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "generatedAtUtc",
        "rfc",
        "sliceIds",
        "proofType",
        "proofScope",
        "evidenceClass",
        "runtimeExecutionProofValid",
        "canonicalPortfolioId",
        "canonicalBenchmarkCode",
        "canonicalContractRef",
        "ownerMainlineEvidenceSchemaVersion",
        "ownerMainlineEvidenceDigest",
        "workbenchLiveValidationSummaryDigest",
        "workbenchShotIndexDigest",
        "runtimeEvidenceRefs",
        "surfaceCoverage",
        "proofChecks",
        "aggregateBlockersCleared",
        "remainingCertificationBlockers",
        "nonProofClaims",
        "gatewayBffConsumptionObserved",
        "productionIdentityImplemented",
        "browserAccessibilityCertified",
        "canonicalDemoRuntimeCertified",
        "dataProductCertified",
        "supportedFeaturePromoted",
        "clientPublicationAuthorized",
        "suitabilityOrExecutionAuthorized",
        "proofClosed",
        "aggregateProofProvenance",
    }
)


def build_gateway_workbench_runtime_execution_proof_payload(
    *,
    generated_at_utc: datetime,
    repository_root: Path,
    workbench_live_validation_summary: Mapping[str, Any],
    workbench_live_validation_summary_ref: str,
    workbench_shot_index_text: str,
    workbench_shot_index_ref: str,
    owner_mainline_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    proof_checks = {
        "timezoneAwareGeneratedAtUtc": generated_at_utc.tzinfo is not None
        and generated_at_utc.utcoffset() is not None,
        "localEvidencePresent": _local_evidence_present(repository_root),
        "makeTargetEvidencePresent": _local_make_targets_present(repository_root),
        "ownerMainlineEvidenceValid": owner_mainline_evidence_contract_is_valid(
            owner_mainline_evidence,
            repository_root=repository_root,
        ),
        "canonicalPortfolioObserved": (
            workbench_live_validation_summary.get("portfolioId") == "PB_SG_GLOBAL_BAL_001"
        ),
        "canonicalBenchmarkObserved": (
            workbench_live_validation_summary.get("benchmarkCode") == "BMK_PB_GLOBAL_BALANCED_60_40"
        ),
        "canonicalContractObserved": _canonical_contract_observed(
            workbench_live_validation_summary
        ),
        "ideaJourneyThroughGatewayObserved": _idea_journey_through_gateway_observed(
            workbench_live_validation_summary
        ),
        "ideaQueueRowsObserved": _idea_queue_rows_observed(workbench_live_validation_summary),
        "ideaScreenshotEvidenceObserved": _idea_screenshot_evidence_observed(
            workbench_live_validation_summary
        ),
        "shotIndexBindsIdeaScreenshot": _shot_index_binds_idea_screenshot(
            workbench_shot_index_text
        ),
    }
    runtime_valid = all(value is True for value in proof_checks.values())
    return {
        "schemaVersion": GATEWAY_WORKBENCH_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "rfc": "RFC-0002",
        "sliceIds": ["RFC-0002/slice-11", "RFC-0002/slice-17"],
        "proofType": "gateway_workbench_runtime_execution",
        "proofScope": "workbench_bff_gateway_idea_review_queue_and_detail_runtime",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "runtimeExecutionProofValid": runtime_valid,
        "canonicalPortfolioId": "PB_SG_GLOBAL_BAL_001",
        "canonicalBenchmarkCode": "BMK_PB_GLOBAL_BALANCED_60_40",
        "canonicalContractRef": "lotus-platform/context/contracts/canonical-front-office-demo-data-contract.json",
        "ownerMainlineEvidenceSchemaVersion": OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION,
        "ownerMainlineEvidenceDigest": _digest_mapping(owner_mainline_evidence),
        "workbenchLiveValidationSummaryDigest": _digest_mapping(workbench_live_validation_summary),
        "workbenchShotIndexDigest": _digest_text(workbench_shot_index_text),
        "runtimeEvidenceRefs": [
            workbench_live_validation_summary_ref,
            workbench_shot_index_ref,
        ],
        "surfaceCoverage": list(REQUIRED_GATEWAY_WORKBENCH_RUNTIME_SURFACES),
        "proofChecks": proof_checks,
        "aggregateBlockersCleared": list(GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED),
        "remainingCertificationBlockers": list(
            REMAINING_GATEWAY_WORKBENCH_RUNTIME_CERTIFICATION_BLOCKERS
        ),
        "nonProofClaims": list(REQUIRED_GATEWAY_WORKBENCH_RUNTIME_NON_CLAIMS),
        "gatewayBffConsumptionObserved": runtime_valid,
        "productionIdentityImplemented": False,
        "browserAccessibilityCertified": False,
        "canonicalDemoRuntimeCertified": False,
        "dataProductCertified": False,
        "supportedFeaturePromoted": False,
        "clientPublicationAuthorized": False,
        "suitabilityOrExecutionAuthorized": False,
        "proofClosed": False,
    }


def gateway_workbench_runtime_execution_proof_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    return not validate_gateway_workbench_runtime_execution_proof(payload)


def validate_gateway_workbench_runtime_execution_proof(
    payload: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    _validate_top_level_claims(payload, errors)
    _validate_exact_sequence(
        payload,
        "sliceIds",
        ("RFC-0002/slice-11", "RFC-0002/slice-17"),
        errors,
    )
    _validate_exact_sequence(
        payload,
        "runtimeEvidenceRefs",
        payload.get("runtimeEvidenceRefs")
        if isinstance(payload.get("runtimeEvidenceRefs"), list)
        else (),
        errors,
        allow_dynamic_non_empty_text=True,
    )
    _validate_exact_sequence(
        payload,
        "surfaceCoverage",
        REQUIRED_GATEWAY_WORKBENCH_RUNTIME_SURFACES,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "aggregateBlockersCleared",
        GATEWAY_WORKBENCH_RUNTIME_BLOCKERS_SATISFIED,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "remainingCertificationBlockers",
        REMAINING_GATEWAY_WORKBENCH_RUNTIME_CERTIFICATION_BLOCKERS,
        errors,
    )
    _validate_exact_sequence(
        payload,
        "nonProofClaims",
        REQUIRED_GATEWAY_WORKBENCH_RUNTIME_NON_CLAIMS,
        errors,
    )
    _validate_proof_checks(payload, errors)
    return errors


def _validate_top_level_claims(payload: Mapping[str, Any], errors: list[str]) -> None:
    unknown_keys = sorted(set(payload) - EXPECTED_TOP_LEVEL_KEYS)
    if unknown_keys:
        errors.append(f"unknown top-level gateway-workbench runtime fields: {unknown_keys}")
    if payload.get("schemaVersion") != GATEWAY_WORKBENCH_RUNTIME_EXECUTION_SCHEMA_VERSION:
        errors.append("schemaVersion must be the Gateway/Workbench runtime execution schema")
    if payload.get("repository") != "lotus-idea":
        errors.append("repository must be lotus-idea")
    if not is_timezone_aware_datetime_text(payload.get("generatedAtUtc")):
        errors.append("generatedAtUtc must be timezone-aware")
    if payload.get("rfc") != "RFC-0002":
        errors.append("rfc must be RFC-0002")
    if payload.get("proofType") != "gateway_workbench_runtime_execution":
        errors.append("proofType must be gateway_workbench_runtime_execution")
    if payload.get("proofScope") != ("workbench_bff_gateway_idea_review_queue_and_detail_runtime"):
        errors.append("proofScope must be the governed Workbench/Gateway runtime boundary")
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        errors.append("evidenceClass must be runtime_execution")
    if payload.get("runtimeExecutionProofValid") is not True:
        errors.append("runtimeExecutionProofValid must be true")
    if payload.get("canonicalPortfolioId") != "PB_SG_GLOBAL_BAL_001":
        errors.append("canonicalPortfolioId must be PB_SG_GLOBAL_BAL_001")
    if payload.get("canonicalBenchmarkCode") != "BMK_PB_GLOBAL_BALANCED_60_40":
        errors.append("canonicalBenchmarkCode must be BMK_PB_GLOBAL_BALANCED_60_40")
    if payload.get("canonicalContractRef") != (
        "lotus-platform/context/contracts/canonical-front-office-demo-data-contract.json"
    ):
        errors.append("canonicalContractRef must be the governed front-office data contract")
    if payload.get("ownerMainlineEvidenceSchemaVersion") != OWNER_MAINLINE_EVIDENCE_SCHEMA_VERSION:
        errors.append("ownerMainlineEvidenceSchemaVersion must match owner-mainline evidence")
    for digest_field in (
        "ownerMainlineEvidenceDigest",
        "workbenchLiveValidationSummaryDigest",
        "workbenchShotIndexDigest",
    ):
        if not _is_sha256_digest(payload.get(digest_field)):
            errors.append(f"{digest_field} must be a sha256 digest")
    if payload.get("gatewayBffConsumptionObserved") is not True:
        errors.append("gatewayBffConsumptionObserved must be true")
    for field_name in (
        "productionIdentityImplemented",
        "browserAccessibilityCertified",
        "canonicalDemoRuntimeCertified",
        "dataProductCertified",
        "supportedFeaturePromoted",
        "clientPublicationAuthorized",
        "suitabilityOrExecutionAuthorized",
        "proofClosed",
    ):
        if payload.get(field_name) is not False:
            errors.append(f"{field_name} must be false")


def _validate_proof_checks(payload: Mapping[str, Any], errors: list[str]) -> None:
    proof_checks = payload.get("proofChecks")
    if not isinstance(proof_checks, Mapping):
        errors.append("proofChecks must be an object")
        return
    required_checks = (
        "timezoneAwareGeneratedAtUtc",
        "localEvidencePresent",
        "makeTargetEvidencePresent",
        "ownerMainlineEvidenceValid",
        "canonicalPortfolioObserved",
        "canonicalBenchmarkObserved",
        "canonicalContractObserved",
        "ideaJourneyThroughGatewayObserved",
        "ideaQueueRowsObserved",
        "ideaScreenshotEvidenceObserved",
        "shotIndexBindsIdeaScreenshot",
    )
    unknown_checks = sorted(set(proof_checks) - set(required_checks))
    if unknown_checks:
        errors.append(f"unknown proofChecks fields: {unknown_checks}")
    for check in required_checks:
        if proof_checks.get(check) is not True:
            errors.append(f"proofChecks.{check} must be true")


def _validate_exact_sequence(
    payload: Mapping[str, Any],
    field_name: str,
    expected: Sequence[object],
    errors: list[str],
    *,
    allow_dynamic_non_empty_text: bool = False,
) -> None:
    value = payload.get(field_name)
    if not isinstance(value, list):
        errors.append(f"{field_name} must be a JSON array")
        return
    if allow_dynamic_non_empty_text:
        if len(value) != 2 or not all(isinstance(item, str) and item.strip() for item in value):
            errors.append(f"{field_name} must contain two source-safe evidence refs")
        return
    if tuple(value) != tuple(expected):
        errors.append(f"{field_name} must match the governed runtime execution contract")


def _local_evidence_present(repository_root: Path) -> bool:
    return required_file_evidence_present(
        repository_root=repository_root,
        sibling_roots={},
        evidence_refs=REQUIRED_GATEWAY_WORKBENCH_RUNTIME_LOCAL_REFS,
        non_file_ref_prefixes=("make ",),
    )


def _local_make_targets_present(repository_root: Path) -> bool:
    return required_make_target_evidence_present(
        repository_root=repository_root,
        evidence_refs=REQUIRED_GATEWAY_WORKBENCH_RUNTIME_LOCAL_REFS,
    )


def _canonical_contract_observed(summary: Mapping[str, Any]) -> bool:
    contract = summary.get("canonicalContract")
    return (
        isinstance(contract, Mapping)
        and contract.get("contractId") == "canonical-front-office-demo-data-contract"
        and contract.get("governedByRfc") == "RFC-0076"
        and contract.get("portfolioId") == "PB_SG_GLOBAL_BAL_001"
        and contract.get("benchmarkCode") == "BMK_PB_GLOBAL_BALANCED_60_40"
        and isinstance(contract.get("canonicalAsOfDate"), str)
        and bool(contract.get("canonicalAsOfDate"))
    )


def _idea_journey_through_gateway_observed(summary: Mapping[str, Any]) -> bool:
    checks = summary.get("advisoryJourneyChecks")
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)):
        return False
    for item in checks:
        if not isinstance(item, Mapping):
            continue
        route = item.get("route")
        if (
            item.get("key") == "opportunities"
            and item.get("title") == "Opportunities And Ideas"
            and item.get("panel") == "advisory.opportunities"
            and item.get("owner") == "lotus-idea"
            and item.get("sourcePosture") == "idea-review-queue-through-gateway"
            and item.get("state") == "ready"
            and item.get("gatewayBacked") is True
            and isinstance(route, str)
            and "mode=opportunities" in route
            and "candidateId=" in route
        ):
            return True
    return False


def _idea_queue_rows_observed(summary: Mapping[str, Any]) -> bool:
    checks = summary.get("uiChecks")
    if not isinstance(checks, Sequence) or isinstance(checks, (str, bytes)):
        return False
    for item in checks:
        if not isinstance(item, Mapping):
            continue
        row_count = item.get("rowCount")
        if (
            item.get("description") == "Idea candidate review queue"
            and item.get("kind") == "table"
            and isinstance(row_count, int)
            and not isinstance(row_count, bool)
            and row_count >= 1
        ):
            return True
    return False


def _idea_screenshot_evidence_observed(summary: Mapping[str, Any]) -> bool:
    screenshots = summary.get("screenshots")
    if not isinstance(screenshots, Sequence) or isinstance(screenshots, (str, bytes)):
        return False
    for item in screenshots:
        if not isinstance(item, Mapping):
            continue
        if (
            item.get("name") == "advisory-opportunities-live.png"
            and item.get("panel") == "advisory.opportunities"
            and item.get("portfolioId") == "PB_SG_GLOBAL_BAL_001"
            and item.get("benchmarkCode") == "BMK_PB_GLOBAL_BALANCED_60_40"
            and item.get("state") == "demo_ready"
        ):
            return True
    return False


def _shot_index_binds_idea_screenshot(shot_index_text: str) -> bool:
    return (
        "advisory-opportunities-live.png" in shot_index_text
        and "live-validation-summary.json" in shot_index_text
    )


def _digest_mapping(payload: Mapping[str, Any]) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return _digest_text(rendered)


def _digest_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _is_sha256_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdef" for character in digest)
