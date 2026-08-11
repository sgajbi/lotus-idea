from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.runtime_evidence import sha256_json
from app.application.manage_mandate_runtime_evidence.runtime_execution import (
    MANAGE_MANDATE_REMAINING_BLOCKERS,
    MANAGE_MANDATE_RUNTIME_BLOCKERS_SATISFIED,
    MANAGE_MANDATE_RUNTIME_EVIDENCE_REFS,
    MANAGE_MANDATE_RUNTIME_EXECUTION_SCHEMA_VERSION,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

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
        "actionRegisterReceipt",
        "mandatePerformanceHealthReceipt",
        "mandateRiskHealthReceipt",
        "evaluationReceipt",
        "qualificationBlockers",
    }
)
_REQUEST_KEYS = frozenset(
    {
        "tenantIdHash",
        "portfolioIdHash",
        "asOfDate",
        "evaluatedAtUtc",
        "consumerSystem",
        "correlationIdHash",
        "policyVersion",
        "requestDigest",
    }
)
_SOURCE_KEYS = frozenset(
    {
        "productId",
        "sourceSystem",
        "productVersion",
        "route",
        "asOfDate",
        "generatedAtUtc",
        "contentHash",
        "dataQualityStatus",
        "freshness",
        "receiptDigest",
    }
)
_ACTION_KEYS = _SOURCE_KEYS | {
    "responseTenantIdHash",
    "responsePortfolioIdHash",
    "responseAsOfDate",
    "responseGeneratedAtUtc",
    "responseEvidenceAsOfDate",
    "responseProducerGeneratedAtUtc",
    "temporalIdentityStatus",
    "sourceBatchFingerprint",
    "runCount",
    "operationCount",
    "workflowDecisionCount",
    "lineageEdgeCount",
    "supportabilityState",
    "supportabilityReason",
    "freshnessBucket",
    "portfolioScopeConfirmed",
    "sourceCorrelationIdHash",
    "upstreamSourceRefsDigest",
}
_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "reasonCodes",
        "unsupportedReasons",
        "policyVersion",
        "minimumWorkflowDecisionCount",
        "minimumLineageEdgeCount",
        "candidateScore",
        "candidateIdHash",
        "signalIdHash",
        "evidencePacketIdHash",
        "sourceRefsDigest",
        "evaluationDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "mandateFactsOwned",
        "performanceFactsOwned",
        "riskFactsOwned",
        "opportunityDetectionOwned",
        "mandateComplianceApproved",
        "rebalanceActionCreated",
        "orderCreated",
        "executionReady",
        "suitabilityCertified",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "clientPublicationApproved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
        "ideaPersistenceRequired",
    }
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def manage_mandate_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != MANAGE_MANDATE_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "allocation_drift_mandate_review"
        or payload.get("proofType") != "lotus_manage_mandate_health_evaluation"
        or payload.get("sourceAuthority") != "lotus-manage"
    ):
        return False
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    if (
        generated is None
        or not isinstance(execution, Mapping)
        or set(execution) != _EXECUTION_KEYS
        or not isinstance(claims, Mapping)
        or set(claims) != _CLAIM_KEYS
        or not _claims_are_valid(claims)
    ):
        return False
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    request = execution.get("requestReceipt")
    action = execution.get("actionRegisterReceipt")
    performance = execution.get("mandatePerformanceHealthReceipt")
    risk = execution.get("mandateRiskHealthReceipt")
    evaluation = execution.get("evaluationReceipt")
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or evaluated is None
        or generated < evaluated
        or not _mapping_has_keys(request, _REQUEST_KEYS)
        or not _mapping_has_keys(action, _ACTION_KEYS)
        or not _mapping_has_keys(performance, _SOURCE_KEYS)
        or not _mapping_has_keys(risk, _SOURCE_KEYS)
        or not _mapping_has_keys(evaluation, _EVALUATION_KEYS)
    ):
        return False
    assert isinstance(request, Mapping)
    assert isinstance(action, Mapping)
    assert isinstance(performance, Mapping)
    assert isinstance(risk, Mapping)
    assert isinstance(evaluation, Mapping)
    return (
        _digests_are_valid(request, action, performance, risk, evaluation)
        and _receipts_reconcile(request, action, performance, risk, evaluation, evaluated)
        and tuple(payload.get("aggregateBlockersSatisfied") or ())
        == MANAGE_MANDATE_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == MANAGE_MANDATE_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ()) == MANAGE_MANDATE_RUNTIME_EVIDENCE_REFS
    )


def _claims_are_valid(claims: Mapping[str, Any]) -> bool:
    owners = {
        "mandateFactsOwned": "lotus-manage",
        "performanceFactsOwned": "lotus-performance",
        "riskFactsOwned": "lotus-risk",
        "opportunityDetectionOwned": "lotus-idea",
    }
    return all(claims.get(key) == value for key, value in owners.items()) and all(
        value is False for key, value in claims.items() if key not in owners
    )


def _mapping_has_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == keys


def _digests_are_valid(*receipts: Mapping[str, Any]) -> bool:
    for receipt in receipts:
        digest_key = next(
            (
                key
                for key in ("requestDigest", "evaluationDigest", "receiptDigest")
                if key in receipt
            ),
            None,
        )
        if digest_key is None:
            return False
        material = {key: receipt[key] for key in receipt if key != digest_key}
        if receipt.get(digest_key) != sha256_json(material):
            return False
    return all(
        _is_sha256(value)
        for value in (
            receipts[0].get("tenantIdHash"),
            receipts[0].get("portfolioIdHash"),
            receipts[0].get("requestDigest"),
            receipts[1].get("sourceBatchFingerprint"),
            receipts[1].get("receiptDigest"),
            receipts[2].get("contentHash"),
            receipts[2].get("receiptDigest"),
            receipts[3].get("contentHash"),
            receipts[3].get("receiptDigest"),
            receipts[4].get("sourceRefsDigest"),
            receipts[4].get("evaluationDigest"),
        )
    )


