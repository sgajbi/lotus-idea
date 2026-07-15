from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import re
from typing import Any

from app.application.core_runtime_evidence import (
    format_utc,
    identity_hash,
    require_aware,
    sha256_json,
    source_ref_receipt,
)
from app.domain import EvidenceFreshness, SourceSystem
from app.domain.proof_evidence import EvidenceClass
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
)

BOND_MATURITY_RUNTIME_EXECUTION_ENV = "LOTUS_IDEA_BOND_MATURITY_LIVE_PROOF"
BOND_MATURITY_RUNTIME_EXECUTION_SCHEMA_VERSION = (
    "lotus-idea.bond-maturity.runtime-execution.v2"
)
BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED = (
    "opportunity_archetype_maturity_live_core_source_proof_missing",
)
BOND_MATURITY_REMAINING_BLOCKERS = (
    "opportunity_archetype_workbench_product_proof_missing",
    "opportunity_archetype_data_mesh_not_certified",
    "opportunity_archetype_client_publication_not_ready",
    "opportunity_archetype_supported_feature_promotion_missing",
    "deployment_certification_missing",
    "production_certification_missing",
)
BOND_MATURITY_RUNTIME_EVIDENCE_REFS = (
    "src/app/application/bond_maturity_runtime_evidence/runtime_execution.py",
    "src/app/application/bond_maturity_runtime_evidence/contract.py",
    "src/app/application/core_runtime_evidence/receipts.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "scripts/bond_maturity_runtime_evidence/generate_runtime_execution.py",
    "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json",
    "make bond-maturity-live-proof-contract-gate",
)

_MATURITY_PRODUCT_ID = "lotus-core:PortfolioMaturitySummary:v1"
_MATURITY_PRODUCT_NAME = "PortfolioMaturitySummary"
_HOLDINGS_PRODUCT_ID = "lotus-core:HoldingsAsOf:v1"
_HOLDINGS_PRODUCT_NAME = "HoldingsAsOf"
_PRODUCT_VERSION = "v1"
_MATURITY_BASIS = "CONTRACTUAL_INSTRUMENT_MATURITY_DATE"
_CONSUMER_SYSTEM = "lotus-idea"
_COMPLETE = "COMPLETE"
_SUPPORTED = "SUPPORTED"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUEST_FINGERPRINT_PATTERN = re.compile(r"^maturity_summary:[0-9a-f]{16}$")


@dataclass(frozen=True)
class EvaluateBondMaturityReadiness:
    tenant_id: str
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    maturity_window_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id.strip() or not self.portfolio_id.strip():
            raise ValueError("tenant_id and portfolio_id are required")
        if self.maturity_window_days < 1 or self.maturity_window_days > 366:
            raise ValueError("maturity_window_days must be between 1 and 366")
        require_aware(self.evaluated_at_utc, "evaluated_at_utc")
        if self.correlation_id is not None and not self.correlation_id.strip():
            raise ValueError("correlation_id must not be blank")


@dataclass(frozen=True)
class BondMaturityReadinessResult:
    command: EvaluateBondMaturityReadiness
    evidence: CoreBondMaturityEvidence


