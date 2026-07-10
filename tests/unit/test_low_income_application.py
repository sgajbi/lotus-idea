from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.low_income_signal import (
    EvaluateLowIncomeFromCoreCommand,
    EvaluateLowIncomeSignalCommand,
    evaluate_low_income_signal_command,
    evaluate_low_income_signal_from_core,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreLowIncomeSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubCoreLowIncomeSource(CoreLowIncomeSourcePort):
    def __init__(
        self,
        evidence: CoreLowIncomeEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[CoreLowIncomeEvidenceRequest] = []

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_evaluate_low_income_signal_command_maps_source_input() -> None:
    result = evaluate_low_income_signal_command(
        EvaluateLowIncomeSignalCommand(
            as_of_date=AS_OF_DATE,
            source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
            cash_movement_count=3,
            cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_low_income_")


def test_evaluate_low_income_signal_from_core_uses_source_evidence() -> None:
    core_source = StubCoreLowIncomeSource(
        CoreLowIncomeEvidence(
            source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
            cash_movement_count=3,
            cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            cashflow_projection_ref=_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
            cashflow_diagnostic="core_cashflow_liquidity_evidence_ready",
        )
    )

    result = evaluate_low_income_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (ReasonCode.INCOME_ATTENTION, ReasonCode.REVIEW_REQUIRED)
    assert core_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert core_source.requests[0].horizon_days == 30
    assert core_source.requests[0].correlation_id == "corr-core"


def test_evaluate_low_income_signal_from_core_blocks_entitlement_denial() -> None:
    result = evaluate_low_income_signal_from_core(
        _command(),
        core_source=StubCoreLowIncomeSource(exception=CoreSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_evaluate_low_income_signal_from_core_blocks_source_unavailable() -> None:
    result = evaluate_low_income_signal_from_core(
        _command(),
        core_source=StubCoreLowIncomeSource(
            exception=CoreSourceUnavailable(code="core_cashflow_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def _command() -> EvaluateLowIncomeFromCoreCommand:
    return EvaluateLowIncomeFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        horizon_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _source_ref(product_id: str) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioCashMovementSummary:v1": (
            "/portfolios/{portfolio_id}/cash-movement-summary"
        ),
        "lotus-core:PortfolioCashflowProjection:v1": (
            "/portfolios/{portfolio_id}/cashflow-projection"
        ),
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
