from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import non_authority_claims_are_valid, sha256_json
from app.domain import assess_performance_benchmark_readiness
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

from .runtime_execution import (
    PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS,
    PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED,
    PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EVIDENCE_REFS,
    PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_SCHEMA_VERSION,
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
        "sourceReceipt",
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
        "periodName",
        "reportingCurrency",
        "evaluatedAtUtc",
        "consumerSystem",
        "correlationIdHash",
        "traceIdHash",
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
        "calculationIdHash",
        "portfolioIdHash",
        "inputFingerprint",
        "calculationHash",
        "benchmarkContextAvailable",
        "benchmarkIdHash",
        "benchmarkReturnSource",
        "requestedPointCount",
        "returnedPointCount",
        "missingPointCount",
        "coverageRatio",
        "producerCorrelationIdHash",
        "producerTraceIdHash",
        "readinessDiagnostic",
        "entitlementAllowed",
        "receiptDigest",
    }
)
_EVALUATION_KEYS = frozenset(
    {
        "family",
        "outcome",
        "readinessDiagnostic",
        "benchmarkReviewRequired",
        "policyVersion",
        "requestReceiptDigest",
        "sourceReceiptDigest",
        "benchmarkContextDigest",
        "sourceRefCount",
        "evaluationDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "officialPerformanceOwned",
        "benchmarkAssignmentOwned",
        "opportunityReadinessOwned",
        "benchmarkAssignmentChanged",
        "officialPerformanceCalculated",
        "benchmarkMethodologyCertified",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "clientPublicationApproved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
        "ideaPersistenceRequired",
    }
)
_HASH_KEYS = (
    "tenantIdHash",
    "bookIdHash",
    "portfolioIdHash",
    "clientIdHash",
    "evaluationIdHash",
    "correlationIdHash",
    "traceIdHash",
    "requestDigest",
)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def performance_benchmark_readiness_runtime_execution_is_valid(
    payload: Mapping[str, Any],
) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion")
        != PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "missing_benchmark_performance_readiness"
        or payload.get("proofType") != "lotus_performance_benchmark_readiness_evaluation"
        or payload.get("sourceAuthority") != "lotus-performance"
    ):
        return False
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if (
        generated is None
        or not _has_exact_keys(execution, _EXECUTION_KEYS)
        or not _has_exact_keys(claims, _CLAIM_KEYS)
    ):
        return False
    assert isinstance(execution, Mapping) and isinstance(claims, Mapping)
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    request = execution.get("requestReceipt")
    source = execution.get("sourceReceipt")
    evaluation = execution.get("evaluationReceipt")
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or evaluated is None
        or generated < evaluated
        or not _has_exact_keys(request, _REQUEST_KEYS)
        or not _has_exact_keys(source, _SOURCE_KEYS)
        or not _has_exact_keys(evaluation, _EVALUATION_KEYS)
        or not non_authority_claims_are_valid(
            claims,
            owners={
                "officialPerformanceOwned": "lotus-performance",
                "benchmarkAssignmentOwned": "lotus-core",
                "opportunityReadinessOwned": "lotus-idea",
            },
        )
    ):
        return False
    assert isinstance(request, Mapping)
    assert isinstance(source, Mapping)
    assert isinstance(evaluation, Mapping)
    return (
        _request_is_valid(request, execution)
        and _source_is_valid(source, request, evaluated)
        and _evaluation_is_valid(evaluation, source, request)
        and tuple(payload.get("aggregateBlockersSatisfied") or ())
        == PERFORMANCE_BENCHMARK_READINESS_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == PERFORMANCE_BENCHMARK_READINESS_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ())
        == PERFORMANCE_BENCHMARK_READINESS_RUNTIME_EVIDENCE_REFS
    )


def _request_is_valid(request: Mapping[str, Any], execution: Mapping[str, Any]) -> bool:
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except (TypeError, ValueError):
        return False
    currency = request.get("reportingCurrency")
    return (
        _digest_is_valid(request, "requestDigest")
        and all(_is_sha256(request.get(key)) for key in _HASH_KEYS)
        and request.get("evaluatedAtUtc") == execution.get("evaluatedAtUtc")
        and request.get("consumerSystem") == "lotus-idea"
        and isinstance(request.get("periodName"), str)
        and bool(str(request.get("periodName")).strip())
        and isinstance(request.get("policyVersion"), str)
        and bool(str(request.get("policyVersion")).strip())
        and (
            currency is None
            or (
                isinstance(currency, str)
                and len(currency) == 3
                and currency.isalpha()
                and currency.isupper()
            )
        )
    )


