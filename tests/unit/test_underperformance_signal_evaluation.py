from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnderperformanceSignalInput,
    UnderperformanceSignalPolicy,
    UnsupportedEvidenceReason,
    evaluate_underperformance_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> UnderperformanceSignalPolicy:
    return UnderperformanceSignalPolicy(
        policy_version="underperformance-review-v1",
        active_return_threshold=Decimal("-0.005"),
        candidate_score=Decimal("74"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-performance:ReturnsSeriesBundle:v1",
        source_system=SourceSystem.LOTUS_PERFORMANCE,
        product_version="v1",
        route="/integration/returns/series",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:returns-series-bundle",
        data_quality_status="ready",
        freshness=freshness,
    )


def underperformance_input(
    *,
    active_return: Decimal | None = Decimal("-0.0125"),
    benchmark_context_available: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> UnderperformanceSignalInput:
    return UnderperformanceSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_active_return=active_return,
        benchmark_context_available=benchmark_context_available,
        performance_ref=source_ref(freshness) if include_source_ref else None,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_underperformance_positive_case_creates_reproducible_candidate() -> None:
    first = evaluate_underperformance_signal(underperformance_input(), policy())
    second = evaluate_underperformance_signal(underperformance_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.UNDERPERFORMANCE
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.UNDERPERFORMANCE_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_underperformance_above_threshold_does_not_create_candidate() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(active_return=Decimal("-0.001")),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_underperformance_missing_benchmark_context_blocks_positive_claim() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(benchmark_context_available=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.MISSING_BENCHMARK,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_underperformance_stale_source_blocks_positive_claim() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_underperformance_missing_source_ref_blocks_positive_claim() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(include_source_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_underperformance_missing_active_return_blocks_positive_claim() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(active_return=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_underperformance_duplicate_source_is_suppressed() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(duplicate_of_candidate_id="idea_underperformance_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_underperformance_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_underperformance_signal(
        underperformance_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_underperformance_requires_timezone_aware_evaluation_time() -> None:
    invalid_input = UnderperformanceSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_active_return=Decimal("-0.0125"),
        benchmark_context_available=True,
        performance_ref=source_ref(),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
    )

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_underperformance_signal(invalid_input, policy())


def test_underperformance_policy_rejects_positive_threshold() -> None:
    with pytest.raises(ValueError, match="active_return_threshold"):
        UnderperformanceSignalPolicy(
            policy_version="underperformance-review-v1",
            active_return_threshold=Decimal("0.01"),
            candidate_score=Decimal("74"),
        )
