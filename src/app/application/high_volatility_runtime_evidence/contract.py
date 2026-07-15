from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.application.high_volatility_runtime_evidence.runtime_execution import (
    HIGH_VOLATILITY_REMAINING_BLOCKERS,
    HIGH_VOLATILITY_RUNTIME_BLOCKERS_SATISFIED,
    HIGH_VOLATILITY_RUNTIME_EVIDENCE_REFS,
    HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
)
from app.application.proof_provenance import AGGREGATE_PROOF_PROVENANCE_KEY
from app.application.risk_runtime_evidence import (
    runtime_execution_receipts_are_valid,
)
from app.domain import OpportunityFamily, SourceSystem
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
        "periodName",
        "requestFingerprint",
        "sourceReceipt",
        "persistenceReceipt",
        "qualificationBlockers",
    }
)
_NON_PROOF_CLAIM_KEYS = frozenset(
    {
        "officialRiskCalculationOwned",
        "drawdownRuntimeCertified",
        "dataMeshRuntimeCertified",
        "gatewayWorkbenchRuntimeObserved",
        "clientPublicationApproved",
        "deploymentCertified",
        "productionCertified",
        "supportedFeaturePromoted",
    }
)
_PRODUCT_ID = "lotus-risk:RiskMetricsReport:v1"


def high_volatility_runtime_execution_is_valid(payload: Mapping[str, Any]) -> bool:
    if set(payload) not in (
        _TOP_LEVEL_KEYS,
        _TOP_LEVEL_KEYS | {AGGREGATE_PROOF_PROVENANCE_KEY},
    ):
        return False
    if payload.get("schemaVersion") != HIGH_VOLATILITY_RUNTIME_EXECUTION_SCHEMA_VERSION:
        return False
    if payload.get("repository") != "lotus-idea":
        return False
    if payload.get("evidenceClass") != EvidenceClass.RUNTIME_EXECUTION.value:
        return False
    if payload.get("proofFamily") != "high_volatility":
        return False
    if payload.get("proofType") != "lotus_risk_high_volatility_candidate_persistence":
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
        HIGH_VOLATILITY_REMAINING_BLOCKERS
    ):
        return False
    if tuple(payload.get("evidenceRefs") or ()) != HIGH_VOLATILITY_RUNTIME_EVIDENCE_REFS:
        return False
    if tuple(payload.get("aggregateBlockersSatisfied") or ()) != (
        HIGH_VOLATILITY_RUNTIME_BLOCKERS_SATISFIED
    ):
        return False
    if not runtime_execution_receipts_are_valid(
        execution,
        generated_at_utc=generated_at_utc,
        product_id=_PRODUCT_ID,
        source_system=SourceSystem.LOTUS_RISK,
        family=OpportunityFamily.HIGH_VOLATILITY,
        period_name_required=True,
    ):
        return False
    return evidence_class_can_clear(
        actual=EvidenceClass.RUNTIME_EXECUTION,
        required=EvidenceClass.RUNTIME_EXECUTION,
    )
