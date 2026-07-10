from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.bond_maturity_signal import (
    EvaluateBondMaturityFromCoreCommand,
    EvaluateBondMaturitySignalCommand,
    evaluate_bond_maturity_signal_command,
    evaluate_bond_maturity_signal_from_core,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubCoreBondMaturitySource(CoreBondMaturitySourcePort):
    def __init__(
        self,
        evidence: CoreBondMaturityEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[CoreBondMaturityEvidenceRequest] = []

    def fetch_bond_maturity_evidence(
        self, request: CoreBondMaturityEvidenceRequest
    ) -> CoreBondMaturityEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_evaluate_bond_maturity_signal_command_maps_source_input() -> None:
    result = evaluate_bond_maturity_signal_command(
        EvaluateBondMaturitySignalCommand(
            as_of_date=AS_OF_DATE,
            source_reported_next_maturity_date=date(2026, 7, 10),
            source_reported_maturing_position_count=2,
            holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
            maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_bond_maturity_")


def test_evaluate_bond_maturity_signal_from_core_uses_source_evidence() -> None:
    core_source = StubCoreBondMaturitySource(
        CoreBondMaturityEvidence(
            source_reported_next_maturity_date=date(2026, 7, 10),
            source_reported_maturing_position_count=2,
            holdings_ref=_source_ref("lotus-core:HoldingsAsOf:v1"),
            maturity_fact_ref=_source_ref("lotus-core:PortfolioMaturitySummary:v1"),
            maturity_diagnostic="core_maturity_evidence_ready",
        )
    )

    result = evaluate_bond_maturity_signal_from_core(_command(), core_source=core_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (ReasonCode.MATURITY_WINDOW, ReasonCode.REVIEW_REQUIRED)
    assert result.candidate is not None
    assert result.candidate.access_scope is not None
    assert result.candidate.access_scope.tenant_id == "tenant-a"
    assert core_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert core_source.requests[0].tenant_id == "tenant-a"
    assert core_source.requests[0].maturity_window_days == 30
    assert core_source.requests[0].correlation_id == "corr-core"


def test_evaluate_bond_maturity_signal_from_core_blocks_entitlement_denial() -> None:
    result = evaluate_bond_maturity_signal_from_core(
        _command(),
        core_source=StubCoreBondMaturitySource(exception=CoreSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def test_evaluate_bond_maturity_signal_from_core_blocks_source_unavailable() -> None:
    result = evaluate_bond_maturity_signal_from_core(
        _command(),
        core_source=StubCoreBondMaturitySource(
            exception=CoreSourceUnavailable(code="core_maturity_contract_missing")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def _command() -> EvaluateBondMaturityFromCoreCommand:
    return EvaluateBondMaturityFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        maturity_window_days=30,
        correlation_id="corr-core",
        trace_id="trace-core",
    )


def _source_ref(product_id: str, *, suffix: str = "") -> SourceRef:
    route_by_product = {
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/positions",
        "lotus-core:PortfolioMaturitySummary:v1": "/portfolios/{portfolio_id}/maturity-summary",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}{suffix}",
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