def _receipts_reconcile(
    request: Mapping[str, Any],
    action: Mapping[str, Any],
    performance: Mapping[str, Any],
    risk: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    return (
        _request_scope_reconciles(request, action, performance, risk, evaluation, evaluated)
        and _source_receipts_are_valid(action, performance, risk, evaluated)
        and _source_ref_digests_reconcile(action, performance, risk, evaluation)
        and _action_register_supportability_is_valid(action)
        and _evaluation_outcome_is_valid(action, evaluation)
    )


def _request_scope_reconciles(
    request: Mapping[str, Any],
    action: Mapping[str, Any],
    performance: Mapping[str, Any],
    risk: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except ValueError:
        return False

    as_of_date = request.get("asOfDate")
    return (
        request.get("consumerSystem") == "lotus-idea"
        and request.get("evaluatedAtUtc") == evaluated.isoformat().replace("+00:00", "Z")
        and request.get("policyVersion") == evaluation.get("policyVersion")
        and request.get("tenantIdHash") == action.get("responseTenantIdHash")
        and request.get("portfolioIdHash") == action.get("responsePortfolioIdHash")
        and as_of_date == action.get("asOfDate")
        and as_of_date == action.get("responseAsOfDate")
        and as_of_date == action.get("responseEvidenceAsOfDate")
        and as_of_date == performance.get("asOfDate")
        and as_of_date == risk.get("asOfDate")
        and request.get("correlationIdHash") == action.get("sourceCorrelationIdHash")
        and _action_temporal_identity_reconciles(action)
    )


def _action_temporal_identity_reconciles(action: Mapping[str, Any]) -> bool:
    return (
        action.get("generatedAtUtc") == action.get("responseGeneratedAtUtc")
        and action.get("generatedAtUtc") == action.get("responseProducerGeneratedAtUtc")
        and action.get("contentHash") == action.get("sourceBatchFingerprint")
        and action.get("temporalIdentityStatus") == "available"
    )


def _source_receipts_are_valid(
    action: Mapping[str, Any],
    performance: Mapping[str, Any],
    risk: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    return (
        _source_is_valid(
            action,
            product_id="lotus-manage:PortfolioActionRegister:v1",
            source_system="lotus-manage",
            route="/api/v1/rebalance/supportability/summary",
            evaluated=evaluated,
        )
        and _source_is_valid(
            performance,
            product_id="lotus-performance:MandatePerformanceHealthContext:v1",
            source_system="lotus-performance",
            route="/performance/mandate-health-context",
            evaluated=evaluated,
        )
        and _source_is_valid(
            risk,
            product_id="lotus-risk:MandateRiskHealthContext:v1",
            source_system="lotus-risk",
            route="/analytics/risk/mandate-health-context",
            evaluated=evaluated,
        )
    )


def _source_ref_digests_reconcile(
    action: Mapping[str, Any],
    performance: Mapping[str, Any],
    risk: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    upstream = [dict(performance), dict(risk)]
    if action.get("upstreamSourceRefsDigest") != sha256_json(upstream):
        return False
    action_source_material = {key: action[key] for key in _SOURCE_KEYS if key != "receiptDigest"}
    action_source = {
        **action_source_material,
        "receiptDigest": sha256_json(action_source_material),
    }
    return evaluation.get("sourceRefsDigest") == sha256_json([action_source, *upstream])


def _action_register_supportability_is_valid(action: Mapping[str, Any]) -> bool:
    counts = (
        action.get("runCount"),
        action.get("operationCount"),
        action.get("workflowDecisionCount"),
        action.get("lineageEdgeCount"),
    )
    return (
        all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in counts
        )
        and action.get("supportabilityState") == "ready"
        and action.get("supportabilityReason") == "supportability_summary_ready"
        and action.get("freshnessBucket") in {"current", "same_day"}
        and action.get("portfolioScopeConfirmed") is True
    )


def _evaluation_outcome_is_valid(
    action: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    if evaluation.get("family") != "allocation_drift" or evaluation.get("unsupportedReasons") != []:
        return False
    minimum_workflow = evaluation.get("minimumWorkflowDecisionCount")
    minimum_lineage = evaluation.get("minimumLineageEdgeCount")
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in (minimum_workflow, minimum_lineage)
    ):
        return False
    try:
        Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, ValueError):
        return False
    should_create = (
        action["workflowDecisionCount"] >= minimum_workflow
        and action["lineageEdgeCount"] >= minimum_lineage
    )
    if should_create:
        return (
            evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and _is_sha256(evaluation.get("evidencePacketIdHash"))
            and "allocation_drift_attention" in tuple(evaluation.get("reasonCodes") or ())
        )
    return (
        evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and evaluation.get("evidencePacketIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _source_is_valid(
    receipt: Mapping[str, Any],
    *,
    product_id: str,
    source_system: str,
    route: str,
    evaluated: Any,
) -> bool:
    generated = parse_timezone_aware_datetime(receipt.get("generatedAtUtc"))
    return (
        receipt.get("productId") == product_id
        and receipt.get("sourceSystem") == source_system
        and receipt.get("productVersion") == "v1"
        and receipt.get("route") == route
        and generated is not None
        and generated <= evaluated
        and receipt.get("freshness") == "current"
        and str(receipt.get("dataQualityStatus", "")).lower() in {"ready", "complete"}
        and _is_sha256(receipt.get("contentHash"))
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
