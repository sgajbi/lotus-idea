from __future__ import annotations

from datetime import date, datetime, timedelta

from app.application.core_portfolio_state_runtime_evidence import (
    EvaluateCorePortfolioStateReadiness,
    build_core_portfolio_state_runtime_execution,
    evaluate_core_portfolio_state_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.core_sources import (
    CorePortfolioStateEvidence,
    CorePortfolioStateEvidenceRequest,
)


class AuthoritativeCorePortfolioStateSource:
    def fetch_portfolio_state_evidence(
        self, request: CorePortfolioStateEvidenceRequest
    ) -> CorePortfolioStateEvidence:
        content_hash = "sha256:" + "a" * 64
        generated_at = request.evaluated_at_utc - timedelta(minutes=1)
        return CorePortfolioStateEvidence(
            portfolio_state_ref=SourceRef(
                product_id="lotus-core:PortfolioStateSnapshot:v1",
                source_system=SourceSystem.LOTUS_CORE,
                product_version="v1",
                route="/integration/portfolios/{portfolio_id}/core-snapshot",
                as_of_date=request.as_of_date,
                generated_at_utc=generated_at,
                content_hash=content_hash,
                data_quality_status="COMPLETE",
                freshness=EvidenceFreshness.CURRENT,
            ),
            source_evidence_available=True,
            response_product_name="PortfolioStateSnapshot",
            response_product_version="v1",
            response_tenant_id=request.tenant_id,
            response_portfolio_id=request.portfolio_id,
            snapshot_mode="BASELINE",
            request_fingerprint="core-snapshot-request:test",
            snapshot_id="pss_test_snapshot",
            source_batch_fingerprint=content_hash,
            response_content_hash=content_hash,
            response_source_digest=content_hash,
            restatement_version="restatement-v1",
            reconciliation_status="COMPLETE",
            latest_evidence_at_utc=generated_at - timedelta(minutes=1),
            source_evidence_current=True,
            policy_version="tenant-policy-v1",
            source_correlation_id=request.correlation_id,
            applied_sections=("portfolio_state", "portfolio_totals"),
            dropped_sections=(),
            portfolio_state_diagnostic="core_portfolio_state_ready",
        )


def valid_core_portfolio_state_runtime_evidence(
    *, evaluated_at_utc: datetime, as_of_date: date | None = None
) -> dict[str, object]:
    command = EvaluateCorePortfolioStateReadiness(
        tenant_id="test-tenant",
        portfolio_id="test-portfolio",
        as_of_date=as_of_date or evaluated_at_utc.date(),
        evaluated_at_utc=evaluated_at_utc,
        correlation_id="corr-test",
        trace_id="trace-test",
    )
    result = evaluate_core_portfolio_state_readiness(
        command,
        core_source=AuthoritativeCorePortfolioStateSource(),
    )
    return build_core_portfolio_state_runtime_execution(
        generated_at_utc=evaluated_at_utc,
        result=result,
    )
