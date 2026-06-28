from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.mandate_restriction_signal import (
    EvaluateMandateRestrictionSignalCommand,
    evaluate_mandate_restriction_signal_command,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_mandate_restriction_command_maps_source_input() -> None:
    result = evaluate_mandate_restriction_signal_command(
        EvaluateMandateRestrictionSignalCommand(
            as_of_date=AS_OF_DATE,
            restriction_ref=_source_ref(),
            restriction_status="REVIEW_REQUIRED",
            changed_since_last_review=True,
            actionability_blocked=True,
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_mandate_restriction_")
    assert result.reason_codes == (
        ReasonCode.MANDATE_RESTRICTION_REVIEW,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_mandate_restriction_command_preserves_entitlement_blocker() -> None:
    result = evaluate_mandate_restriction_signal_command(
        EvaluateMandateRestrictionSignalCommand(
            as_of_date=AS_OF_DATE,
            restriction_ref=_source_ref(),
            restriction_status="REVIEW_REQUIRED",
            changed_since_last_review=True,
            actionability_blocked=True,
            evaluated_at_utc=EVALUATED_AT,
            entitlement_allowed=False,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/restriction-posture",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:mandate-restriction-review",
        data_quality_status="quality_passed",
        freshness=EvidenceFreshness.CURRENT,
    )
