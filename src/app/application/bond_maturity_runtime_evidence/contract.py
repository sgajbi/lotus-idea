from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
from typing import Any

from app.application.bond_maturity_runtime_evidence.runtime_execution import (
    BOND_MATURITY_REMAINING_BLOCKERS,
    BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED,
    BOND_MATURITY_RUNTIME_EVIDENCE_REFS,
    BOND_MATURITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
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
        "opportunityDetected",
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
        "maturityWindowDays",
        "includeProjected",
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
        "sourceProductName",
        "sourceProductVersion",
        "windowStartDate",
        "windowEndDate",
        "horizonDays",
        "includeProjected",
        "maturityBasis",
        "nextMaturityDate",
        "maturingHoldingCount",
        "maturityBearingHoldingCount",
        "missingMaturityDateCount",
        "unsupportedMaturityFeatureCount",
        "supportabilityStatus",
        "supportabilityReasons",
        "requestFingerprint",
        "snapshotId",
        "sourceBatchFingerprint",
        "responseContentHash",
        "responseSourceDigest",
        "upstreamProductId",
        "upstreamProductName",
        "holdingsContentHash",
        "upstreamContentHash",
        "restatementVersion",
        "reconciliationStatus",
        "latestEvidenceAtUtc",
        "sourceEvidenceCurrent",
        "policyVersion",
        "sourceCorrelationIdHash",
        "receiptDigest",
    }
)
_CLAIM_KEYS = frozenset(
    {
        "maturityFactsOwned",
        "portfolioAccountingAuthorityTransferred",
        "productRecommendationProduced",
        "reinvestmentAdviceProduced",
        "cashflowForecastProduced",
        "suitabilityCertified",
        "riskMethodologyCertified",
        "complianceApproved",
        "rebalanceConstructed",
        "orderExecutionReady",
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
_REQUEST_FINGERPRINT_PATTERN = re.compile(r"^maturity_summary:[0-9a-f]{16}$")


@dataclass(frozen=True)
class _RuntimeExecutionValidationParts:
    generated_at_utc: datetime
    evaluated_at_utc: datetime
    execution: Mapping[str, Any]
    request: Mapping[str, Any]
    source: Mapping[str, Any]


def bond_maturity_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    parts = _runtime_execution_validation_parts(payload)
    return (
        parts is not None
        and _request_receipt_is_valid(parts)
        and _source_receipt_is_valid(parts)
        and _fact_posture_is_valid(parts)
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
        payload.get("schemaVersion") != BOND_MATURITY_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "bond_maturity"
        or payload.get("proofType") != "lotus_core_portfolio_maturity_summary_read"
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
        and claims.get("maturityFactsOwned") == "lotus-core"
        and all(value is False for key, value in claims.items() if key != "maturityFactsOwned")
    )


def _request_receipt_is_valid(parts: _RuntimeExecutionValidationParts) -> bool:
    request = parts.request
    request_material = {key: request[key] for key in _REQUEST_KEYS if key != "requestDigest"}
    if (
        request.get("requestDigest") != sha256_json(request_material)
        or request.get("evaluatedAtUtc") != parts.execution.get("evaluatedAtUtc")
        or request.get("consumerSystem") != "lotus-idea"
        or request.get("includeProjected") is not False
    ):
        return False
    request_hashes = (
        request.get("tenantIdHash"),
        request.get("portfolioIdHash"),
        request.get("correlationIdHash"),
        request.get("requestDigest"),
    )
    return all(_is_sha256(value) for value in request_hashes)


def _source_receipt_is_valid(parts: _RuntimeExecutionValidationParts) -> bool:
    source = parts.source
    source_material = {key: source[key] for key in _SOURCE_KEYS if key != "receiptDigest"}
    return (
        source.get("receiptDigest") == sha256_json(source_material)
        and _source_scope_matches_request(parts)
        and _source_product_and_posture_are_valid(source)
        and _source_window_and_temporal_posture_are_valid(parts)
        and _source_hash_identity_is_valid(source)
        and _source_required_strings_are_present(source)
    )


def _source_scope_matches_request(parts: _RuntimeExecutionValidationParts) -> bool:
    request = parts.request
    source = parts.source
    return (
        request.get("asOfDate") == source.get("asOfDate")
        and request.get("asOfDate") == source.get("windowStartDate")
        and request.get("maturityWindowDays") == source.get("horizonDays")
        and request.get("tenantIdHash") == source.get("responseTenantIdHash")
        and request.get("portfolioIdHash") == source.get("responsePortfolioIdHash")
        and request.get("correlationIdHash") == source.get("sourceCorrelationIdHash")
    )


def _source_product_and_posture_are_valid(source: Mapping[str, Any]) -> bool:
    return (
        source.get("includeProjected") is False
        and source.get("productId") == "lotus-core:PortfolioMaturitySummary:v1"
        and source.get("sourceSystem") == SourceSystem.LOTUS_CORE.value
        and source.get("productVersion") == "v1"
        and source.get("route") == "/portfolios/{portfolio_id}/maturity-summary"
        and source.get("responseProductName") == "PortfolioMaturitySummary"
        and source.get("responseProductVersion") == "v1"
        and source.get("sourceProductName") == "HoldingsAsOf"
        and source.get("sourceProductVersion") == "v1"
        and source.get("upstreamProductId") == "lotus-core:HoldingsAsOf:v1"
        and source.get("upstreamProductName") == "HoldingsAsOf"
        and source.get("maturityBasis") == "CONTRACTUAL_INSTRUMENT_MATURITY_DATE"
        and source.get("freshness") == EvidenceFreshness.CURRENT.value
        and str(source.get("dataQualityStatus", "")).upper() == "COMPLETE"
        and str(source.get("supportabilityStatus", "")).upper() == "SUPPORTED"
        and not tuple(source.get("supportabilityReasons") or ())
        and source.get("missingMaturityDateCount") == 0
        and source.get("unsupportedMaturityFeatureCount") == 0
        and str(source.get("reconciliationStatus", "")).upper() == "COMPLETE"
        and source.get("sourceEvidenceCurrent") is True
    )


def _source_window_and_temporal_posture_are_valid(
    parts: _RuntimeExecutionValidationParts,
) -> bool:
    request = parts.request
    source = parts.source
    try:
        as_of = date.fromisoformat(str(request.get("asOfDate")))
        window_end = date.fromisoformat(str(source.get("windowEndDate")))
    except ValueError:
        return False
    horizon = request.get("maturityWindowDays")
    source_generated = parse_timezone_aware_datetime(source.get("generatedAtUtc"))
    latest_evidence = parse_timezone_aware_datetime(source.get("latestEvidenceAtUtc"))
    return (
        isinstance(horizon, int)
        and 1 <= horizon <= 366
        and window_end == as_of + timedelta(days=horizon)
        and source_generated is not None
        and latest_evidence is not None
        and source_generated <= parts.evaluated_at_utc
        and latest_evidence <= source_generated
        and parts.generated_at_utc >= parts.evaluated_at_utc
    )


def _source_hash_identity_is_valid(source: Mapping[str, Any]) -> bool:
    source_hashes = (
        source.get("contentHash"),
        source.get("sourceBatchFingerprint"),
        source.get("responseContentHash"),
        source.get("responseSourceDigest"),
    )
    if not all(_is_sha256(value) for value in source_hashes):
        return False
    if not _is_sha256(source.get("upstreamContentHash")) or not _is_sha256(
        source.get("holdingsContentHash")
    ):
        return False
    return (
        source.get("holdingsContentHash") == source.get("upstreamContentHash")
        and len(set(source_hashes)) == 1
        and isinstance(source.get("requestFingerprint"), str)
        and _REQUEST_FINGERPRINT_PATTERN.fullmatch(str(source["requestFingerprint"])) is not None
    )


def _source_required_strings_are_present(source: Mapping[str, Any]) -> bool:
    return all(
        isinstance(source.get(field), str) and str(source[field]).strip()
        for field in ("snapshotId", "restatementVersion", "policyVersion", "receiptDigest")
    )


def _execution_closure_is_valid(
    payload: Mapping[str, Any],
    parts: _RuntimeExecutionValidationParts,
) -> bool:
    execution = parts.execution
    if (
        execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or tuple(payload.get("aggregateBlockersSatisfied") or ())
        != BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED
        or tuple(payload.get("remainingCertificationBlockers") or ())
        != BOND_MATURITY_REMAINING_BLOCKERS
        or tuple(payload.get("evidenceRefs") or ()) != BOND_MATURITY_RUNTIME_EVIDENCE_REFS
    ):
        return False
    return True


def _fact_posture_is_valid(
    parts: _RuntimeExecutionValidationParts,
) -> bool:
    execution = parts.execution
    source = parts.source
    counts = (
        source.get("maturingHoldingCount"),
        source.get("maturityBearingHoldingCount"),
        source.get("missingMaturityDateCount"),
        source.get("unsupportedMaturityFeatureCount"),
    )
    if not all(isinstance(value, int) and value >= 0 for value in counts):
        return False
    if int(source["missingMaturityDateCount"]) > int(source["maturityBearingHoldingCount"]):
        return False
    maturing_count = int(source["maturingHoldingCount"])
    opportunity_detected = execution.get("opportunityDetected")
    diagnostic = execution.get("diagnosticCode")
    next_maturity = source.get("nextMaturityDate")
    if maturing_count == 0:
        return (
            next_maturity is None
            and opportunity_detected is False
            and diagnostic == "core_maturity_window_empty"
        )
    if opportunity_detected is not True or diagnostic != "core_maturity_evidence_ready":
        return False
    try:
        next_date = date.fromisoformat(str(next_maturity))
        window_start = date.fromisoformat(str(source.get("windowStartDate")))
        window_end = date.fromisoformat(str(source.get("windowEndDate")))
    except ValueError:
        return False
    return window_start <= next_date <= window_end


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
