from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    HighVolatilitySignalInput,
    HighVolatilitySignalPolicy,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_high_volatility_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> HighVolatilitySignalPolicy:
    return HighVolatilitySignalPolicy(
        policy_version="high-volatility-attention-v1",
        volatility_threshold=Decimal("12.00"),
        candidate_score=Decimal("72"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-risk:RiskMetricsReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        product_version="v1",
        route="/analytics/risk/calculate",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:risk-metrics-report",
        data_quality_status="ready",
        freshness=freshness,
    )


def volatility_input(
    *,
    source_reported_volatility: Decimal | None = Decimal("14.25"),
    risk_supportability_state: str | None = "ready",
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> HighVolatilitySignalInput:
    return HighVolatilitySignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_volatility=source_reported_volatility,
        risk_supportability_state=risk_supportability_state,
        risk_ref=source_ref(freshness) if include_source_ref else None,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_high_volatility_positive_case_creates_reproducible_candidate() -> None:
    first = evaluate_high_volatility_signal(volatility_input(), policy())
    second = evaluate_high_volatility_signal(volatility_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.HIGH_VOLATILITY
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.VOLATILITY_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_high_volatility_below_threshold_does_not_create_candidate() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(source_reported_volatility=Decimal("8.50")),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_high_volatility_missing_source_ref_blocks_positive_claim() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(include_source_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_high_volatility_stale_source_blocks_positive_claim() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_high_volatility_non_ready_source_blocks_positive_claim() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(risk_supportability_state="degraded"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,)


def test_high_volatility_missing_source_metric_blocks_positive_claim() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(source_reported_volatility=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_high_volatility_duplicate_source_is_suppressed() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(duplicate_of_candidate_id="idea_high_volatility_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_high_volatility_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_high_volatility_signal(
        volatility_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_high_volatility_rejects_negative_source_volatility() -> None:
    with pytest.raises(ValueError, match="source_reported_volatility"):
        evaluate_high_volatility_signal(
            volatility_input(source_reported_volatility=Decimal("-0.01")),
            policy(),
        )


def test_high_volatility_requires_timezone_aware_evaluation_time() -> None:
    invalid_input = HighVolatilitySignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_volatility=Decimal("14.25"),
        risk_supportability_state="ready",
        risk_ref=source_ref(),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
    )

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_high_volatility_signal(invalid_input, policy())


def test_high_volatility_policy_rejects_negative_threshold() -> None:
    with pytest.raises(ValueError, match="volatility_threshold"):
        HighVolatilitySignalPolicy(
            policy_version="high-volatility-attention-v1",
            volatility_threshold=Decimal("-0.01"),
            candidate_score=Decimal("72"),
        )


def test_high_volatility_policy_requires_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        HighVolatilitySignalPolicy(
            policy_version=" ",
            volatility_threshold=Decimal("12.00"),
            candidate_score=Decimal("72"),
        )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_high_volatility_policy_rejects_invalid_candidate_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score"):
        HighVolatilitySignalPolicy(
            policy_version="high-volatility-attention-v1",
            volatility_threshold=Decimal("12.00"),
            candidate_score=score,
        )
