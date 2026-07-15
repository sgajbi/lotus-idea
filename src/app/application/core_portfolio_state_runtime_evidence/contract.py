from __future__ import annotations

from collections.abc import Mapping
from datetime import date
import re
from typing import Any

from app.application.core_portfolio_state_runtime_evidence.runtime_execution import (
    CORE_PORTFOLIO_STATE_REMAINING_BLOCKERS,
    CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS,
    CORE_PORTFOLIO_STATE_RUNTIME_BLOCKERS_SATISFIED,
    CORE_PORTFOLIO_STATE_RUNTIME_EVIDENCE_REFS,
    CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_SCHEMA_VERSION,
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


def core_portfolio_state_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (_TOP_KEYS, _TOP_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY}):
        return False
    if (
        payload.get("schemaVersion") != CORE_PORTFOLIO_STATE_RUNTIME_EXECUTION_SCHEMA_VERSION
        or payload.get("repository") != "lotus-idea"
        or payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value
        or payload.get("proofFamily") != "core_portfolio_state"
        or payload.get("proofType") != "lotus_core_baseline_portfolio_state_read"
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
    if claims.get("portfolioStateOwned") != "lotus-core" or any(
        value is not False for key, value in claims.items() if key != "portfolioStateOwned"
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
    source_generated = parse_timezone_aware_datetime(source.get("generatedAtUtc"))
    latest_evidence = parse_timezone_aware_datetime(source.get("latestEvidenceAtUtc"))
    try:
        date.fromisoformat(str(request.get("asOfDate")))
    except ValueError:
        return False
    if (
        request.get("requestDigest") != sha256_json(request_material)
        or source.get("receiptDigest") != sha256_json(source_material)
        or execution.get("status") != "completed"
        or tuple(execution.get("qualificationBlockers") or ())
        or request.get("evaluatedAtUtc") != execution.get("evaluatedAtUtc")
        or request.get("asOfDate") != source.get("asOfDate")
        or request.get("tenantIdHash") != source.get("responseTenantIdHash")
        or request.get("portfolioIdHash") != source.get("responsePortfolioIdHash")
        or request.get("correlationIdHash") != source.get("sourceCorrelationIdHash")
        or request.get("consumerSystem") != "lotus-idea"
        or request.get("snapshotMode") != "BASELINE"
        or tuple(request.get("requestedSections") or ()) != CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS
        or source.get("snapshotMode") != "BASELINE"
        or tuple(source.get("appliedSections") or ()) != CORE_PORTFOLIO_STATE_REQUIRED_SECTIONS
        or tuple(source.get("droppedSections") or ())
        or source.get("productId") != "lotus-core:PortfolioStateSnapshot:v1"
        or source.get("sourceSystem") != SourceSystem.LOTUS_CORE.value
        or source.get("productVersion") != "v1"
        or source.get("responseProductName") != "PortfolioStateSnapshot"
        or source.get("responseProductVersion") != "v1"
        or source.get("freshness") != EvidenceFreshness.CURRENT.value
        or source.get("dataQualityStatus") != "COMPLETE"
        or source.get("reconciliationStatus") != "COMPLETE"
        or source.get("sourceEvidenceCurrent") is not True
        or source_generated is None
        or latest_evidence is None
        or source_generated > evaluated
        or latest_evidence > source_generated
        or generated < evaluated
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
    if not all(
        isinstance(source.get(field), str) and str(source[field]).strip()
        for field in (
            "route",
            "requestFingerprint",
            "snapshotId",
            "restatementVersion",
            "policyVersion",
            "receiptDigest",
        )
    ):
        return False
    if (
        not isinstance(execution.get("diagnosticCode"), str)
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
    return evidence_class_can_clear(
        actual=EvidenceClass.RUNTIME_EXECUTION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None
