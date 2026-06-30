from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    MissingSuitabilityContextSignalInput,
    MissingSuitabilityContextSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_missing_suitability_context_signal,
    validate_missing_suitability_counts,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> MissingSuitabilityContextSignalPolicy:
    return MissingSuitabilityContextSignalPolicy(
        policy_version="missing-suitability-context-review-v1",
        minimum_open_requirement_count=1,
        candidate_score=Decimal("68"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        source_system=SourceSystem.LOTUS_ADVISE,
        product_version="v1",
        route="/advisory/policy-evaluations/pev_001/workflow",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:advisory-policy-evaluation-record",
        data_quality_status="quality_passed",
        freshness=freshness,
    )


def suitability_input(
    *,
    evaluation_status: str | None = "PENDING_REVIEW",
    open_requirement_count: int | None = 2,
    blocked_requirement_count: int | None = 0,
    sign_off_status: str | None = "PENDING_REVIEW",
    sign_off_blocker_count: int | None = 1,
    client_ready_publication: str | None = "BLOCKED",
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> MissingSuitabilityContextSignalInput:
    return MissingSuitabilityContextSignalInput(
        as_of_date=AS_OF_DATE,
        evaluation_status=evaluation_status,
        open_requirement_count=open_requirement_count,
        blocked_requirement_count=blocked_requirement_count,
        sign_off_status=sign_off_status,
        sign_off_blocker_count=sign_off_blocker_count,
        client_ready_publication=client_ready_publication,
        policy_ref=source_ref(freshness) if include_source_ref else None,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_missing_suitability_context_creates_compliance_review_candidate() -> None:
    first = evaluate_missing_suitability_context_signal(suitability_input(), policy())
    second = evaluate_missing_suitability_context_signal(suitability_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.MISSING_SUITABILITY_CONTEXT
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.COMPLIANCE_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.SUITABILITY_CONTEXT_MISSING,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_missing_suitability_context_does_not_create_candidate_when_advise_is_clear() -> None:
    result = evaluate_missing_suitability_context_signal(
        suitability_input(
            evaluation_status="READY",
            open_requirement_count=0,
            blocked_requirement_count=0,
            sign_off_status="SIGNED_OFF",
            sign_off_blocker_count=0,
        ),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_missing_suitability_context_missing_or_stale_source_blocks_claim() -> None:
    missing = evaluate_missing_suitability_context_signal(
        suitability_input(include_source_ref=False),
        policy(),
    )
    stale = evaluate_missing_suitability_context_signal(
        suitability_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert missing.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert stale.outcome is SignalEvaluationOutcome.BLOCKED
    assert stale.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert stale.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_missing_suitability_context_missing_status_or_count_blocks_claim() -> None:
    missing_status = evaluate_missing_suitability_context_signal(
        suitability_input(evaluation_status=None),
        policy(),
    )
    missing_count = evaluate_missing_suitability_context_signal(
        suitability_input(open_requirement_count=None),
        policy(),
    )

    assert missing_status.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing_status.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert missing_count.outcome is SignalEvaluationOutcome.BLOCKED
    assert missing_count.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_missing_suitability_context_requires_blocked_publication_boundary() -> None:
    result = evaluate_missing_suitability_context_signal(
        suitability_input(client_ready_publication="READY"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,)


def test_missing_suitability_context_blocks_missing_publication_boundary() -> None:
    result = evaluate_missing_suitability_context_signal(
        suitability_input(client_ready_publication=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_missing_suitability_context_duplicate_and_entitlement_are_guarded() -> None:
    duplicate = evaluate_missing_suitability_context_signal(
        suitability_input(duplicate_of_candidate_id="idea_missing_suitability_context_existing"),
        policy(),
    )
    denied = evaluate_missing_suitability_context_signal(
        suitability_input(entitlement_allowed=False),
        policy(),
    )

    assert duplicate.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert duplicate.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)
    assert denied.outcome is SignalEvaluationOutcome.BLOCKED
    assert denied.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_missing_suitability_context_rejects_negative_counts_and_naive_time() -> None:
    with pytest.raises(ValueError, match="blocked_requirement_count must be non-negative"):
        evaluate_missing_suitability_context_signal(
            suitability_input(blocked_requirement_count=-1),
            policy(),
        )

    invalid_input = MissingSuitabilityContextSignalInput(
        as_of_date=AS_OF_DATE,
        evaluation_status="PENDING_REVIEW",
        open_requirement_count=1,
        blocked_requirement_count=0,
        sign_off_status="PENDING_REVIEW",
        sign_off_blocker_count=0,
        client_ready_publication="BLOCKED",
        policy_ref=source_ref(),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
    )
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_missing_suitability_context_signal(invalid_input, policy())


@pytest.mark.parametrize(
    ("policy_version", "minimum_open_requirement_count", "candidate_score", "message"),
    [
        (" ", 1, Decimal("68"), "policy_version is required"),
        (
            "missing-suitability-context-review-v1",
            -1,
            Decimal("68"),
            "minimum_open_requirement_count must be non-negative",
        ),
        (
            "missing-suitability-context-review-v1",
            1,
            Decimal("101"),
            "candidate_score must be between 0 and 100",
        ),
    ],
)
def test_missing_suitability_policy_rejects_invalid_configuration(
    policy_version: str,
    minimum_open_requirement_count: int,
    candidate_score: Decimal,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        MissingSuitabilityContextSignalPolicy(
            policy_version=policy_version,
            minimum_open_requirement_count=minimum_open_requirement_count,
            candidate_score=candidate_score,
        )


def test_missing_suitability_count_validation_defends_post_blocking_invariant() -> None:
    with pytest.raises(
        ValueError,
        match="open_requirement_count must be available after blocking validation",
    ):
        validate_missing_suitability_counts(suitability_input(open_requirement_count=None))
