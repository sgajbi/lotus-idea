from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.mandate_restriction_signal import (
    mandate_restriction_review_ready_from_advise_diagnostic,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import sha256_json
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

from .runtime_execution import (
    ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_EVIDENCE_REFS,
    ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_SCHEMA_VERSION,
)

_TOP_KEYS = frozenset(
    {
        "schemaVersion",
        "repository",
        "evidenceClass",
        "proofFamily",
        "proofType",
        "sourceAuthority",
        "generatedAtUtc",
        "execution",
        "aggregateBlockersSatisfied",
        "remainingCertificationBlockers",
        "evidenceRefs",
        "nonProofClaims",
    }
)
_EXECUTION_KEYS = frozenset(
    {
        "status",
        "evaluatedAtUtc",
        "requestReceipt",
        "workflowReceipt",
        "evaluationReceipt",
        "qualificationBlockers",
    }
)
_REQUEST_KEYS = frozenset(
    {
        "tenantIdHash",
        "bookIdHash",
        "portfolioIdHash",
        "clientIdHash",
        "evaluationIdHash",
        "asOfDate",
        "evaluatedAtUtc",
        "consumerSystem",
        "correlationIdHash",
        "traceIdHash",
        "policyVersion",
        "requestDigest",
    }
)
_WORKFLOW_KEYS = frozenset(
    {
        "productId",
        "sourceSystem",
        "productVersion",
        "routeTemplate",
        "evaluationIdHash",
        "tenantScopeHash",
        "portfolioIdHash",
        "sourceCorrelationIdHash",
        "sourceTraceIdHash",
        "asOfDate",
        "generatedAtUtc",
        "contentHash",
        "sourceEvidenceHash",
        "policyContentHash",
        "policyPackId",
        "policyVersion",
        "evaluationStatus",
        "openRequirementCount",
        "blockedRequirementCount",
        "signOffStatus",
        "signOffBlockerCount",
        "clientReadyPublication",
        "dataQualityStatus",
        "freshness",
        "adviseDiagnostic",
        "receiptDigest",
    }
)
_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "reasonCodes",
        "unsupportedReasons",
        "policyVersion",
        "candidateScore",
        "restrictionReviewRequired",
        "candidateIdHash",
        "signalIdHash",
        "evidencePacketIdHash",
        "sourceRefsDigest",
        "evaluationDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "policyWorkflowOwned",
        "opportunityDetectionOwned",
        "restrictionCleared",
        "suitabilityApproved",
        "policyApproved",
        "proposalApproved",
        "rebalanceAuthorized",
        "orderAuthorized",
        "clientPublicationApproved",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
        "ideaPersistenceRequired",
    }
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_WORKFLOW_ROUTE_TEMPLATE = "/advisory/policy-evaluations/{evaluation_id}/workflow"


def advise_mandate_restriction_runtime_execution_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != ADVISE_MANDATE_RESTRICTION_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "mandate_restriction_review"
        or payload.get("proofType") != "lotus_advise_policy_workflow_evaluation"
        or payload.get("sourceAuthority") != "lotus-advise"
    ):
        return False
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    if (
        generated is None
        or not _mapping_has_keys(execution, _EXECUTION_KEYS)
        or not _mapping_has_keys(claims, _CLAIM_KEYS)
    ):
        return False
    assert isinstance(execution, Mapping)
    assert isinstance(claims, Mapping)
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    request = execution.get("requestReceipt")
    workflow = execution.get("workflowReceipt")
    evaluation = execution.get("evaluationReceipt")
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or evaluated is None
        or generated < evaluated
        or not _mapping_has_keys(request, _REQUEST_KEYS)
        or not _mapping_has_keys(workflow, _WORKFLOW_KEYS)
        or not _mapping_has_keys(evaluation, _EVALUATION_KEYS)
        or not _claims_are_valid(claims)
    ):
        return False
    assert isinstance(request, Mapping)
    assert isinstance(workflow, Mapping)
    assert isinstance(evaluation, Mapping)
    return (
        _digests_are_valid(request, workflow, evaluation)
        and _receipts_reconcile(request, workflow, evaluation, evaluated)
        and tuple(payload.get("aggregateBlockersSatisfied") or ())
        == ADVISE_MANDATE_RESTRICTION_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == ADVISE_MANDATE_RESTRICTION_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ())
        == ADVISE_MANDATE_RESTRICTION_RUNTIME_EVIDENCE_REFS
    )


