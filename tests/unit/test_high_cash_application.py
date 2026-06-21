from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from dataclasses import dataclass

from app.application.high_cash_signal import (
    EvaluateHighCashFromCoreCommand,
    EvaluateHighCashSignalCommand,
    evaluate_high_cash_signal_from_core,
    evaluate_high_cash_signal_command,
)
from app.domain import (
    EvidenceFreshness,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
)
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def source_ref(
    product_id: str, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def command(
    *,
    cash_weight: Decimal | None = Decimal("0.18"),
    entitlement_allowed: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> EvaluateHighCashSignalCommand:
    return EvaluateHighCashSignalCommand(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1", freshness),
        cash_movement_ref=source_ref("lotus-core:PortfolioCashMovementSummary:v1", freshness),
        cashflow_projection_ref=source_ref("lotus-core:PortfolioCashflowProjection:v1", freshness),
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
    )


def test_application_evaluates_high_cash_command_with_default_policy() -> None:
    result = evaluate_high_cash_signal_command(command())

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.score is not None
    assert result.candidate.score.policy_version == "idle-liquidity-v1"


def test_application_preserves_entitlement_denied_as_blocked_domain_posture() -> None:
    result = evaluate_high_cash_signal_command(command(entitlement_allowed=False))

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_application_preserves_stale_source_as_blocked_domain_posture() -> None:
    result = evaluate_high_cash_signal_command(command(freshness=EvidenceFreshness.STALE))

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence | None = None
    error: Exception | None = None
    seen_request: CoreHighCashEvidenceRequest | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        if self.evidence is None:
            raise AssertionError("evidence must be configured")
        return self.evidence


def from_core_command() -> EvaluateHighCashFromCoreCommand:
    return EvaluateHighCashFromCoreCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-idea",
        trace_id="trace-idea",
    )


def current_core_evidence(*, cash_weight: Decimal | None = Decimal("0.18")) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1"),
        cash_movement_ref=source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )


def test_application_fetches_core_source_evidence_before_high_cash_evaluation() -> None:
    source = RecordingCoreSource(evidence=current_core_evidence())

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert source.seen_request is not None
    assert source.seen_request.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert source.seen_request.correlation_id == "corr-idea"
    assert source.seen_request.trace_id == "trace-idea"


def test_application_blocks_source_backed_flow_when_core_denies_entitlement() -> None:
    source = RecordingCoreSource(error=CoreSourceEntitlementDenied())

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)
    assert result.candidate is None


def test_application_blocks_source_backed_flow_when_core_is_unavailable() -> None:
    source = RecordingCoreSource(error=CoreSourceUnavailable(code="upstream_timeout"))

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,)
    assert result.candidate is None


def test_application_does_not_infer_cash_weight_when_core_omits_source_reported_value() -> None:
    source = RecordingCoreSource(evidence=current_core_evidence(cash_weight=None))

    result = evaluate_high_cash_signal_from_core(from_core_command(), core_source=source)

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert result.candidate is None
