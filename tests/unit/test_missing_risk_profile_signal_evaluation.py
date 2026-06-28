from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    MissingRiskProfileSignalInput,
    MissingRiskProfileSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_missing_risk_profile_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> MissingRiskProfileSignalPolicy:
    return MissingRiskProfileSignalPolicy(
        policy_version="missing-risk-profile-review-v1",
        candidate_score=Decimal("64"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/workflow",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:advise-risk-profile-gap",
        data_quality_status="quality_passed",
        freshness=freshness,
    )


def risk_profile_input(
    *,
    risk_profile_status: str | None = "MISSING",
    risk_profile_effective_for_as_of_date: bool | None = False,
    risk_profile_review_due: bool | None = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> MissingRiskProfileSignalInput:
    return MissingRiskProfileSignalInput(
        as_of_date=AS_OF_DATE,
        risk_profile_ref=source_ref(freshness) if include_source_ref else None,
        risk_profile_status=risk_profile_status,
        risk_profile_effective_for_as_of_date=risk_profile_effective_for_as_of_date,
        risk_profile_review_due=risk_profile_review_due,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_missing_risk_profile_gap_creates_reproducible_review_candidate() -> None:
    first = evaluate_missing_risk_profile_signal(risk_profile_input(), policy())
    second = evaluate_missing_risk_profile_signal(risk_profile_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.MISSING_RISK_PROFILE
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (ReasonCode.MISSING_RISK_PROFILE, ReasonCode.REVIEW_REQUIRED)


def test_current_risk_profile_is_not_eligible() -> None:
    result = evaluate_missing_risk_profile_signal(
        risk_profile_input(
            risk_profile_status="CURRENT",
            risk_profile_effective_for_as_of_date=True,
            risk_profile_review_due=False,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


@pytest.mark.parametrize(
    ("risk_profile_status", "effective", "review_due"),
    [
        ("STALE", True, True),
        ("EXPIRED", True, True),
        ("PENDING_REVIEW", True, False),
        ("CURRENT", False, False),
        ("CURRENT", True, True),
    ],
)
def test_missing_risk_profile_reviewable_postures_create_candidate(
    risk_profile_status: str,
    effective: bool,
    review_due: bool,
) -> None:
    result = evaluate_missing_risk_profile_signal(
        risk_profile_input(
            risk_profile_status=risk_profile_status,
            risk_profile_effective_for_as_of_date=effective,
            risk_profile_review_due=review_due,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (ReasonCode.MISSING_RISK_PROFILE, ReasonCode.REVIEW_REQUIRED)


def test_missing_risk_profile_blocks_missing_or_stale_source_ref() -> None:
    missing = evaluate_missing_risk_profile_signal(
        risk_profile_input(include_source_ref=False),
        policy(),
    )
    stale = evaluate_missing_risk_profile_signal(
        risk_profile_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert missing.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert stale.outcome is SignalEvaluationOutcome.BLOCKED
    assert stale.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert stale.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_missing_risk_profile_blocks_missing_posture_fields() -> None:
    result = evaluate_missing_risk_profile_signal(
        risk_profile_input(risk_profile_status=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_missing_risk_profile_duplicate_and_entitlement_are_guarded() -> None:
    duplicate = evaluate_missing_risk_profile_signal(
        risk_profile_input(duplicate_of_candidate_id="idea_missing_risk_profile_existing"),
        policy(),
    )
    denied = evaluate_missing_risk_profile_signal(
        risk_profile_input(entitlement_allowed=False),
        policy(),
    )

    assert duplicate.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert duplicate.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)
    assert denied.outcome is SignalEvaluationOutcome.BLOCKED
    assert denied.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_missing_risk_profile_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_missing_risk_profile_signal(
            MissingRiskProfileSignalInput(
                as_of_date=AS_OF_DATE,
                risk_profile_ref=source_ref(),
                risk_profile_status="MISSING",
                risk_profile_effective_for_as_of_date=False,
                risk_profile_review_due=True,
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            policy(),
        )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_missing_risk_profile_policy_rejects_out_of_range_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score must be between 0 and 100"):
        MissingRiskProfileSignalPolicy(
            policy_version="missing-risk-profile-review-v1",
            candidate_score=score,
        )


def test_missing_risk_profile_policy_rejects_blank_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        MissingRiskProfileSignalPolicy(policy_version=" ", candidate_score=Decimal("64"))
