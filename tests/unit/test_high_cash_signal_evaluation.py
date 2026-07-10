from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from dataclasses import replace

import pytest

from app.domain import (
    EvidenceFreshness,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_high_cash_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> HighCashSignalPolicy:
    return HighCashSignalPolicy(
        policy_version="idle-liquidity-v1",
        cash_weight_threshold=Decimal("0.12"),
        candidate_score=Decimal("82"),
    )


def source_ref(
    product_id: str,
    source_system: SourceSystem = SourceSystem.LOTUS_CORE,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioStateSnapshot:v1": "/integration/portfolios/{portfolio_id}/core-snapshot",
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/cash-balances",
        "lotus-core:PortfolioCashMovementSummary:v1": "/portfolios/{portfolio_id}/cash-movement-summary",
        "lotus-core:PortfolioCashflowProjection:v1": "/portfolios/{portfolio_id}/cashflow-projection",
    }
    return SourceRef(
        product_id=product_id,
        source_system=source_system,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def high_cash_input(
    *,
    cash_weight: Decimal | None = Decimal("0.18"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_cashflow_projection: bool = True,
) -> HighCashSignalInput:
    return HighCashSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=cash_weight,
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness=freshness),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1", freshness=freshness),
        cash_movement_ref=source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1", freshness=freshness
        ),
        cashflow_projection_ref=(
            source_ref("lotus-core:PortfolioCashflowProjection:v1", freshness=freshness)
            if include_cashflow_projection
            else None
        ),
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_high_cash_positive_case_creates_reproducible_candidate() -> None:
    first = evaluate_high_cash_signal(high_cash_input(), policy())
    second = evaluate_high_cash_signal(high_cash_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.HIGH_CASH
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.candidate.evidence_packet.lineage_ref.source_refs
    assert first.reason_codes == (
        ReasonCode.HIGH_CASH_RATIO,
        ReasonCode.CASH_SOURCE_READY,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_high_cash_negative_case_does_not_create_candidate() -> None:
    result = evaluate_high_cash_signal(
        high_cash_input(cash_weight=Decimal("0.05")),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_high_cash_stale_source_blocks_positive_claim() -> None:
    result = evaluate_high_cash_signal(
        high_cash_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_high_cash_mismatched_source_date_blocks_candidate_creation() -> None:
    input_value = high_cash_input()
    mismatched_ref = replace(
        input_value.portfolio_state_ref,
        as_of_date=date(2026, 6, 20),
    )
    result = evaluate_high_cash_signal(
        replace(input_value, portfolio_state_ref=mismatched_ref),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_DATE_MISMATCH,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,)


def test_high_cash_future_source_generation_blocks_candidate_creation() -> None:
    input_value = high_cash_input()
    future_ref = replace(
        input_value.portfolio_state_ref,
        generated_at_utc=datetime(2026, 6, 21, 10, 0, 1, tzinfo=UTC),
    )
    result = evaluate_high_cash_signal(
        replace(input_value, portfolio_state_ref=future_ref),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_GENERATED_AFTER_EVALUATION,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,)


def test_high_cash_missing_source_blocks_positive_claim() -> None:
    result = evaluate_high_cash_signal(
        high_cash_input(include_cashflow_projection=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_high_cash_missing_cash_weight_blocks_positive_claim() -> None:
    result = evaluate_high_cash_signal(
        high_cash_input(cash_weight=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_high_cash_duplicate_source_is_suppressed() -> None:
    result = evaluate_high_cash_signal(
        high_cash_input(duplicate_of_candidate_id="idea_high_cash_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_high_cash_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_high_cash_signal(
        high_cash_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_high_cash_requires_timezone_aware_evaluation_time() -> None:
    invalid_input = HighCashSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1"),
        cash_movement_ref=source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
    )

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_high_cash_signal(invalid_input, policy())


def test_high_cash_rejects_invalid_source_reported_weight() -> None:
    with pytest.raises(ValueError, match="source_reported_cash_weight"):
        evaluate_high_cash_signal(
            high_cash_input(cash_weight=Decimal("1.01")),
            policy(),
        )


@pytest.mark.parametrize("threshold", [Decimal("-0.01"), Decimal("1.01")])
def test_high_cash_policy_rejects_invalid_threshold(threshold: Decimal) -> None:
    with pytest.raises(ValueError, match="cash_weight_threshold"):
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=threshold,
            candidate_score=Decimal("82"),
        )


def test_high_cash_policy_requires_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        HighCashSignalPolicy(
            policy_version=" ",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        )


@pytest.mark.parametrize("score", [Decimal("-1"), Decimal("101")])
def test_high_cash_policy_rejects_invalid_candidate_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score must be between 0 and 100"):
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=score,
        )
