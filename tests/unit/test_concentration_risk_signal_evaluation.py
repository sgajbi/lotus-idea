from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    ConcentrationRiskSignalInput,
    ConcentrationRiskSignalPolicy,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_concentration_risk_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> ConcentrationRiskSignalPolicy:
    return ConcentrationRiskSignalPolicy(
        policy_version="concentration-attention-v1",
        top_position_weight_threshold=Decimal("0.15"),
        top_issuer_weight_threshold=Decimal("0.20"),
        candidate_score=Decimal("78"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-risk:ConcentrationRiskReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        product_version="v1",
        route="/analytics/risk/concentration",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:concentration-risk-report",
        data_quality_status="ready",
        freshness=freshness,
    )


def concentration_input(
    *,
    top_position_weight: Decimal | None = Decimal("0.23"),
    top_issuer_weight: Decimal | None = Decimal("0.245"),
    issuer_coverage_status: str | None = "complete",
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> ConcentrationRiskSignalInput:
    return ConcentrationRiskSignalInput(
        as_of_date=AS_OF_DATE,
        top_position_weight_current=top_position_weight,
        top_issuer_weight_current=top_issuer_weight,
        issuer_coverage_status=issuer_coverage_status,
        concentration_ref=source_ref(freshness) if include_source_ref else None,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_concentration_positive_case_creates_reproducible_candidate() -> None:
    first = evaluate_concentration_risk_signal(concentration_input(), policy())
    second = evaluate_concentration_risk_signal(concentration_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.CONCENTRATION
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.CONCENTRATION_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_concentration_negative_case_does_not_create_candidate() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(
            top_position_weight=Decimal("0.08"),
            top_issuer_weight=Decimal("0.11"),
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_concentration_stale_source_blocks_positive_claim() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_concentration_partial_issuer_coverage_blocks_positive_claim() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(issuer_coverage_status="partial"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,)


def test_concentration_missing_source_ref_blocks_positive_claim() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(include_source_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_concentration_missing_issuer_coverage_blocks_positive_claim() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(issuer_coverage_status=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_concentration_missing_weights_block_positive_claim() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(top_position_weight=None, top_issuer_weight=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_concentration_duplicate_source_is_suppressed() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(duplicate_of_candidate_id="idea_concentration_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_concentration_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_concentration_risk_signal(
        concentration_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_concentration_requires_timezone_aware_evaluation_time() -> None:
    invalid_input = ConcentrationRiskSignalInput(
        as_of_date=AS_OF_DATE,
        top_position_weight_current=Decimal("0.23"),
        top_issuer_weight_current=Decimal("0.245"),
        issuer_coverage_status="complete",
        concentration_ref=source_ref(),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
    )

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_concentration_risk_signal(invalid_input, policy())


@pytest.mark.parametrize(
    ("field_name", "top_position_weight", "top_issuer_weight"),
    [
        ("top_position_weight_current", Decimal("1.01"), Decimal("0.20")),
        ("top_issuer_weight_current", Decimal("0.15"), Decimal("-0.01")),
    ],
)
def test_concentration_rejects_invalid_source_reported_weight(
    field_name: str,
    top_position_weight: Decimal,
    top_issuer_weight: Decimal,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        evaluate_concentration_risk_signal(
            concentration_input(
                top_position_weight=top_position_weight,
                top_issuer_weight=top_issuer_weight,
            ),
            policy(),
        )


@pytest.mark.parametrize("threshold", [Decimal("-0.01"), Decimal("1.01")])
def test_concentration_policy_rejects_invalid_position_threshold(threshold: Decimal) -> None:
    with pytest.raises(ValueError, match="top_position_weight_threshold"):
        ConcentrationRiskSignalPolicy(
            policy_version="concentration-attention-v1",
            top_position_weight_threshold=threshold,
            top_issuer_weight_threshold=Decimal("0.20"),
            candidate_score=Decimal("78"),
        )


def test_concentration_policy_requires_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        ConcentrationRiskSignalPolicy(
            policy_version=" ",
            top_position_weight_threshold=Decimal("0.15"),
            top_issuer_weight_threshold=Decimal("0.20"),
            candidate_score=Decimal("78"),
        )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_concentration_policy_rejects_invalid_candidate_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score"):
        ConcentrationRiskSignalPolicy(
            policy_version="concentration-attention-v1",
            top_position_weight_threshold=Decimal("0.15"),
            top_issuer_weight_threshold=Decimal("0.20"),
            candidate_score=score,
        )
