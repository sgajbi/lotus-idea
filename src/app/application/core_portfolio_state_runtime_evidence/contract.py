from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any

from app.application.core_portfolio_state_runtime_evidence.runtime_execution import (
    CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS,
    CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS,
    CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED,
    CORE_PORTFOLIO_STATE_RUNTIME_EVIDENCE_REFS,
    CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_SCHEMA_VERSION,
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
        "diagnosticCode",
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
        "snapshotMode",
        "requestedSections",
        "correlationIdHash",
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
        "responseProductName",
        "responseProductVersion",
        "responseTenantIdHash",
        "responsePortfolioIdHash",
        "snapshotMode",
        "requestFingerprint",
        "snapshotId",
        "sourceBatchFingerprint",
        "responseContentHash",
        "responseSourceDigest",
        "restatementVersion",
        "reconciliationStatus",
        "latestEvidenceAtUtc",
        "sourceEvidenceCurrent",
        "policyVersion",
        "sourceCorrelationIdHash",
        "appliedSections",
        "droppedSections",
        "receiptDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "portfolioStateOwned",
        "portfolioStateMutated",
        "portfolioAccountingAuthorityTransferred",
        "reconciliationAuthorityTransferred",
        "rebalanceConstructed",
        "orderExecutionReady",
        "riskMethodologyCertified",
        "performanceMethodologyCertified",
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
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class _RuntimeExecutionValidationParts:
    generated_at_utc: datetime
    evaluated_at_utc: datetime
    execution: Mapping[str, Any]
    request: Mapping[str, Any]
    source: Mapping[str, Any]


def core_portfolio_state_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    parts = _runtime_execution_validation_parts(payload)
    return (
        parts is not None
        and _request_receipt_is_valid(parts)
        and _source_receipt_is_valid(parts)
        and _execution_closure_is_valid(payload, parts)
        and evidence_class_can_clear(
            actual=EvidenceClass.RUNTIME_EXECUTION,
            required=EvidenceClass.RUNTIME_EXECUTION,
        )
    )


def _runtime_execution_validation_parts(
    payload: Mapping[str, Any],
) -> _RuntimeExecutionValidationParts | None:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return None
    if (
        payload.get("schemaVersion") != CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "core_portfolio_state"
        or payload.get("proofType") != "lotus_core_baseline_portfolio_state_read"
        or payload.get("sourceAuthority") != SourceSystem.LOTUS_CORE.value
    ):
        return None
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if generated is None or not isinstance(execution, Mapping) or set(execution) != _EXECUTION_KEYS:
        return None
    if not _non_proof_claims_are_valid(claims):
        return None
    request = execution.get("requestReceipt")
    source = execution.get("sourceReceipt")
    evaluated = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if (
        not isinstance(request, Mapping)
        or set(request) != _REQUEST_KEYS
        or not isinstance(source, Mapping)
        or set(source) != _SOURCE_KEYS
        or evaluated is None
    ):
        return None
    return _RuntimeExecutionValidationParts(
        generated_at_utc=generated,
        evaluated_at_utc=evaluated,
        execution=execution,
        request=request,
        source=source,
    )


def _non_proof_claims_are_valid(claims: object) -> bool:
    return (
        isinstance(claims, Mapping)
        and set(claims) == _CLAIM_KEYS
        and claims.get("portfolioStateOwned") == "lotus-core"
        and all(value is False for key, value in claims.items() if key != "portfolioStateOwned")
    )


def _request_receipt_is_valid(parts: _RuntimeExecutionValidationParts) -> bool:
    request = parts.request
    request_material = {key: request[key] for key in _REQUEST_KEYS if key != "requestDigest"}
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except ValueError:
        return False
    if (
        request.get("requestDigest") != sha256_json(request_material)
        or request.get("evaluatedAtUtc") != parts.execution.get("evaluatedAtUtc")
        or request.get("consumerSystem") != "lotus-idea"
        or request.get("snapshotMode") != "BASELINE"
        or tuple(request.get("requestedSections") or ()) != CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS
    ):
        return False
    hash_fields = (
        "tenantIdHash",
        "portfolioIdHash",
        "correlationIdHash",
        "requestDigest",
    )
    if not all(_is_sha256(request.get(field)) for field in hash_fields):
        return False
    return True


def _source_receipt_is_valid(parts: _RuntimeExecutionValidationParts) -> bool:
    source = parts.source
    source_material = {key: source[key] for key in _SOURCE_KEYS if key != "receiptDigest"}
    return (
        source.get("receiptDigest") == sha256_json(source_material)
        and _source_scope_matches_request(parts)
        and _source_product_and_posture_are_valid(source)
        and _source_temporal_posture_is_valid(parts)
        and _source_hash_identity_is_valid(source)
        and _source_required_strings_are_present(source)
    )


def _source_scope_matches_request(parts: _RuntimeExecutionValidationParts) -> bool:
    request = parts.request
    source = parts.source
    return (
        request.get("asOfDate") == source.get("asOfDate")
        and request.get("tenantIdHash") == source.get("responseTenantIdHash")
        and request.get("portfolioIdHash") == source.get("responsePortfolioIdHash")
        and request.get("correlationIdHash") == source.get("sourceCorrelationIdHash")
    )


def _source_product_and_posture_are_valid(source: Mapping[str, Any]) -> bool:
    return (
        source.get("snapshotMode") == "BASELINE"
        and tuple(source.get("appliedSections") or ()) == CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS
        and not tuple(source.get("droppedSections") or ())
        and source.get("productId") == "lotus-core:PortfolioStateSnapshot:v1"
        and source.get("sourceSystem") == SourceSystem.LOTUS_CORE.value
        and source.get("productVersion") == "v1"
        and source.get("responseProductName") == "PortfolioStateSnapshot"
        and source.get("responseProductVersion") == "v1"
        and source.get("freshness") == EvidenceFreshness.CURRENT.value
        and source.get("dataQualityStatus") == "COMPLETE"
        and source.get("reconciliationStatus") == "COMPLETE"
        and source.get("sourceEvidenceCurrent") is True
    )


def _source_temporal_posture_is_valid(parts: _RuntimeExecutionValidationParts) -> bool:
    source = parts.source
    source_generated = parse_timezone_aware_datetime(source.get("generatedAtUtc"))
    latest_evidence = parse_timezone_aware_datetime(source.get("latestEvidenceAtUtc"))
    return (
        source_generated is not None
        and latest_evidence is not None
        and source_generated <= parts.generated_at_utc
        and latest_evidence <= source_generated
        and parts.generated_at_utc >= parts.evaluated_at_utc
    )


def _source_hash_identity_is_valid(source: Mapping[str, Any]) -> bool:
    source_hash_fields = (
        "contentHash",
        "sourceBatchFingerprint",
        "responseContentHash",
        "responseSourceDigest",
    )
    if not all(_is_sha256(source.get(field)) for field in source_hash_fields):
        return False
    if len({source.get(field) for field in source_hash_fields}) != 1:
        return False
    return True


def _source_required_strings_are_present(source: Mapping[str, Any]) -> bool:
    return all(
        isinstance(source.get(field), str) and str(source[field]).strip()
        for field in (
            "route",
            "requestFingerprint",
            "snapshotId",
            "restatementVersion",
            "policyVersion",
            "receiptDigest",
        )
    )


def _execution_closure_is_valid(
    payload: Mapping[str, Any],
    parts: _RuntimeExecutionValidationParts,
) -> bool:
    execution = parts.execution
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or not isinstance(execution.get("diagnosticCode"), str)
        or not str(execution["diagnosticCode"]).strip()
    ):
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED
        or tuple(payload.get("remainingCertificationBlockers") or ())
        != CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS
        or tuple(payload.get("evidenceRefs") or ()) != CORE_PORTFOLIO_STATE_RUNTIME_EVIDENCE_REFS
    ):
        return False
    return True


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
