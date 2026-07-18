from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY,
    DrawdownReviewSignalInput,
    DrawdownReviewSignalPolicy,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_drawdown_review_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> DrawdownReviewSignalPolicy:
    return DrawdownReviewSignalPolicy(
        policy_version="drawdown-review-attention-v1",
        max_drawdown_threshold=Decimal("-0.08"),
        candidate_score=Decimal("72"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-risk:DrawdownAnalyticsReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        product_version="v1",
        route="/analytics/risk/drawdown",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:drawdown-analytics-report",
        data_quality_status="ready",
        freshness=freshness,
    )


def drawdown_input(
    *,
    source_reported_max_drawdown: Decimal | None = Decimal("-0.1245"),
    risk_supportability_state: str | None = "ready",
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> DrawdownReviewSignalInput:
    return DrawdownReviewSignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_max_drawdown=source_reported_max_drawdown,
        risk_supportability_state=risk_supportability_state,
        risk_ref=source_ref(freshness) if include_source_ref else None,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_drawdown_review_positive_case_creates_source_safe_candidate() -> None:
    first = evaluate_drawdown_review_signal(drawdown_input(), policy())
    second = evaluate_drawdown_review_signal(drawdown_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert first.signal.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert first.signal.reason_codes == (DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.reason_code,)
    assert first.signal.source_refs[0].product_id == DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_product_id
    assert first.signal.source_refs[0].route == DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_route
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.candidate_id.startswith("idea_drawdown_review_")
    assert first.candidate.family is OpportunityFamily.HIGH_VOLATILITY
    assert first.candidate.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.DRAWDOWN_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_drawdown_review_below_materiality_does_not_create_candidate() -> None:
    result = evaluate_drawdown_review_signal(
        drawdown_input(source_reported_max_drawdown=Decimal("-0.025")),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_drawdown_review_missing_or_stale_source_blocks_positive_claim() -> None:
    missing = evaluate_drawdown_review_signal(drawdown_input(include_source_ref=False), policy())
    stale = evaluate_drawdown_review_signal(
        drawdown_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert missing.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert missing.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert stale.outcome is SignalEvaluationOutcome.BLOCKED
    assert stale.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert stale.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert stale.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_drawdown_review_non_ready_source_blocks_positive_claim() -> None:
    result = evaluate_drawdown_review_signal(
        drawdown_input(risk_supportability_state="degraded"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,)


def test_drawdown_review_duplicate_source_is_suppressed() -> None:
    result = evaluate_drawdown_review_signal(
        drawdown_input(duplicate_of_candidate_id="idea_drawdown_review_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_drawdown_review_missing_metric_or_entitlement_blocks_positive_claim() -> None:
    missing_metric = evaluate_drawdown_review_signal(
        drawdown_input(source_reported_max_drawdown=None),
        policy(),
    )
    denied = evaluate_drawdown_review_signal(
        drawdown_input(entitlement_allowed=False),
        policy(),
    )

    assert missing_metric.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing_metric.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert missing_metric.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert denied.outcome is SignalEvaluationOutcome.BLOCKED
    assert denied.family is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    assert denied.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_drawdown_review_rejects_positive_source_drawdown() -> None:
    with pytest.raises(ValueError, match="source_reported_max_drawdown"):
        evaluate_drawdown_review_signal(
            drawdown_input(source_reported_max_drawdown=Decimal("0.01")),
            policy(),
        )


def test_drawdown_review_policy_validates_threshold_and_score() -> None:
    with pytest.raises(ValueError, match="max_drawdown_threshold"):
        DrawdownReviewSignalPolicy(
            policy_version="drawdown-review-attention-v1",
            max_drawdown_threshold=Decimal("0.01"),
            candidate_score=Decimal("72"),
        )
    with pytest.raises(ValueError, match="policy_version is required"):
        DrawdownReviewSignalPolicy(
            policy_version=" ",
            max_drawdown_threshold=Decimal("-0.08"),
            candidate_score=Decimal("72"),
        )
    with pytest.raises(ValueError, match="candidate_score"):
        DrawdownReviewSignalPolicy(
            policy_version="drawdown-review-attention-v1",
            max_drawdown_threshold=Decimal("-0.08"),
            candidate_score=Decimal("100.01"),
        )
