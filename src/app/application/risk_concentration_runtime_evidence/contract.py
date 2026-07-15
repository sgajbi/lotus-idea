from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.risk_concentration_runtime_evidence.runtime_execution import (
    RISK_CONCENTRATION_REMAINING_BLOCKERS,
    RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED,
    RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS,
    RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION,
    is_sha256,
    sha256_json,
    source_evidence_hash,
)
from app.domain import EvidenceFreshness, OpportunityFamily, SourceSystem
from app.domain.proof_evidence import (
    EvidenceClass,
    evidence_class_can_clear,
    parse_timezone_aware_datetime,
)

_TOP_LEVEL_KEYS = frozenset(
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
        "durableStorageBacked",
        "evaluatedAtUtc",
        "asOfDate",
        "requestFingerprint",
        "sourceReceipt",
        "persistenceReceipt",
        "qualificationBlockers",
    }
)
_SOURCE_RECEIPT_KEYS = frozenset(
    {
        "productId",
        "sourceSystem",
        "productVersion",
        "asOfDate",
        "generatedAtUtc",
        "contentHash",
        "dataQualityStatus",
        "freshness",
        "sourceReceiptSha256",
    }
)
_PERSISTENCE_RECEIPT_KEYS = frozenset(
    {
        "decision",
        "candidateFamily",
        "candidateLifecycleStatus",
        "sourceEvidenceHash",
        "scopeFingerprint",
        "persistedAtUtc",
        "persistenceReceiptSha256",
    }
)
_NON_PROOF_CLAIM_KEYS = frozenset(
    {
        "officialRiskCalculationOwned",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "clientPublicationApproved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
    }
)
_PRODUCT_ID = "lotus-risk:ConcentrationRiskReport:v1"


def risk_concentration_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (
        _TOP_LEVEL_KEYS,
        _TOP_LEVEL_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY},
    ):
        return False
    if payload.get("schemaVersion") != RISK_CONCENTRATION_RUNTIME_EXECUTION_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        return False
    if payload.get("proofFamily") != "risk_concentration":
        return False
    if payload.get("proofType") != "lotus_risk_concentration_candidate_persistence":
        return False
    if payload.get("sourceAuthority") != SourceSystem.LOTUS_RISK.value:
        return False
    generated_at_utc = parse_timezone_aware_datetime(payload.get("generatedAtUtc"))
    execution = payload.get("execution")
    claims = payload.get("nonProofClaims")
    if (
        generated_at_utc is None
        or not isinstance(execution, Mapping)
        or set(execution) != _EXECUTION_KEYS
    ):
        return False
    if not isinstance(claims, Mapping) or set(claims) != _NON_PROOF_CLAIM_KEYS:
        return False
    if claims.get("officialRiskCalculationOwned") != "lotus-risk":
        return False
    if any(
        value is not False for key, value in claims.items() if key != "officialRiskCalculationOwned"
    ):
        return False
    if tuple(payload.get("remainingCertificationBlockers") or ()) != (
        RISK_CONCENTRATION_REMAINING_BLOCKERS
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != RISK_CONCENTRATION_RUNTIME_EVIDENCE_REFS:
        return False
    if tuple(payload.get("aggregateBlockersSatisfied") or ()) != (
        RISK_CONCENTRATION_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if not _execution_is_valid(execution, generated_at_utc=generated_at_utc):
        return False
    return evidence_class_can_clear(
        actual=EvidenceClass.RUNTIME_EXECUTION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )


def _execution_is_valid(execution: Mapping[str, Any], *, generated_at_utc: datetime) -> bool:
    if execution.get("status") != "completed" or execution.get("durableStorageBacked") is not True:
        return False
    if tuple(execution.get("qualificationBlockers") or ()):
        return False
    evaluated_at_utc = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if evaluated_at_utc is None or evaluated_at_utc > generated_at_utc:
        return False
    try:
        as_of_date = date.fromisoformat(str(execution.get("asOfDate")))
    except ValueError:
        return False
    if not is_sha256(execution.get("requestFingerprint")):
        return False
    source = execution.get("sourceReceipt")
    persistence = execution.get("persistenceReceipt")
    if not _source_receipt_is_valid(
        source,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
    ):
        return False
    if not _persistence_receipt_is_valid(persistence, generated_at_utc=generated_at_utc):
        return False
    assert isinstance(source, Mapping) and isinstance(persistence, Mapping)
    return persistence.get("sourceEvidenceHash") == source_evidence_hash(source)


def _source_receipt_is_valid(
    value: object,
    *,
    as_of_date: date,
    evaluated_at_utc: datetime,
) -> bool:
    if not isinstance(value, Mapping) or set(value) != _SOURCE_RECEIPT_KEYS:
        return False
    if (
        value.get("productId") != _PRODUCT_ID
        or value.get("sourceSystem") != SourceSystem.LOTUS_RISK.value
    ):
        return False
    if (
        value.get("asOfDate") != as_of_date.isoformat()
        or value.get("freshness") != EvidenceFreshness.CURRENT.value
    ):
        return False
    if not all(
        isinstance(value.get(key), str) and str(value[key]).strip()
        for key in ("productVersion", "contentHash", "dataQualityStatus")
    ):
        return False
    source_generated_at = parse_timezone_aware_datetime(value.get("generatedAtUtc"))
    if source_generated_at is None or source_generated_at > evaluated_at_utc:
        return False
    unsigned = {key: item for key, item in value.items() if key != "sourceReceiptSha256"}
    return value.get("sourceReceiptSha256") == sha256_json(unsigned)


def _persistence_receipt_is_valid(value: object, *, generated_at_utc: datetime) -> bool:
    if not isinstance(value, Mapping) or set(value) != _PERSISTENCE_RECEIPT_KEYS:
        return False
    if value.get("decision") not in {"accepted", "replayed"}:
        return False
    if value.get("candidateFamily") != OpportunityFamily.CONCENTRATION.value:
        return False
    if not all(is_sha256(value.get(key)) for key in ("sourceEvidenceHash", "scopeFingerprint")):
        return False
    persisted_at_utc = parse_timezone_aware_datetime(value.get("persistedAtUtc"))
    if persisted_at_utc is None or persisted_at_utc > generated_at_utc:
        return False
    unsigned = {key: item for key, item in value.items() if key != "persistenceReceiptSha256"}
    return value.get("persistenceReceiptSha256") == sha256_json(unsigned)
