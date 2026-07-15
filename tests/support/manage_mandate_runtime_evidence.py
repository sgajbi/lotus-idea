from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.application.runtime_evidence import identity_hash
from app.application.manage_mandate_runtime_evidence import (
    EvaluateManageMandateReadiness,
    build_manage_mandate_runtime_execution,
    evaluate_manage_mandate_readiness,
)
from app.domain import EvidenceFreshness, SourceRef, SourceSystem
from app.ports.manage_sources import (
    ManageActionRegisterRuntimeEvidence,
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
)

ACTION_HASH = "sha256:" + "a" * 64
PERFORMANCE_HASH = "sha256:" + "b" * 64
RISK_HASH = "sha256:" + "c" * 64


class AuthoritativeManageMandateSource:
    def __init__(self, *, workflow_count: int = 2, lineage_count: int = 4) -> None:
        self.workflow_count = workflow_count
        self.lineage_count = lineage_count
        self.requests: list[ManageMandateHealthEvidenceRequest] = []

    def close(self) -> None:
        return None

    def fetch_mandate_health_evidence(
        self,
        request: ManageMandateHealthEvidenceRequest,
    ) -> ManageMandateHealthEvidence:
        self.requests.append(request)
        generated_at = request.evaluated_at_utc - timedelta(minutes=1)
        return ManageMandateHealthEvidence(
            workflow_decision_count=self.workflow_count,
            lineage_edge_count=self.lineage_count,
            supportability_state="ready",
            supportability_reason="supportability_summary_ready",
            freshness_bucket="current",
            portfolio_scope_confirmed=True,
            action_register_ref=_source_ref(
                request=request,
                product_id="lotus-manage:PortfolioActionRegister:v1",
                source_system=SourceSystem.LOTUS_MANAGE,
                route="/api/v1/rebalance/supportability/summary",
                content_hash=ACTION_HASH,
                generated_at=generated_at,
            ),
            action_register_runtime=ManageActionRegisterRuntimeEvidence(
                product_id="lotus-manage:PortfolioActionRegister:v1",
                product_version="v1",
                tenant_id_hash=identity_hash(request.tenant_id),
                portfolio_id=request.portfolio_id,
                as_of_date=request.as_of_date,
                generated_at_utc=generated_at,
                source_batch_fingerprint=ACTION_HASH,
                run_count=1,
                operation_count=1,
                correlation_id=request.correlation_id,
            ),
            mandate_performance_health_ref=_source_ref(
                request=request,
                product_id="lotus-performance:MandatePerformanceHealthContext:v1",
                source_system=SourceSystem.LOTUS_PERFORMANCE,
                route="/performance/mandate-health-context",
                content_hash=PERFORMANCE_HASH,
                generated_at=generated_at,
            ),
            mandate_risk_health_ref=_source_ref(
                request=request,
                product_id="lotus-risk:MandateRiskHealthContext:v1",
                source_system=SourceSystem.LOTUS_RISK,
                route="/analytics/risk/mandate-health-context",
                content_hash=RISK_HASH,
                generated_at=generated_at,
            ),
            manage_diagnostic="manage_action_register_ready_portfolio_scope",
        )


def valid_manage_mandate_runtime_evidence(
    *,
    evaluated_at_utc: datetime,
    as_of_date: date | None = None,
    workflow_count: int = 2,
    lineage_count: int = 4,
) -> dict[str, Any]:
    command = EvaluateManageMandateReadiness(
        tenant_id="tenant-a",
        portfolio_id="portfolio-a",
        as_of_date=as_of_date or evaluated_at_utc.date(),
        evaluated_at_utc=evaluated_at_utc,
        correlation_id="corr-manage",
        trace_id="trace-manage",
    )
    result = evaluate_manage_mandate_readiness(
        command,
        manage_source=AuthoritativeManageMandateSource(
            workflow_count=workflow_count,
            lineage_count=lineage_count,
        ),
    )
    return build_manage_mandate_runtime_execution(
        generated_at_utc=evaluated_at_utc,
        result=result,
    )


def _source_ref(
    *,
    request: ManageMandateHealthEvidenceRequest,
    product_id: str,
    source_system: SourceSystem,
    route: str,
    content_hash: str,
    generated_at: datetime,
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=source_system,
        product_version="v1",
        route=route,
        as_of_date=request.as_of_date,
        generated_at_utc=generated_at,
        content_hash=content_hash,
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
