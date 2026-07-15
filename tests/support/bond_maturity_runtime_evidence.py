from __future__ import annotations

from datetime import date, datetime, timedelta

from app.application.bond_maturity_runtime_evidence import (
    EvaluateBondMaturityReadiness,
    build_bond_maturity_runtime_execution,
    evaluate_bond_maturity_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import CoreBondMaturityEvidence, CoreBondMaturityEvidenceRequest

MATURITY_HASH = "sha256:" + "a" * 64
HOLDINGS_HASH = "sha256:" + "b" * 64


class AuthoritativeCoreBondMaturitySource:
    def __init__(self, *, opportunity_detected: bool = True) -> None:
        self.opportunity_detected = opportunity_detected

    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        return authoritative_bond_maturity_evidence(
            request=request,
            opportunity_detected=self.opportunity_detected,
        )

    def close(self) -> None:
        return None


def authoritative_bond_maturity_evidence(
    *,
    request: CoreBondMaturityEvidenceRequest,
    opportunity_detected: bool = True,
) -> CoreBondMaturityEvidence:
    generated_at = request.evaluated_at_utc - timedelta(minutes=1)
    window_end = request.as_of_date + timedelta(days=request.maturity_window_days)
    return CoreBondMaturityEvidence(
        source_reported_next_maturity_date=(
            request.as_of_date + timedelta(days=10) if opportunity_detected else None
        ),
        source_reported_maturing_position_count=1 if opportunity_detected else 0,
        holdings_ref=SourceRef(
            product_id="lotus-core:HoldingsAsOf:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/portfolios/{portfolio_id}/positions",
            as_of_date=request.as_of_date,
            generated_at_utc=generated_at,
            content_hash=HOLDINGS_HASH,
            data_quality_status="COMPLETE",
            freshness=EvidenceFreshness.CURRENT,
        ),
        maturity_fact_ref=SourceRef(
            product_id="lotus-core:PortfolioMaturitySummary:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/portfolios/{portfolio_id}/maturity-summary",
            as_of_date=request.as_of_date,
            generated_at_utc=generated_at,
            content_hash=MATURITY_HASH,
            data_quality_status="COMPLETE",
            freshness=EvidenceFreshness.CURRENT,
        ),
        response_product_name="PortfolioMaturitySummary",
        response_product_version="v1",
        response_tenant_id=request.tenant_id,
        response_portfolio_id=request.portfolio_id,
        source_product_name="HoldingsAsOf",
        source_product_version="v1",
        window_start_date=request.as_of_date,
        window_end_date=window_end,
        horizon_days=request.maturity_window_days,
        include_projected=False,
        maturity_basis="CONTRACTUAL_INSTRUMENT_MATURITY_DATE",
        maturity_bearing_holding_count=2,
        missing_maturity_date_count=0,
        unsupported_maturity_feature_count=0,
        supportability_status="SUPPORTED",
        supportability_reasons=(),
        request_fingerprint="maturity_summary:0123456789abcdef",
        snapshot_id="holdings-snapshot-1",
        source_batch_fingerprint=MATURITY_HASH,
        response_content_hash=MATURITY_HASH,
        response_source_digest=MATURITY_HASH,
        upstream_product_name="HoldingsAsOf",
        upstream_content_hash=HOLDINGS_HASH,
        restatement_version="restatement-v1",
        reconciliation_status="COMPLETE",
        latest_evidence_at_utc=generated_at - timedelta(minutes=1),
        source_evidence_current=True,
        policy_version="holdings-policy-v1",
        source_correlation_id=request.correlation_id,
        maturity_diagnostic=(
            "core_maturity_evidence_ready" if opportunity_detected else "core_maturity_window_empty"
        ),
    )


def valid_bond_maturity_runtime_evidence(
    *,
    evaluated_at_utc: datetime,
    as_of_date: date | None = None,
    opportunity_detected: bool = True,
) -> dict[str, object]:
    command = EvaluateBondMaturityReadiness(
        tenant_id="test-tenant",
        portfolio_id="test-portfolio",
        as_of_date=as_of_date or evaluated_at_utc.date(),
        evaluated_at_utc=evaluated_at_utc,
        maturity_window_days=30,
        correlation_id="corr-test",
        trace_id="trace-test",
    )
    result = evaluate_bond_maturity_readiness(
        command,
        core_source=AuthoritativeCoreBondMaturitySource(opportunity_detected=opportunity_detected),
    )
    return build_bond_maturity_runtime_execution(
        generated_at_utc=evaluated_at_utc,
        result=result,
    )
