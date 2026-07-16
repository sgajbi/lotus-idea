from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.advise_policy_runtime_evidence import (
    reconcile_advise_policy_workflow_receipts,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import sha256_json
from app.domain import missing_suitability_review_required_from_workflow
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

from .runtime_execution import (
    ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS,
    ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED,
    ADVISE_MISSING_SUITABILITY_RUNTIME_EVIDENCE_REFS,
    ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
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
        "minimumOpenRequirementCount",
        "candidateScore",
        "suitabilityContextMissing",
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
        "suitabilityApproved",
        "policyApproved",
        "proposalApproved",
        "signOffApproved",
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


def advise_missing_suitability_runtime_execution_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != ADVISE_MISSING_SUITABILITY_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "missing_suitability_context"
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
        == ADVISE_MISSING_SUITABILITY_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == ADVISE_MISSING_SUITABILITY_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ())
        == ADVISE_MISSING_SUITABILITY_RUNTIME_EVIDENCE_REFS
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


def _digests_are_valid(
    request: Mapping[str, Any],
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    for receipt, digest_key in (
        (request, "requestDigest"),
        (workflow, "receiptDigest"),
        (evaluation, "evaluationDigest"),
    ):
        material = {key: value for key, value in receipt.items() if key != digest_key}
        if receipt.get(digest_key) != sha256_json(material):
            return False
    hashes = (
        request.get("tenantIdHash"),
        request.get("bookIdHash"),
        request.get("portfolioIdHash"),
        request.get("clientIdHash"),
        request.get("evaluationIdHash"),
        request.get("correlationIdHash"),
        request.get("traceIdHash"),
        request.get("requestDigest"),
        workflow.get("tenantScopeHash"),
        workflow.get("portfolioIdHash"),
        workflow.get("evaluationIdHash"),
        workflow.get("sourceCorrelationIdHash"),
        workflow.get("sourceTraceIdHash"),
        workflow.get("contentHash"),
        workflow.get("sourceEvidenceHash"),
        workflow.get("policyContentHash"),
        workflow.get("receiptDigest"),
        evaluation.get("sourceRefsDigest"),
        evaluation.get("evaluationDigest"),
    )
    return all(_is_sha256(value) for value in hashes)


def _receipts_reconcile(
    request: Mapping[str, Any],
    workflow: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    try:
        date.fromisoformat(str(request.get("asOfDate")))
        Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    minimum_open = evaluation.get("minimumOpenRequirementCount")
    if (
        not isinstance(minimum_open, int)
        or isinstance(minimum_open, bool)
        or minimum_open < 0
        or not reconcile_advise_policy_workflow_receipts(
            request,
            workflow,
            evaluated_at_utc=evaluated,
        )
        or request.get("policyVersion") != evaluation.get("policyVersion")
        or evaluation.get("family") != "missing_suitability_context"
        or evaluation.get("unsupportedReasons") != []
        or evaluation.get("sourceRefsDigest") != sha256_json([dict(workflow)])
        or str(workflow.get("clientReadyPublication", "")).upper() != "BLOCKED"
    ):
        return False
    values = (
        workflow.get("evaluationStatus"),
        workflow.get("openRequirementCount"),
        workflow.get("blockedRequirementCount"),
        workflow.get("signOffStatus"),
        workflow.get("signOffBlockerCount"),
    )
    if not (
        isinstance(values[0], str)
        and isinstance(values[1], int)
        and not isinstance(values[1], bool)
        and isinstance(values[2], int)
        and not isinstance(values[2], bool)
        and isinstance(values[3], str)
        and isinstance(values[4], int)
        and not isinstance(values[4], bool)
    ):
        return False
    context_missing = missing_suitability_review_required_from_workflow(
        evaluation_status=values[0],
        open_requirement_count=values[1],
        blocked_requirement_count=values[2],
        sign_off_status=values[3],
        sign_off_blocker_count=values[4],
        minimum_open_requirement_count=minimum_open,
    )
    if evaluation.get("suitabilityContextMissing") is not context_missing:
        return False
    if context_missing:
        return (
            evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and _is_sha256(evaluation.get("evidencePacketIdHash"))
            and tuple(evaluation.get("reasonCodes") or ())
            == ("suitability_context_missing", "review_required")
        )
    return (
        evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and evaluation.get("evidencePacketIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
