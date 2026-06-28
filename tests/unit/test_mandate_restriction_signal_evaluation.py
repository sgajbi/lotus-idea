from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    MandateRestrictionSignalInput,
    MandateRestrictionSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_mandate_restriction_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> MandateRestrictionSignalPolicy:
    return MandateRestrictionSignalPolicy(
        policy_version="mandate-restriction-review-v1",
        candidate_score=Decimal("66"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/restriction-posture",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:mandate-restriction-review",
        data_quality_status="quality_passed",
        freshness=freshness,
    )


def restriction_input(
    *,
    restriction_status: str | None = "REVIEW_REQUIRED",
    changed_since_last_review: bool | None = True,
    actionability_blocked: bool | None = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> MandateRestrictionSignalInput:
    return MandateRestrictionSignalInput(
        as_of_date=AS_OF_DATE,
        restriction_ref=source_ref(freshness) if include_source_ref else None,
        restriction_status=restriction_status,
        changed_since_last_review=changed_since_last_review,
        actionability_blocked=actionability_blocked,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_mandate_restriction_posture_creates_reproducible_review_candidate() -> None:
    first = evaluate_mandate_restriction_signal(restriction_input(), policy())
    second = evaluate_mandate_restriction_signal(restriction_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.MANDATE_RESTRICTION
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.COMPLIANCE_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.MANDATE_RESTRICTION_REVIEW,
        ReasonCode.REVIEW_REQUIRED,
    )


@pytest.mark.parametrize(
    ("restriction_status", "changed", "blocked"),
    [
        ("BLOCKED", False, False),
        ("BREACHED", False, False),
        ("RESTRICTION_CHANGED", False, False),
        ("CLEAR", True, False),
        ("WITHIN_MANDATE", False, True),
    ],
)
def test_actionable_restriction_postures_create_candidate(
    restriction_status: str,
    changed: bool,
    blocked: bool,
) -> None:
    result = evaluate_mandate_restriction_signal(
        restriction_input(
            restriction_status=restriction_status,
            changed_since_last_review=changed,
            actionability_blocked=blocked,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.reason_codes == (
        ReasonCode.MANDATE_RESTRICTION_REVIEW,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_clear_restriction_posture_is_not_eligible() -> None:
    result = evaluate_mandate_restriction_signal(
        restriction_input(
            restriction_status="CLEAR",
            changed_since_last_review=False,
            actionability_blocked=False,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_mandate_restriction_blocks_missing_or_stale_source_ref() -> None:
    missing = evaluate_mandate_restriction_signal(
        restriction_input(include_source_ref=False),
        policy(),
    )
    stale = evaluate_mandate_restriction_signal(
        restriction_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert missing.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert stale.outcome is SignalEvaluationOutcome.BLOCKED
    assert stale.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert stale.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_mandate_restriction_blocks_missing_posture_fields() -> None:
    result = evaluate_mandate_restriction_signal(
        restriction_input(restriction_status=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_mandate_restriction_duplicate_and_entitlement_are_guarded() -> None:
    duplicate = evaluate_mandate_restriction_signal(
        restriction_input(duplicate_of_candidate_id="idea_mandate_restriction_existing"),
        policy(),
    )
    denied = evaluate_mandate_restriction_signal(
        restriction_input(entitlement_allowed=False),
        policy(),
    )

    assert duplicate.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert duplicate.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)
    assert denied.outcome is SignalEvaluationOutcome.BLOCKED
    assert denied.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_mandate_restriction_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_mandate_restriction_signal(
            MandateRestrictionSignalInput(
                as_of_date=AS_OF_DATE,
                restriction_ref=source_ref(),
                restriction_status="REVIEW_REQUIRED",
                changed_since_last_review=True,
                actionability_blocked=True,
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            policy(),
        )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_mandate_restriction_policy_rejects_out_of_range_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score must be between 0 and 100"):
        MandateRestrictionSignalPolicy(
            policy_version="mandate-restriction-review-v1",
            candidate_score=score,
        )


def test_mandate_restriction_policy_rejects_blank_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        MandateRestrictionSignalPolicy(policy_version=" ", candidate_score=Decimal("66"))
