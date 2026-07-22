from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    BondMaturitySignalInput,
    BondMaturitySignalPolicy,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_bond_maturity_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> BondMaturitySignalPolicy:
    return BondMaturitySignalPolicy(
        policy_version="bond-maturity-review-v1",
        maturity_window_days=30,
        candidate_score=Decimal("70"),
    )


def source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    content_hash_suffix: str = "",
) -> SourceRef:
    route_by_product = {
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/positions",
        "lotus-core:PortfolioMaturitySummary:v1": ("/portfolios/{portfolio_id}/maturity-summary"),
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}{content_hash_suffix}",
        data_quality_status="complete",
        freshness=freshness,
    )


def maturity_input(
    *,
    next_maturity_date: date | None = date(2026, 7, 10),
    maturing_position_count: int | None = 2,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_maturity_fact_ref: bool = True,
) -> BondMaturitySignalInput:
    return BondMaturitySignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_next_maturity_date=next_maturity_date,
        source_reported_maturing_position_count=maturing_position_count,
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1", freshness=freshness),
        maturity_fact_ref=(
            source_ref(
                "lotus-core:PortfolioMaturitySummary:v1",
                freshness=freshness,
                content_hash_suffix=":maturity",
            )
            if include_maturity_fact_ref
            else None
        ),
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_bond_maturity_positive_case_creates_review_candidate() -> None:
    first = evaluate_bond_maturity_signal(maturity_input(), policy())
    second = evaluate_bond_maturity_signal(maturity_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.BOND_MATURITY
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (ReasonCode.MATURITY_WINDOW, ReasonCode.REVIEW_REQUIRED)


def test_bond_maturity_not_eligible_outside_maturity_window() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=date(2026, 8, 1)),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_bond_maturity_not_eligible_without_maturing_positions() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(maturing_position_count=0),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_bond_maturity_not_eligible_for_supported_empty_maturity_window() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=None, maturing_position_count=0),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_bond_maturity_blocks_missing_maturity_source_ref() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(include_maturity_fact_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_bond_maturity_blocks_missing_maturity_date() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=None, maturing_position_count=1),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_bond_maturity_blocks_stale_source() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_bond_maturity_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_bond_maturity_duplicate_source_is_suppressed() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(duplicate_of_candidate_id="idea_bond_maturity_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_bond_maturity_rejects_negative_maturing_position_count() -> None:
    with pytest.raises(
        ValueError,
        match="source_reported_maturing_position_count must be non-negative",
    ):
        evaluate_bond_maturity_signal(
            maturity_input(maturing_position_count=-1),
            policy(),
        )


def test_bond_maturity_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_bond_maturity_signal(
            BondMaturitySignalInput(
                as_of_date=AS_OF_DATE,
                source_reported_next_maturity_date=date(2026, 7, 10),
                source_reported_maturing_position_count=2,
                holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1"),
                maturity_fact_ref=source_ref(
                    "lotus-core:HoldingsAsOf:v1",
                    content_hash_suffix=":maturity",
                ),
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            policy(),
        )


def test_bond_maturity_policy_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="maturity_window_days must be between 1 and 366"):
        BondMaturitySignalPolicy(
            policy_version="bond-maturity-review-v1",
            maturity_window_days=0,
            candidate_score=Decimal("70"),
        )


def test_bond_maturity_policy_rejects_out_of_range_score() -> None:
    with pytest.raises(ValueError, match="candidate_score must be between 0 and 100"):
        BondMaturitySignalPolicy(
            policy_version="bond-maturity-review-v1",
            maturity_window_days=30,
            candidate_score=Decimal("101"),
        )
