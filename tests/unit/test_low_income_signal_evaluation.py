from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    LowIncomeSignalInput,
    LowIncomeSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    ReviewAccessScope,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_low_income_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> LowIncomeSignalPolicy:
    return LowIncomeSignalPolicy(
        policy_version="cashflow-liquidity-review-v1",
        projected_cumulative_cashflow_threshold=Decimal("-10000"),
        candidate_score=Decimal("68"),
    )


def source_ref(
    product_id: str,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> SourceRef:
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
        data_quality_status="complete",
        freshness=freshness,
    )


def low_income_input(
    *,
    min_projected_cumulative_cashflow: Decimal | None = Decimal("-12500"),
    cash_movement_count: int | None = 3,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_cashflow_projection: bool = True,
    access_scope: ReviewAccessScope | None = None,
) -> LowIncomeSignalInput:
    return LowIncomeSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_min_projected_cumulative_cashflow=min_projected_cumulative_cashflow,
        cash_movement_count=cash_movement_count,
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
        access_scope=access_scope,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_low_income_positive_case_creates_review_candidate() -> None:
    first = evaluate_low_income_signal(low_income_input(), policy())
    second = evaluate_low_income_signal(low_income_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.LOW_INCOME
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (ReasonCode.INCOME_ATTENTION, ReasonCode.REVIEW_REQUIRED)


def test_low_income_source_correction_preserves_candidate_and_versions_evidence() -> None:
    source_input = low_income_input()
    assert source_input.cashflow_projection_ref is not None
    corrected_input = replace(
        source_input,
        cashflow_projection_ref=replace(
            source_input.cashflow_projection_ref,
            content_hash="sha256:lotus-core:PortfolioCashflowProjection:v1:correction-2",
        ),
    )

    original = evaluate_low_income_signal(source_input, policy())
    corrected = evaluate_low_income_signal(corrected_input, policy())

    assert original.signal is not None
    assert corrected.signal is not None
    assert original.candidate is not None
    assert corrected.candidate is not None
    assert original.candidate.candidate_id == corrected.candidate.candidate_id
    assert original.signal.signal_id != corrected.signal.signal_id
    assert (
        original.candidate.evidence_packet.evidence_packet_id
        != corrected.candidate.evidence_packet.evidence_packet_id
    )
    assert (
        original.candidate.evidence_packet.lineage_ref.lineage_id
        != corrected.candidate.evidence_packet.lineage_ref.lineage_id
    )
    assert (
        original.candidate.evidence_packet.lineage_ref.content_hash
        != corrected.candidate.evidence_packet.lineage_ref.content_hash
    )
    assert corrected.candidate.evidence_packet.source_refs[1].content_hash.endswith("correction-2")
    assert (
        corrected.candidate.evidence_packet.lineage_ref.source_refs
        == corrected.candidate.evidence_packet.source_refs
    )


def test_low_income_candidate_identity_is_bound_to_access_scope() -> None:
    private_book_scope = ReviewAccessScope(
        tenant_id="tenant-a",
        book_id="private-bank-sg",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-001",
    )
    discretionary_book_scope = ReviewAccessScope(
        tenant_id="tenant-a",
        book_id="discretionary-book",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-001",
    )

    private_book = evaluate_low_income_signal(
        low_income_input(access_scope=private_book_scope),
        policy(),
    )
    discretionary_book = evaluate_low_income_signal(
        low_income_input(access_scope=discretionary_book_scope),
        policy(),
    )

    assert private_book.candidate is not None
    assert discretionary_book.candidate is not None
    assert private_book.candidate.access_scope == private_book_scope
    assert discretionary_book.candidate.access_scope == discretionary_book_scope
    assert private_book.candidate.candidate_id != discretionary_book.candidate.candidate_id


def test_low_income_not_eligible_when_projected_cashflow_above_threshold() -> None:
    result = evaluate_low_income_signal(
        low_income_input(min_projected_cumulative_cashflow=Decimal("-5000")),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_low_income_blocks_missing_projection_source() -> None:
    result = evaluate_low_income_signal(
        low_income_input(include_cashflow_projection=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_low_income_blocks_missing_source_reported_cashflow() -> None:
    result = evaluate_low_income_signal(
        low_income_input(min_projected_cumulative_cashflow=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_low_income_blocks_missing_cash_movement_count() -> None:
    result = evaluate_low_income_signal(
        low_income_input(cash_movement_count=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_low_income_blocks_stale_source() -> None:
    result = evaluate_low_income_signal(
        low_income_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_low_income_duplicate_source_is_suppressed() -> None:
    result = evaluate_low_income_signal(
        low_income_input(duplicate_of_candidate_id="idea_low_income_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_low_income_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_low_income_signal(
        low_income_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_low_income_rejects_negative_cash_movement_count() -> None:
    with pytest.raises(ValueError, match="cash_movement_count must be non-negative"):
        evaluate_low_income_signal(low_income_input(cash_movement_count=-1), policy())


def test_low_income_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_low_income_signal(
            LowIncomeSignalInput(
                as_of_date=AS_OF_DATE,
                source_reported_min_projected_cumulative_cashflow=Decimal("-12500"),
                cash_movement_count=3,
                cash_movement_ref=source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
                cashflow_projection_ref=source_ref("lotus-core:PortfolioCashflowProjection:v1"),
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            policy(),
        )


def test_low_income_policy_rejects_positive_shortfall_threshold() -> None:
    with pytest.raises(ValueError, match="projected_cumulative_cashflow_threshold"):
        LowIncomeSignalPolicy(
            policy_version="cashflow-liquidity-review-v1",
            projected_cumulative_cashflow_threshold=Decimal("1"),
            candidate_score=Decimal("68"),
        )


def test_low_income_policy_requires_policy_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        LowIncomeSignalPolicy(
            policy_version=" ",
            projected_cumulative_cashflow_threshold=Decimal("-10000"),
            candidate_score=Decimal("68"),
        )


def test_low_income_policy_rejects_out_of_range_score() -> None:
    with pytest.raises(ValueError, match="candidate_score must be between 0 and 100"):
        LowIncomeSignalPolicy(
            policy_version="cashflow-liquidity-review-v1",
            projected_cumulative_cashflow_threshold=Decimal("-10000"),
            candidate_score=Decimal("101"),
        )
