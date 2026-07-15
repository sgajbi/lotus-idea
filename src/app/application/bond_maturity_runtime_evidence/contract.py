from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
import re
from typing import Any

from app.application.bond_maturity_runtime_evidence.runtime_execution import (
    BOND_MATURITY_REMAINING_BLOCKERS,
    BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED,
    BOND_MATURITY_RUNTIME_EVIDENCE_REFS,
    BOND_MATURITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
)
from app.application.core_runtime_evidence import sha256_json
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


def bond_maturity_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != BOND_MATURITY_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "bond_maturity"
        or payload.get("proofType") != "lotus_core_portfolio_maturity_summary_read"
        or payload.get("sourceAuthority") != SourceSystem.LOTUS_CORE.value
    ):
        return False
    generated = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if generated is None or not isinstance(execution, Mapping) or set(execution) != _EXECUTION_KEYS:
        return False
    if not isinstance(claims, Mapping) or set(claims) != _CLAIM_KEYS:
        return False
    if claims.get("maturityFactsOwned") != "lotus-core" or any(
        value is not False for key, value in claims.items() if key != "maturityFactsOwned"
    ):
        return False
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
        return False
    request_material = {key: request[key] for key in _REQUEST_KEYS if key != "requestDigest"}
    source_material = {key: source[key] for key in _SOURCE_KEYS if key != "receiptDigest"}
    if (
        request.get("requestDigest") != sha256_json(request_material)
        or source.get("receiptDigest") != sha256_json(source_material)
        or execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or request.get("evaluatedAtUtc") != execution.get("evaluatedAtUtc")
        or request.get("consumerSystem") != "lotus-idea"
        or request.get("includeProjected") is not False
        or source.get("includeProjected") is not False
        or request.get("asOfDate") != source.get("asOfDate")
        or request.get("asOfDate") != source.get("windowStartDate")
        or request.get("maturityWindowDays") != source.get("horizonDays")
        or request.get("tenantIdHash") != source.get("responseTenantIdHash")
        or request.get("portfolioIdHash") != source.get("responsePortfolioIdHash")
        or request.get("correlationIdHash") != source.get("sourceCorrelationIdHash")
        or source.get("productId") != "lotus-core:PortfolioMaturitySummary:v1"
        or source.get("sourceSystem") != SourceSystem.LOTUS_CORE.value
        or source.get("productVersion") != "v1"
        or source.get("route") != "/portfolios/{portfolio_id}/maturity-summary"
        or source.get("responseProductName") != "PortfolioMaturitySummary"
        or source.get("responseProductVersion") != "v1"
        or source.get("sourceProductName") != "HoldingsAsOf"
        or source.get("sourceProductVersion") != "v1"
        or source.get("upstreamProductId") != "lotus-core:HoldingsAsOf:v1"
        or source.get("upstreamProductName") != "HoldingsAsOf"
        or source.get("maturityBasis") != "CONTRACTUAL_INSTRUMENT_MATURITY_DATE"
        or source.get("freshness") != EvidenceFreshness.CURRENT.value
        or str(source.get("dataQualityStatus", "")).upper() != "COMPLETE"
        or str(source.get("supportabilityStatus", "")).upper() != "SUPPORTED"
        or tuple(source.get("supportabilityReasons") or ())
        or source.get("missingMaturityDateCount") != 0
        or source.get("unsupportedMaturityFeatureCount") != 0
        or str(source.get("reconciliationStatus", "")).upper() != "COMPLETE"
        or source.get("sourceEvidenceCurrent") is not True
    ):
        return False
    if not _scope_and_time_are_valid(
        request=request,
        source=source,
        evaluated=evaluated,
        generated=generated,
    ):
        return False
    if not _fact_posture_is_valid(execution=execution, source=source):
        return False
    request_hashes = (
        request.get("tenantIdHash"),
        request.get("portfolioIdHash"),
        request.get("correlationIdHash"),
        request.get("requestDigest"),
    )
    source_hashes = (
        source.get("contentHash"),
        source.get("sourceBatchFingerprint"),
        source.get("responseContentHash"),
        source.get("responseSourceDigest"),
    )
    if (
        not all(_is_sha256(value) for value in request_hashes + source_hashes)
        or not _is_sha256(source.get("upstreamContentHash"))
        or not _is_sha256(source.get("holdingsContentHash"))
        or source.get("holdingsContentHash") != source.get("upstreamContentHash")
        or len(set(source_hashes)) != 1
        or not isinstance(source.get("requestFingerprint"), str)
        or _REQUEST_FINGERPRINT_PATTERN.fullmatch(str(source["requestFingerprint"])) is None
    ):
        return False
    if not all(
        isinstance(source.get(field), str) and str(source[field]).strip()
        for field in ("snapshotId", "restatementVersion", "policyVersion", "receiptDigest")
    ):
        return False
    if (
        tuple(payload.get("aggregateBlockersSatisfied") or ())
        != BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED
        or tuple(payload.get("remainingCertificationBlockers") or ())
        != BOND_MATURITY_REMAINING_BLOCKERS
        or tuple(payload.get("evidenceRefs") or ()) != BOND_MATURITY_RUNTIME_EVIDENCE_REFS
    ):
        return False
    return evidence_class_can_clear(
        actual=EvidenceClass.RUNTIME_EXECUTION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )


def _scope_and_time_are_valid(
    *,
    request: Mapping[str, Any],
    source: Mapping[str, Any],
    evaluated: Any,
    generated: Any,
) -> bool:
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
        and source_generated <= evaluated
        and latest_evidence <= source_generated
        and generated >= evaluated
    )


def _fact_posture_is_valid(
    *,
    execution: Mapping[str, Any],
    source: Mapping[str, Any],
) -> bool:
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