def _source_is_valid(
    source: Mapping[str, Any],
    request: Mapping[str, Any],
    evaluated_at_utc: datetime,
) -> bool:
    source_generated = parse_timezone_aware_datetime(source.get("generatedAtUtc"))
    if (
        not _digest_is_valid(source, "receiptDigest")
        or source.get("productId") != "lotus-performance:ReturnsSeriesBundle:v1"
        or source.get("sourceSystem") != "lotus-performance"
        or source.get("route") != "/integration/returns/series"
        or source.get("asOfDate") != request.get("asOfDate")
        or source_generated is None
        or source_generated > evaluated_at_utc
        or source.get("freshness") != "current"
        or str(source.get("dataQualityStatus", "")).lower() not in {"ready", "partial"}
        or source.get("entitlementAllowed") is not True
        or source.get("portfolioIdHash") != request.get("portfolioIdHash")
        or source.get("producerCorrelationIdHash") != request.get("correlationIdHash")
        or source.get("producerTraceIdHash") != request.get("traceIdHash")
        or source.get("contentHash") != source.get("calculationHash")
        or not all(
            _is_sha256(source.get(key))
            for key in (
                "contentHash",
                "calculationIdHash",
                "portfolioIdHash",
                "inputFingerprint",
                "calculationHash",
                "producerCorrelationIdHash",
                "producerTraceIdHash",
            )
        )
        or not isinstance(source.get("productVersion"), str)
        or not str(source.get("productVersion")).strip()
    ):
        return False
    return _coverage_is_valid(source) and _benchmark_context_is_valid(source)


def _coverage_is_valid(source: Mapping[str, Any]) -> bool:
    requested = source.get("requestedPointCount")
    returned = source.get("returnedPointCount")
    missing = source.get("missingPointCount")
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for value in (requested, returned, missing)
    ):
        return False
    assert isinstance(requested, int) and isinstance(returned, int) and isinstance(missing, int)
    try:
        ratio = Decimal(str(source.get("coverageRatio")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return (
        ratio.is_finite()
        and requested > 0
        and returned >= 0
        and missing >= 0
        and returned + missing == requested
        and ratio == Decimal(returned) / Decimal(requested)
    )


def _benchmark_context_is_valid(source: Mapping[str, Any]) -> bool:
    available = source.get("benchmarkContextAvailable")
    if not isinstance(available, bool):
        return False
    benchmark_id_hash = source.get("benchmarkIdHash")
    return_source = source.get("benchmarkReturnSource")
    assessment = assess_performance_benchmark_readiness(
        benchmark_context_available=available,
        benchmark_id=("pseudonymous" if _is_sha256(benchmark_id_hash) else None),
        benchmark_return_source=return_source if isinstance(return_source, str) else None,
    )
    return (
        assessment.outcome.value != "blocked"
        and source.get("readinessDiagnostic") == assessment.diagnostic
        and (
            (_is_sha256(benchmark_id_hash) and isinstance(return_source, str) and bool(return_source))
            if available
            else benchmark_id_hash is None and return_source is None
        )
    )


def _evaluation_is_valid(
    evaluation: Mapping[str, Any],
    source: Mapping[str, Any],
    request: Mapping[str, Any],
) -> bool:
    available = source.get("benchmarkContextAvailable") is True
    expected_outcome = "no_opportunity" if available else "review_required"
    expected_review = not available
    return (
        _digest_is_valid(evaluation, "evaluationDigest")
        and evaluation.get("family") == "missing_benchmark"
        and evaluation.get("outcome") == expected_outcome
        and evaluation.get("readinessDiagnostic") == source.get("readinessDiagnostic")
        and evaluation.get("benchmarkReviewRequired") is expected_review
        and evaluation.get("policyVersion") == request.get("policyVersion")
        and evaluation.get("requestReceiptDigest") == request.get("requestDigest")
        and evaluation.get("sourceReceiptDigest") == source.get("receiptDigest")
        and evaluation.get("benchmarkContextDigest") == _benchmark_context_digest(source)
        and evaluation.get("sourceRefCount") == 1
        and all(
            _is_sha256(evaluation.get(key))
            for key in (
                "requestReceiptDigest",
                "sourceReceiptDigest",
                "benchmarkContextDigest",
                "evaluationDigest",
            )
        )
    )


def _benchmark_context_digest(source: Mapping[str, Any]) -> str:
    return sha256_json(
        {
            key: source[key]
            for key in (
                "benchmarkContextAvailable",
                "benchmarkIdHash",
                "benchmarkReturnSource",
                "readinessDiagnostic",
            )
        }
    )


def _digest_is_valid(receipt: Mapping[str, Any], digest_key: str) -> bool:
    material = {key: value for key, value in receipt.items() if key != digest_key}
    return receipt.get(digest_key) == sha256_json(material)


def _has_exact_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == keys


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