def _mapping_has_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == keys


def _claims_are_valid(claims: Mapping[str, Any]) -> bool:
    owners = {
        "policyWorkflowOwned": "lotus-advise",
        "opportunityDetectionOwned": "lotus-idea",
    }
    return all(claims.get(key) == value for key, value in owners.items()) and all(
        value is False for key, value in claims.items() if key not in owners
    )


def _digests_are_valid(*receipts: Mapping[str, Any]) -> bool:
    digest_keys = ("requestDigest", "receiptDigest", "evaluationDigest")
    for receipt, digest_key in zip(receipts, digest_keys, strict=True):
        material = {key: value for key, value in receipt.items() if key != digest_key}
        if receipt.get(digest_key) != sha256_json(material):
            return False
    return all(
        _is_sha256(value)
        for value in (
            receipts[0].get("tenantIdHash"),
            receipts[0].get("bookIdHash"),
            receipts[0].get("portfolioIdHash"),
            receipts[0].get("clientIdHash"),
            receipts[0].get("evaluationIdHash"),
            receipts[0].get("correlationIdHash"),
            receipts[0].get("traceIdHash"),
            receipts[0].get("requestDigest"),
            receipts[1].get("tenantScopeHash"),
            receipts[1].get("portfolioIdHash"),
            receipts[1].get("evaluationIdHash"),
            receipts[1].get("sourceCorrelationIdHash"),
            receipts[1].get("sourceTraceIdHash"),
            receipts[1].get("contentHash"),
            receipts[1].get("sourceEvidenceHash"),
            receipts[1].get("policyContentHash"),
            receipts[1].get("receiptDigest"),
            receipts[2].get("sourceRefsDigest"),
            receipts[2].get("evaluationDigest"),
        )
    )


def _receipts_reconcile(
    request: Mapping[str, Any],
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    try:
        date.fromisoformat(str(request.get("asOfDate")))
        Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, ValueError):
        return False
    source_generated = parse_timezone_aware_datetime(workflow.get("generatedAtUtc"))
    if (
        request.get("consumerSystem") != "lotus-idea"
        or request.get("evaluatedAtUtc") != evaluated.isoformat().replace("+00:00", "Z")
        or request.get("evaluationIdHash") != workflow.get("evaluationIdHash")
        or request.get("tenantIdHash") != workflow.get("tenantScopeHash")
        or request.get("portfolioIdHash") != workflow.get("portfolioIdHash")
        or request.get("correlationIdHash") != workflow.get("sourceCorrelationIdHash")
        or request.get("traceIdHash") != workflow.get("sourceTraceIdHash")
        or request.get("asOfDate") != workflow.get("asOfDate")
        or request.get("policyVersion") != evaluation.get("policyVersion")
        or source_generated is None
        or source_generated > evaluated
        or workflow.get("productId") != "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
        or workflow.get("sourceSystem") != "lotus-advise"
        or workflow.get("productVersion") != "v1"
        or workflow.get("routeTemplate") != _WORKFLOW_ROUTE_TEMPLATE
        or workflow.get("freshness") != "current"
        or str(workflow.get("dataQualityStatus", "")).lower()
        not in {"ready", "complete", "quality_passed"}
        or evaluation.get("family") != "mandate_restriction"
        or evaluation.get("unsupportedReasons") != []
        or evaluation.get("sourceRefsDigest") != sha256_json([dict(workflow)])
    ):
        return False
    counts = (
        workflow.get("openRequirementCount"),
        workflow.get("blockedRequirementCount"),
        workflow.get("signOffBlockerCount"),
    )
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        return False
    review_required = mandate_restriction_review_ready_from_advise_diagnostic(
        _optional_text(workflow.get("adviseDiagnostic"))
    )
    if evaluation.get("restrictionReviewRequired") is not review_required:
        return False
    if review_required:
        return (
            evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and _is_sha256(evaluation.get("evidencePacketIdHash"))
            and tuple(evaluation.get("reasonCodes") or ())
            == ("mandate_restriction_review", "review_required")
        )
    return (
        evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and evaluation.get("evidencePacketIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
