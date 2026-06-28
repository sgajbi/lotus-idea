from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    MissingBenchmarkSignalInput,
    MissingBenchmarkSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_missing_benchmark_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> MissingBenchmarkSignalPolicy:
    return MissingBenchmarkSignalPolicy(
        policy_version="missing-benchmark-review-v1",
        candidate_score=Decimal("68"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-core:BenchmarkAssignment:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/benchmark-assignment",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:benchmark-assignment-gap",
        data_quality_status="complete",
        freshness=freshness,
    )


def missing_benchmark_input(
    *,
    benchmark_identity_resolved: bool = False,
    assignment_effective_for_as_of_date: bool = False,
    assignment_status: str | None = "active",
    assignment_version_present: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> MissingBenchmarkSignalInput:
    return MissingBenchmarkSignalInput(
        as_of_date=AS_OF_DATE,
        benchmark_assignment_ref=source_ref(freshness) if include_source_ref else None,
        benchmark_identity_resolved=benchmark_identity_resolved,
        assignment_effective_for_as_of_date=assignment_effective_for_as_of_date,
        assignment_status=assignment_status,
        assignment_version_present=assignment_version_present,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_missing_benchmark_gap_creates_reproducible_review_candidate() -> None:
    first = evaluate_missing_benchmark_signal(missing_benchmark_input(), policy())
    second = evaluate_missing_benchmark_signal(missing_benchmark_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.MISSING_BENCHMARK
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (ReasonCode.MISSING_BENCHMARK, ReasonCode.REVIEW_REQUIRED)


def test_missing_benchmark_ready_assignment_is_not_eligible() -> None:
    result = evaluate_missing_benchmark_signal(
        missing_benchmark_input(
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status="active",
            assignment_version_present=True,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


@pytest.mark.parametrize(
    "assignment_status",
    ["inactive", "blocked", None],
)
def test_missing_benchmark_non_active_assignment_creates_review_candidate(
    assignment_status: str | None,
) -> None:
    result = evaluate_missing_benchmark_signal(
        missing_benchmark_input(
            benchmark_identity_resolved=True,
            assignment_effective_for_as_of_date=True,
            assignment_status=assignment_status,
            assignment_version_present=True,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (ReasonCode.MISSING_BENCHMARK, ReasonCode.REVIEW_REQUIRED)


def test_missing_benchmark_blocks_missing_source_ref() -> None:
    result = evaluate_missing_benchmark_signal(
        missing_benchmark_input(include_source_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_missing_benchmark_blocks_stale_source() -> None:
    result = evaluate_missing_benchmark_signal(
        missing_benchmark_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_missing_benchmark_entitlement_denial_blocks_candidate_creation() -> None:
    result = evaluate_missing_benchmark_signal(
        missing_benchmark_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_missing_benchmark_duplicate_source_is_suppressed() -> None:
    result = evaluate_missing_benchmark_signal(
        missing_benchmark_input(duplicate_of_candidate_id="idea_missing_benchmark_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_missing_benchmark_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_missing_benchmark_signal(
            MissingBenchmarkSignalInput(
                as_of_date=AS_OF_DATE,
                benchmark_assignment_ref=source_ref(),
                benchmark_identity_resolved=False,
                assignment_effective_for_as_of_date=False,
                assignment_status="active",
                assignment_version_present=True,
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            policy(),
        )


def test_missing_benchmark_policy_rejects_blank_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        MissingBenchmarkSignalPolicy(
            policy_version=" ",
            candidate_score=Decimal("68"),
        )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_missing_benchmark_policy_rejects_out_of_range_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score must be between 0 and 100"):
        MissingBenchmarkSignalPolicy(
            policy_version="missing-benchmark-review-v1",
            candidate_score=score,
        )
