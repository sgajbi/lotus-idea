from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.runtime_evidence import sha256_json
from app.application.low_income_cashflow_runtime_evidence.runtime_execution import (
    LOW_INCOME_CASHFLOW_REMAINING_BLOCKERS,
    LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED,
    LOW_INCOME_CASHFLOW_RUNTIME_EVIDENCE_REFS,
    LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_SCHEMA_VERSION,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain.proof_evidence import (
    EvidenceClass,
    evidence_class_can_clear,
    parse_timezone_aware_datetime,
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
        "cashMovementReceipt",
        "cashflowProjectionReceipt",
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
        "horizonDays",
        "includeProjected",
        "correlationIdHash",
        "requestDigest",
    }
)
_SOURCE_BASE_KEYS = frozenset(
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
        "responseProductName",
        "responseProductVersion",
        "responseTenantIdHash",
        "responsePortfolioIdHash",
        "responseGeneratedAtUtc",
        "restatementVersion",
        "reconciliationStatus",
        "latestEvidenceAtUtc",
        "sourceBatchFingerprint",
        "snapshotId",
        "responseContentHash",
        "responseSourceDigest",
        "sourceRefsDigest",
        "sourceLineageDigest",
        "degradationStatus",
        "degradationReasonCodes",
        "degradationDetailCount",
        "sourceEvidenceCurrent",
        "freshnessStatus",
        "policyVersion",
        "sourceCorrelationIdHash",
        "receiptDigest",
    }
)
_MOVEMENT_KEYS = _SOURCE_BASE_KEYS | {
    "startDate",
    "endDate",
    "cashflowCount",
    "bucketDigest",
}
_PROJECTION_KEYS = _SOURCE_BASE_KEYS | {
    "rangeStartDate",
    "rangeEndDate",
    "includeProjected",
    "portfolioCurrency",
    "projectionDays",
    "pointCount",
    "minimumProjectedCumulativeCashflow",
    "bookedTotalNetCashflow",
    "projectedSettlementTotalCashflow",
    "totalNetCashflow",
    "pointDigest",
}
_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "reasonCodes",
        "unsupportedReasons",
        "policyVersion",
        "projectedCumulativeCashflowThreshold",
        "candidateScore",
        "candidateIdHash",
        "signalIdHash",
        "evaluationDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "cashflowFactsOwned",
        "opportunityDetectionOwned",
        "clientIncomeNeedInferred",
        "incomePlanProduced",
        "fundingAdviceProduced",
        "liquidityAdviceProduced",
        "treasuryInstructionProduced",
        "suitabilityCertified",
        "complianceApproved",
        "executionReady",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "clientPublicationApproved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
        "ideaPersistenceRequired",
    }
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def low_income_cashflow_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != LOW_INCOME_CASHFLOW_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "low_income_cashflow"
        or payload.get("proofType") != "lotus_core_cashflow_evaluation"
        or payload.get("sourceAuthority") != "lotus-core"
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
    ):
        return False
    if (
        claims.get("cashflowFactsOwned") != "lotus-core"
        or claims.get("opportunityDetectionOwned") != "lotus-idea"
    ):
        return False
    if any(
        value is not False
        for key, value in claims.items()
        if key not in {"cashflowFactsOwned", "opportunityDetectionOwned"}
    ):
        return False
    request = execution.get("requestReceipt")
    movement = execution.get("cashMovementReceipt")
    projection = execution.get("cashflowProjectionReceipt")
    evaluation = execution.get("evaluationReceipt")
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or not isinstance(request, Mapping)
        or set(request) != _REQUEST_KEYS
        or not isinstance(movement, Mapping)
        or set(movement) != _MOVEMENT_KEYS
        or not isinstance(projection, Mapping)
        or set(projection) != _PROJECTION_KEYS
        or not isinstance(evaluation, Mapping)
        or set(evaluation) != _EVALUATION_KEYS
        or evaluated is None
        or generated < evaluated
    ):
        return False
    if not _digests_are_valid(request, movement, projection, evaluation):
        return False
    if not _request_and_sources_reconcile(request, movement, projection, evaluated):
        return False
    if not _source_posture_is_valid(movement) or not _source_posture_is_valid(projection):
        return False
    if not _evaluation_is_valid(evaluation, projection):
        return False
    return (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        == LOW_INCOME_CASHFLOW_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == LOW_INCOME_CASHFLOW_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ()) == LOW_INCOME_CASHFLOW_RUNTIME_EVIDENCE_REFS
        and evidence_class_can_clear(
            actual=EvidenceClass.RUNTIME_EXECUTION,
            required=EvidenceClass.RUNTIME_EXECUTION,
        )
    )