def evaluate_bond_maturity_readiness(
    command: EvaluateBondMaturityReadiness,
    *,
    core_source: CoreBondMaturitySourcePort,
) -> BondMaturityReadinessResult:
    evidence = core_source.fetch_bond_maturity_evidence(
        CoreBondMaturityEvidenceRequest(
            tenant_id=command.tenant_id,
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            maturity_window_days=command.maturity_window_days,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
    )
    return BondMaturityReadinessResult(command=command, evidence=evidence)


def build_bond_maturity_runtime_execution(
    *,
    generated_at_utc: datetime,
    result: BondMaturityReadinessResult,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    blockers = _qualification_blockers(result.command, result.evidence)
    return _payload(
        generated_at_utc=generated_at_utc,
        command=result.command,
        status="completed",
        source_receipt=_source_receipt(result.evidence),
        diagnostic_code=result.evidence.maturity_diagnostic or "core_maturity_unknown",
        opportunity_detected=(result.evidence.source_reported_maturing_position_count or 0) > 0,
        qualification_blockers=blockers,
    )


def build_blocked_bond_maturity_runtime_execution(
    *,
    generated_at_utc: datetime,
    command: EvaluateBondMaturityReadiness,
    error_code: str,
) -> dict[str, Any]:
    require_aware(generated_at_utc, "generated_at_utc")
    return _payload(
        generated_at_utc=generated_at_utc,
        command=command,
        status="blocked",
        source_receipt=None,
        diagnostic_code=error_code,
        opportunity_detected=False,
        qualification_blockers=("core_maturity_source_execution_blocked", error_code),
    )


def _payload(
    *,
    generated_at_utc: datetime,
    command: EvaluateBondMaturityReadiness,
    status: str,
    source_receipt: dict[str, Any] | None,
    diagnostic_code: str,
    opportunity_detected: bool,
    qualification_blockers: tuple[str, ...],
) -> dict[str, Any]:
    blockers = tuple(dict.fromkeys(qualification_blockers))
    return {
        "schemaVersion": BOND_MATURITY_RUNTIME_EXECUTION_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "evidenceClass": EvidenceClass.RUNTIME_EXECUTION.value,
        "proofFamily": "bond_maturity",
        "proofType": "lotus_core_portfolio_maturity_summary_read",
        "sourceAuthority": SourceSystem.LOTUS_CORE.value,
        "generatedAtUtc": format_utc(generated_at_utc),
        "execution": {
            "status": status,
            "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
            "requestReceipt": _request_receipt(command),
            "sourceReceipt": source_receipt,
            "diagnosticCode": diagnostic_code,
            "opportunityDetected": opportunity_detected,
            "qualificationBlockers": list(blockers),
        },
        "aggregateBlockersSatisfied": (
            list(BOND_MATURITY_RUNTIME_BLOCKERS_SATISFIED) if not blockers else []
        ),
        "remainingCertificationBlockers": list(BOND_MATURITY_REMAINING_BLOCKERS),
        "evidenceRefs": list(BOND_MATURITY_RUNTIME_EVIDENCE_REFS),
        "nonProofClaims": {
            "maturityFactsOwned": "lotus-core",
            "portfolioAccountingAuthorityTransferred": False,
            "productRecommendationProduced": False,
            "reinvestmentAdviceProduced": False,
            "cashflowForecastProduced": False,
            "suitabilityCertified": False,
            "riskMethodologyCertified": False,
            "complianceApproved": False,
            "rebalanceConstructed": False,
            "orderExecutionReady": False,
            "dataMeshRuntimeCertified": False,
            "gatewayWorkbenchRuntimeObserved": False,
            "clientPublicationApproved": False,
            "deploymentCertified": False,
            "productionCertified": False,
            "supportedFeaturePromoted": False,
            "ideaPersistenceRequired": False,
        },
    }


def _qualification_blockers(
    command: EvaluateBondMaturityReadiness,
    evidence: CoreBondMaturityEvidence,
) -> tuple[str, ...]:
    maturity_ref = evidence.maturity_fact_ref
    holdings_ref = evidence.holdings_ref
    blockers: list[str] = []
    if (
        maturity_ref is None
        or maturity_ref.source_system is not SourceSystem.LOTUS_CORE
        or maturity_ref.product_id != _MATURITY_PRODUCT_ID
    ):
        blockers.append("core_maturity_source_ref_missing")
    elif maturity_ref.as_of_date != command.as_of_date:
        blockers.append("core_maturity_scope_mismatch")
    elif maturity_ref.generated_at_utc > command.evaluated_at_utc:
        blockers.append("core_maturity_source_time_invalid")
    elif maturity_ref.freshness is not EvidenceFreshness.CURRENT:
        blockers.append("core_maturity_evidence_not_current")
    if (
        holdings_ref is None
        or holdings_ref.source_system is not SourceSystem.LOTUS_CORE
        or holdings_ref.product_id != _HOLDINGS_PRODUCT_ID
    ):
        blockers.append("core_maturity_upstream_holdings_ref_missing")
    elif holdings_ref.as_of_date != command.as_of_date:
        blockers.append("core_maturity_upstream_scope_mismatch")
    elif holdings_ref.freshness is not EvidenceFreshness.CURRENT:
        blockers.append("core_maturity_upstream_not_current")
    if not evidence.entitlement_allowed:
        blockers.append("core_maturity_entitlement_denied")
    if (
        evidence.response_product_name != _MATURITY_PRODUCT_NAME
        or evidence.response_product_version != _PRODUCT_VERSION
        or evidence.source_product_name != _HOLDINGS_PRODUCT_NAME
        or evidence.source_product_version != _PRODUCT_VERSION
    ):
        blockers.append("core_maturity_product_identity_mismatch")
    if (
        evidence.response_tenant_id != command.tenant_id
        or evidence.response_portfolio_id != command.portfolio_id
    ):
        blockers.append("core_maturity_response_scope_mismatch")
    expected_window_end = command.as_of_date + timedelta(days=command.maturity_window_days)
    if (
        evidence.window_start_date != command.as_of_date
        or evidence.window_end_date != expected_window_end
        or evidence.horizon_days != command.maturity_window_days
        or evidence.include_projected is not False
    ):
        blockers.append("core_maturity_window_scope_mismatch")
    if evidence.maturity_basis != _MATURITY_BASIS:
        blockers.append("core_maturity_basis_unsupported")
    if not _counts_are_valid(evidence):
        blockers.append("core_maturity_counts_invalid")
    if not _maturity_fact_is_consistent(evidence):
        blockers.append("core_maturity_fact_inconsistent")
    if (evidence.supportability_status or "").upper() != _SUPPORTED:
        blockers.append("core_maturity_supportability_not_supported")
    if evidence.supportability_reasons:
        blockers.append("core_maturity_supportability_reasons_present")
    if evidence.missing_maturity_date_count != 0:
        blockers.append("core_maturity_dates_incomplete")
    if evidence.unsupported_maturity_feature_count != 0:
        blockers.append("core_maturity_product_features_unsupported")
    if not evidence.request_fingerprint or not _REQUEST_FINGERPRINT_PATTERN.fullmatch(
        evidence.request_fingerprint
    ):
        blockers.append("core_maturity_request_fingerprint_invalid")
    if not evidence.snapshot_id:
        blockers.append("core_maturity_snapshot_identity_missing")
    if not evidence.restatement_version:
        blockers.append("core_maturity_restatement_version_missing")
    if not evidence.policy_version:
        blockers.append("core_maturity_policy_version_missing")
    if not _source_hashes_reconcile(evidence):
        blockers.append("core_maturity_source_digest_mismatch")
    if (evidence.reconciliation_status or "").upper() != _COMPLETE:
        blockers.append("core_maturity_reconciliation_incomplete")
    if maturity_ref is None or maturity_ref.data_quality_status.upper() != _COMPLETE:
        blockers.append("core_maturity_data_quality_incomplete")
    if not evidence.source_evidence_current:
        blockers.append("core_maturity_source_current_posture_missing")
    if (
        evidence.latest_evidence_at_utc is None
        or evidence.latest_evidence_at_utc > command.evaluated_at_utc
        or (
            maturity_ref is not None
            and evidence.latest_evidence_at_utc > maturity_ref.generated_at_utc
        )
    ):
        blockers.append("core_maturity_latest_evidence_time_invalid")
    if (
        command.correlation_id is None
        or evidence.source_correlation_id is None
        or command.correlation_id != evidence.source_correlation_id
    ):
        blockers.append("core_maturity_correlation_binding_missing")
    return tuple(dict.fromkeys(blockers))


def _counts_are_valid(evidence: CoreBondMaturityEvidence) -> bool:
    counts = (
        evidence.source_reported_maturing_position_count,
        evidence.maturity_bearing_holding_count,
        evidence.missing_maturity_date_count,
        evidence.unsupported_maturity_feature_count,
    )
    return all(isinstance(value, int) and value >= 0 for value in counts) and (
        evidence.missing_maturity_date_count or 0
    ) <= (evidence.maturity_bearing_holding_count or 0)


def _maturity_fact_is_consistent(evidence: CoreBondMaturityEvidence) -> bool:
    count = evidence.source_reported_maturing_position_count
    next_date = evidence.source_reported_next_maturity_date
    if count == 0:
        return next_date is None and evidence.maturity_diagnostic == "core_maturity_window_empty"
    if not isinstance(count, int) or count < 1 or next_date is None:
        return False
    return (
        evidence.window_start_date is not None
        and evidence.window_end_date is not None
        and evidence.window_start_date <= next_date <= evidence.window_end_date
        and evidence.maturity_diagnostic == "core_maturity_evidence_ready"
    )


def _request_receipt(command: EvaluateBondMaturityReadiness) -> dict[str, Any]:
    material = {
        "tenantIdHash": identity_hash(command.tenant_id),
        "portfolioIdHash": identity_hash(command.portfolio_id),
        "asOfDate": command.as_of_date.isoformat(),
        "evaluatedAtUtc": format_utc(command.evaluated_at_utc),
        "consumerSystem": _CONSUMER_SYSTEM,
        "maturityWindowDays": command.maturity_window_days,
        "includeProjected": False,
        "correlationIdHash": (
            identity_hash(command.correlation_id) if command.correlation_id is not None else None
        ),
    }
    return {**material, "requestDigest": sha256_json(material)}


def _source_receipt(evidence: CoreBondMaturityEvidence) -> dict[str, Any] | None:
    base = source_ref_receipt(evidence.maturity_fact_ref)
    if base is None:
        return None
    material = {key: value for key, value in base.items() if key != "receiptDigest"}
    material.update(
        {
            "responseProductName": evidence.response_product_name,
            "responseProductVersion": evidence.response_product_version,
            "responseTenantIdHash": (
                identity_hash(evidence.response_tenant_id)
                if evidence.response_tenant_id is not None
                else None
            ),
            "responsePortfolioIdHash": (
                identity_hash(evidence.response_portfolio_id)
                if evidence.response_portfolio_id is not None
                else None
            ),
            "sourceProductName": evidence.source_product_name,
            "sourceProductVersion": evidence.source_product_version,
            "windowStartDate": _date_text(evidence.window_start_date),
            "windowEndDate": _date_text(evidence.window_end_date),
            "horizonDays": evidence.horizon_days,
            "includeProjected": evidence.include_projected,
            "maturityBasis": evidence.maturity_basis,
            "nextMaturityDate": _date_text(evidence.source_reported_next_maturity_date),
            "maturingHoldingCount": evidence.source_reported_maturing_position_count,
            "maturityBearingHoldingCount": evidence.maturity_bearing_holding_count,
            "missingMaturityDateCount": evidence.missing_maturity_date_count,
            "unsupportedMaturityFeatureCount": evidence.unsupported_maturity_feature_count,
            "supportabilityStatus": evidence.supportability_status,
            "supportabilityReasons": list(evidence.supportability_reasons),
            "requestFingerprint": evidence.request_fingerprint,
            "snapshotId": evidence.snapshot_id,
            "sourceBatchFingerprint": evidence.source_batch_fingerprint,
            "responseContentHash": evidence.response_content_hash,
            "responseSourceDigest": evidence.response_source_digest,
            "upstreamProductId": _HOLDINGS_PRODUCT_ID,
            "upstreamProductName": evidence.upstream_product_name,
            "holdingsContentHash": (
                evidence.holdings_ref.content_hash if evidence.holdings_ref is not None else None
            ),
            "upstreamContentHash": evidence.upstream_content_hash,
            "restatementVersion": evidence.restatement_version,
            "reconciliationStatus": evidence.reconciliation_status,
            "latestEvidenceAtUtc": (
                format_utc(evidence.latest_evidence_at_utc)
                if evidence.latest_evidence_at_utc is not None
                else None
            ),
            "sourceEvidenceCurrent": evidence.source_evidence_current,
            "policyVersion": evidence.policy_version,
            "sourceCorrelationIdHash": (
                identity_hash(evidence.source_correlation_id)
                if evidence.source_correlation_id is not None
                else None
            ),
        }
    )
    return {**material, "receiptDigest": sha256_json(material)}


def _source_hashes_reconcile(evidence: CoreBondMaturityEvidence) -> bool:
    maturity_ref = evidence.maturity_fact_ref
    maturity_hashes = (
        maturity_ref.content_hash if maturity_ref is not None else None,
        evidence.source_batch_fingerprint,
        evidence.response_content_hash,
        evidence.response_source_digest,
    )
    holdings_ref = evidence.holdings_ref
    holdings_hashes = (
        holdings_ref.content_hash if holdings_ref is not None else None,
        evidence.upstream_content_hash,
    )
    return (
        all(_is_sha256(value) for value in maturity_hashes + holdings_hashes)
        and len(set(maturity_hashes)) == 1
        and len(set(holdings_hashes)) == 1
        and evidence.upstream_product_name == _HOLDINGS_PRODUCT_NAME
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None
