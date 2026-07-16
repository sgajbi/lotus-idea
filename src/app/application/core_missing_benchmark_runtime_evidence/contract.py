from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.runtime_evidence import non_authority_claims_are_valid, sha256_json
from app.domain import benchmark_assignment_diagnostic
from app.domain.proof_evidence import EvidenceClass, parse_timezone_aware_datetime

from .runtime_execution import (
    CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS,
    CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED,
    CORE_MISSING_BENCHMARK_RUNTIME_EVIDENCE_REFS,
    CORE_MISSING_BENCHMARK_RUNTIME_EXECUTION_SCHEMA_VERSION,
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
        "benchmarkIdentityResolved",
        "assignmentEffectiveForAsOfDate",
        "assignmentStatus",
        "assignmentVersionPresent",
        "assignmentDiagnostic",
        "entitlementAllowed",
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
        "requestReceiptDigest",
        "assignmentStateDigest",
        "missingBenchmarkReviewRequired",
        "candidateIdHash",
        "signalIdHash",
        "evidencePacketIdHash",
        "sourceRefsDigest",
        "evaluationDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "benchmarkAssignmentOwned",
        "opportunityDetectionOwned",
        "benchmarkAssignmentChanged",
        "performanceBenchmarkReadinessCertified",
        "performanceMethodologyCertified",
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


def core_missing_benchmark_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != CORE_MISSING_BENCHMARK_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "missing_benchmark"
        or payload.get("proofType") != "lotus_core_benchmark_assignment_gap_evaluation"
        or payload.get("sourceAuthority") != "lotus-core"
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
                "benchmarkAssignmentOwned": "lotus-core",
                "opportunityDetectionOwned": "lotus-idea",
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
        == CORE_MISSING_BENCHMARK_RUNTIME_BLOCKERS_SATISFIED
        and tuple(payload.get("remainingCertificationBlockers") or ())
        == CORE_MISSING_BENCHMARK_REMAINING_BLOCKERS
        and tuple(payload.get("evidenceRefs") or ()) == CORE_MISSING_BENCHMARK_RUNTIME_EVIDENCE_REFS
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
    state_flags_are_boolean = all(
        isinstance(source.get(key), bool)
        for key in (
            "benchmarkIdentityResolved",
            "assignmentEffectiveForAsOfDate",
            "assignmentVersionPresent",
            "entitlementAllowed",
        )
    )
    assignment_status = source.get("assignmentStatus")
    status_is_valid = assignment_status is None or (
        isinstance(assignment_status, str)
        and bool(assignment_status)
        and assignment_status == assignment_status.strip().lower()
    )
    expected_diagnostic = benchmark_assignment_diagnostic(
        benchmark_identity_resolved=source.get("benchmarkIdentityResolved") is True,
        assignment_effective_for_as_of_date=(source.get("assignmentEffectiveForAsOfDate") is True),
        assignment_status=(
            str(source["assignmentStatus"])
            if isinstance(source.get("assignmentStatus"), str)
            else None
        ),
        assignment_version_present=source.get("assignmentVersionPresent") is True,
    )
    return (
        _digest_is_valid(source, "receiptDigest")
        and state_flags_are_boolean
        and status_is_valid
        and source.get("productId") == "lotus-core:BenchmarkAssignment:v1"
        and source.get("sourceSystem") == "lotus-core"
        and source.get("route") == "/integration/portfolios/{portfolio_id}/benchmark-assignment"
        and source.get("asOfDate") == request.get("asOfDate")
        and source_generated is not None
        and source_generated <= evaluated_at_utc
        and source.get("freshness") == "current"
        and str(source.get("dataQualityStatus", "")).lower() == "complete"
        and source.get("entitlementAllowed") is True
        and source.get("assignmentDiagnostic") == expected_diagnostic
        and _is_sha256(source.get("contentHash"))
        and isinstance(source.get("productVersion"), str)
        and bool(str(source.get("productVersion")).strip())
    )


def _evaluation_is_valid(
    evaluation: Mapping[str, Any],
    source: Mapping[str, Any],
    request: Mapping[str, Any],
) -> bool:
    try:
        score = Decimal(str(evaluation.get("candidateScore")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    ready = source.get("assignmentDiagnostic") == "core_benchmark_assignment_ready"
    if (
        not _digest_is_valid(evaluation, "evaluationDigest")
        or evaluation.get("requestReceiptDigest") != request.get("requestDigest")
        or evaluation.get("assignmentStateDigest") != _assignment_state_digest(source)
        or evaluation.get("sourceRefsDigest") != sha256_json([dict(source)])
        or not _is_sha256(evaluation.get("sourceRefsDigest"))
        or not _is_sha256(evaluation.get("requestReceiptDigest"))
        or not _is_sha256(evaluation.get("assignmentStateDigest"))
        or evaluation.get("policyVersion") != request.get("policyVersion")
        or evaluation.get("family") != "missing_benchmark"
        or evaluation.get("unsupportedReasons") != []
        or score < Decimal("0")
        or score > Decimal("100")
    ):
        return False
    if ready:
        return (
            evaluation.get("outcome") == "not_eligible"
            and evaluation.get("missingBenchmarkReviewRequired") is False
            and tuple(evaluation.get("reasonCodes") or ()) == ("below_materiality",)
            and all(
                evaluation.get(key) is None
                for key in ("candidateIdHash", "signalIdHash", "evidencePacketIdHash")
            )
        )
    return (
        evaluation.get("outcome") == "candidate_created"
        and evaluation.get("missingBenchmarkReviewRequired") is True
        and tuple(evaluation.get("reasonCodes") or ()) == ("missing_benchmark", "review_required")
        and all(
            _is_sha256(evaluation.get(key))
            for key in ("candidateIdHash", "signalIdHash", "evidencePacketIdHash")
        )
    )


def _digest_is_valid(receipt: Mapping[str, Any], digest_key: str) -> bool:
    material = {key: value for key, value in receipt.items() if key != digest_key}
    return receipt.get(digest_key) == sha256_json(material)


def _assignment_state_digest(source: Mapping[str, Any]) -> str:
    return sha256_json(
        {
            key: source[key]
            for key in (
                "benchmarkIdentityResolved",
                "assignmentEffectiveForAsOfDate",
                "assignmentStatus",
                "assignmentVersionPresent",
                "assignmentDiagnostic",
            )
        }
    )


def _has_exact_keys(value: object, keys: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == keys


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None