def _digests_are_valid(
    request: Mapping[str, Any],
    movement: Mapping[str, Any],
    projection: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> bool:
    for mapping, digest_key in (
        (request, "requestDigest"),
        (movement, "receiptDigest"),
        (projection, "receiptDigest"),
        (evaluation, "evaluationDigest"),
    ):
        material = {key: mapping[key] for key in mapping if key != digest_key}
        if mapping.get(digest_key) != sha256_json(material):
            return False
    hash_fields = (
        request.get("tenantIdHash"),
        request.get("portfolioIdHash"),
        request.get("correlationIdHash"),
        request.get("requestDigest"),
        movement.get("bucketDigest"),
        movement.get("receiptDigest"),
        projection.get("pointDigest"),
        projection.get("receiptDigest"),
        evaluation.get("evaluationDigest"),
    )
    return all(_is_sha256(value) for value in hash_fields)


def _request_and_sources_reconcile(
    request: Mapping[str, Any],
    movement: Mapping[str, Any],
    projection: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    try:
        as_of = date.fromisoformat(str(request.get("asOfDate")))
        projection_end = date.fromisoformat(str(projection.get("rangeEndDate")))
    except ValueError:
        return False
    horizon = request.get("horizonDays")
    if not isinstance(horizon, int) or not 1 <= horizon <= 366:
        return False
    if (
        request.get("consumerSystem") != "lotus-idea"
        or request.get("includeProjected") is not True
        or request.get("evaluatedAtUtc") != evaluated.isoformat().replace("+00:00", "Z")
        or request.get("asOfDate") != movement.get("asOfDate")
        or request.get("asOfDate") != projection.get("asOfDate")
        or request.get("asOfDate") != movement.get("startDate")
        or request.get("asOfDate") != movement.get("endDate")
        or request.get("asOfDate") != projection.get("rangeStartDate")
        or projection_end != as_of + timedelta(days=horizon)
        or projection.get("projectionDays") != horizon
        or projection.get("pointCount") != horizon + 1
        or projection.get("includeProjected") is not True
    ):
        return False
    for source in (movement, projection):
        if (
            source.get("responseTenantIdHash") != request.get("tenantIdHash")
            or source.get("responsePortfolioIdHash") != request.get("portfolioIdHash")
            or source.get("sourceCorrelationIdHash") != request.get("correlationIdHash")
        ):
            return False
    return (
        movement.get("productId") == "lotus-core:PortfolioCashMovementSummary:v1"
        and movement.get("responseProductName") == "PortfolioCashMovementSummary"
        and movement.get("route") == "/portfolios/{portfolio_id}/cash-movement-summary"
        and projection.get("productId") == "lotus-core:PortfolioCashflowProjection:v1"
        and projection.get("responseProductName") == "PortfolioCashflowProjection"
        and projection.get("route") == "/portfolios/{portfolio_id}/cashflow-projection"
    )


def _source_posture_is_valid(source: Mapping[str, Any]) -> bool:
    source_generated = parse_timezone_aware_datetime(source.get("responseGeneratedAtUtc"))
    latest_evidence = parse_timezone_aware_datetime(source.get("latestEvidenceAtUtc"))
    hashes = (
        source.get("contentHash"),
        source.get("sourceBatchFingerprint"),
        source.get("responseContentHash"),
        source.get("responseSourceDigest"),
    )
    return (
        source.get("sourceSystem") == "lotus-core"
        and source.get("productVersion") == "v1"
        and source.get("responseProductVersion") == "v1"
        and str(source.get("dataQualityStatus", "")).upper() == "COMPLETE"
        and source.get("freshness") == "current"
        and str(source.get("reconciliationStatus", "")).upper() == "COMPLETE"
        and source.get("degradationStatus") == "NONE"
        and not tuple(source.get("degradationReasonCodes") or ())
        and source.get("degradationDetailCount") == 0
        and source.get("sourceEvidenceCurrent") is True
        and str(source.get("freshnessStatus", "")).upper() == "CURRENT"
        and source_generated is not None
        and latest_evidence is not None
        and latest_evidence <= source_generated
        and all(_is_sha256(value) for value in hashes)
        and len(set(hashes)) == 1
        and all(
            isinstance(source.get(field), str) and str(source[field]).strip()
            for field in ("restatementVersion", "snapshotId", "policyVersion")
        )
    )


def _evaluation_is_valid(evaluation: Mapping[str, Any], projection: Mapping[str, Any]) -> bool:
    if evaluation.get("family") != "low_income" or evaluation.get("unsupportedReasons") != []:
        return False
    try:
        minimum = Decimal(str(projection.get("minimumProjectedCumulativeCashflow")))
        threshold = Decimal(str(evaluation.get("projectedCumulativeCashflowThreshold")))
        Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, ValueError):
        return False
    candidate_expected = minimum <= threshold
    if candidate_expected:
        return (
            evaluation.get("outcome") == "candidate_created"
            and _is_sha256(evaluation.get("candidateIdHash"))
            and _is_sha256(evaluation.get("signalIdHash"))
            and "income_attention" in tuple(evaluation.get("reasonCodes") or ())
        )
    return (
        evaluation.get("outcome") == "not_eligible"
        and evaluation.get("candidateIdHash") is None
        and evaluation.get("signalIdHash") is None
        and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
