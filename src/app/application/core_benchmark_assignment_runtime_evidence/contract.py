from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import re
from typing import Any

from app.application.core_benchmark_assignment_runtime_evidence.runtime_execution import (
    CORE_BENCHMARK_ASSIGNMENT_REMAINING_BLOCKERS,
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_BLOCKERS_SATISFIED,
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EVIDENCE_REFS,
    CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_SCHEMA_VERSION,
)
from app.application.runtime_evidence import sha256_json
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.domain import EvidenceFreshness, SourceSystem
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
        "sourceReceipt",
        "assignmentStatus",
        "diagnosticCode",
        "qualificationBlockers",
    }
)
_REQUEST_KEYS = frozenset(
    {
        "tenantIdHash",
        "portfolioIdHash",
        "asOfDate",
        "reportingCurrency",
        "evaluatedAtUtc",
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
_CLAIM_KEYS = frozenset(
    {
        "benchmarkAssignmentOwned",
        "benchmarkAssignmentChanged",
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
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def core_benchmark_assignment_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if not _has_valid_payload_envelope(payload):
        return False
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if (
        generated is None
        or not _has_valid_execution_envelope(execution)
        or not _has_valid_no_claim_boundary(claims)
    ):
        return False
    assert isinstance(execution, Mapping)
    request = execution.get("requestReceipt")
    source = execution.get("sourceReceipt")
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if not _has_valid_receipt_envelopes(request=request, source=source, evaluated=evaluated):
        return False
    assert isinstance(request, Mapping)
    assert isinstance(source, Mapping)
    assert evaluated is not None
    return (
        _request_receipt_is_valid(request=request, source=source, execution=execution)
        and _source_receipt_is_valid(source=source, evaluated=evaluated)
        and _execution_success_is_valid(
            execution=execution, generated=generated, evaluated=evaluated
        )
        and _control_lists_are_valid(payload)
        and evidence_class_can_clear(
            actual=EvidenceClass.RUNTIME_EXECUTION, required=EvidenceClass.RUNTIME_EXECUTION
        )
    )


def _has_valid_payload_envelope(payload: Mapping[str, Any]) -> bool:
    return set(payload) in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}) and (
        payload.get("schemaVersion") == CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EXECUTION_SCHEMA_VERSION
        and payload.get("repository") == "lotus-idea"
        and payload.get("evidenceClass") == EvidenceClass.RUNTIME_EXECUTION.value
        and payload.get("proofFamily") == "core_benchmark_assignment"
        and payload.get("proofType") == "lotus_core_effective_dated_benchmark_assignment_read"
        and payload.get("sourceAuthority") == SourceSystem.LOTUS_CORE.value
    )


def _has_valid_execution_envelope(execution: object) -> bool:
    return isinstance(execution, Mapping) and set(execution) == _EXECUTION_KEYS


def _has_valid_no_claim_boundary(claims: object) -> bool:
    return (
        isinstance(claims, Mapping)
        and set(claims) == _CLAIM_KEYS
        and claims.get("benchmarkAssignmentOwned") == "lotus-core"
        and all(v is False for k, v in claims.items() if k != "benchmarkAssignmentOwned")
    )


def _has_valid_receipt_envelopes(
    *,
    request: object,
    source: object,
    evaluated: object,
) -> bool:
    return (
        isinstance(request, Mapping)
        and set(request) == _REQUEST_KEYS
        and isinstance(source, Mapping)
        and set(source) == _SOURCE_KEYS
        and evaluated is not None
    )


def _request_receipt_is_valid(
    *,
    request: Mapping[str, Any],
    source: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> bool:
    if (
        not _request_business_date_is_valid(request)
        or request.get("requestDigest") != _receipt_digest(request, "requestDigest")
        or request.get("evaluatedAtUtc") != execution.get("evaluatedAtUtc")
        or request.get("asOfDate") != source.get("asOfDate")
        or not _hash_fields_are_valid(request, ("tenantIdHash", "portfolioIdHash", "requestDigest"))
        or not _currency_is_valid(request.get("reportingCurrency"))
    ):
        return False
    return True


def _request_business_date_is_valid(request: Mapping[str, Any]) -> bool:
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except ValueError:
        return False
    return True


def _receipt_digest(receipt: Mapping[str, Any], digest_key: str) -> str:
    return sha256_json({k: receipt[k] for k in receipt if k != digest_key})


def _hash_fields_are_valid(receipt: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    return all(
        isinstance(receipt.get(key), str) and _SHA256_PATTERN.fullmatch(str(receipt[key]))
        for key in keys
    )


def _currency_is_valid(currency: object) -> bool:
    return currency is None or (
        isinstance(currency, str)
        and len(currency) == 3
        and currency.isalpha()
        and currency.isupper()
    )


def _source_receipt_is_valid(
    *,
    source: Mapping[str, Any],
    evaluated: Any,
) -> bool:
    source_generated = parse_timezone_aware_datetime(source.get("generatedAtUtc"))
    if (
        source.get("receiptDigest") != _receipt_digest(source, "receiptDigest")
        or source.get("productId") != "lotus-core:BenchmarkAssignment:v1"
        or source.get("sourceSystem") != SourceSystem.LOTUS_CORE.value
        or source.get("freshness") != EvidenceFreshness.CURRENT.value
        or source_generated is None
        or source_generated > evaluated
    ):
        return False
    if not all(
        isinstance(source.get(key), str) and str(source[key]).strip()
        for key in ("productVersion", "route", "contentHash", "dataQualityStatus", "receiptDigest")
    ):
        return False
    return True


def _execution_success_is_valid(
    *,
    execution: Mapping[str, Any],
    generated: Any,
    evaluated: Any,
) -> bool:
    if (
        not isinstance(execution.get("diagnosticCode"), str)
        or not str(execution["diagnosticCode"]).strip()
        or generated < evaluated
        or execution.get("status") != "completed"
        or execution.get("assignmentStatus") != "active"
        or tuple(execution.get("qualificationBlockers") or ())
    ):
        return False
    return True


def _control_lists_are_valid(payload: Mapping[str, Any]) -> bool:
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != CORE_BENCHMARK_ASSIGNMENT_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if (
        tuple(payload.get("remainingCertificationBlockers") or ())
        != CORE_BENCHMARK_ASSIGNMENT_REMAINING_BLOCKERS
        or tuple(payload.get("evidenceRefs") or ())
        != CORE_BENCHMARK_ASSIGNMENT_RUNTIME_EVIDENCE_REFS
    ):
        return False
    return True
