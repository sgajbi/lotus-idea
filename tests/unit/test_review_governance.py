from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    EvidenceSupportability,
    FeedbackCommand,
    FeedbackOutcome,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaFeedback,
    IdeaLifecycleStatus,
    IdeaScore,
    InvalidReviewAction,
    LineageRef,
    OpportunityFamily,
    QueueExclusionReason,
    ReasonCode,
    ReviewAccessScope,
    ReviewAction,
    ReviewActionPolicy,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewEntitlementDenied,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
    apply_review_action,
    build_review_queue,
    feedback_mutation_identity_from_command,
    record_feedback,
    review_mutation_identity_from_command,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 6, 21, 10, 5, tzinfo=UTC)


def source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:portfolio-state",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def evidence_packet(
    *,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
) -> IdeaEvidencePacket:
    source = source_ref()
    lineage = LineageRef(
        lineage_id="lineage:lotus-idea:review:test",
        source_refs=(source,),
        content_hash="sha256:review-lineage",
    )
    return IdeaEvidencePacket(
        evidence_packet_id="iep_review_test",
        supportability=supportability,
        source_refs=(source,),
        lineage_ref=lineage,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        unsupported_reasons=(
            (UnsupportedEvidenceReason.STALE_SOURCE,)
            if supportability is EvidenceSupportability.BLOCKED
            else ()
        ),
        created_at_utc=EVALUATED_AT,
    )


def candidate(
    candidate_id: str = "idea-review-001",
    *,
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.READY_FOR_REVIEW,
    review_posture: ReviewPosture = ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=candidate_id,
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=lifecycle_status,
        review_posture=review_posture,
        evidence_packet=evidence_packet(supportability=supportability),
        source_signal_ids=("signal-review-001",),
        score=IdeaScore(
            policy_version="idea-deterministic-ranking-v1",
            score=Decimal("82"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        created_at_utc=EVALUATED_AT,
        updated_at_utc=EVALUATED_AT,
    )


def access_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-private-bank-sg",
        book_id="book-advisor-001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-001",
    )


def advisor_context() -> ReviewActorContext:
    return ReviewActorContext(
        actor_subject="advisor-001",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({"tenant-private-bank-sg"}),
        book_ids=frozenset({"book-advisor-001"}),
        portfolio_ids=frozenset({"PB_SG_GLOBAL_BAL_001"}),
        client_ids=frozenset({"client-001"}),
    )


def decision_command(
    action: ReviewAction,
    *,
    actor: ReviewActorContext | None = None,
    suppression_reason: SuppressionReason | None = None,
    snoozed_until_utc: datetime | None = None,
) -> ReviewDecisionCommand:
    return ReviewDecisionCommand(
        review_id=f"review-{action.value}",
        action=action,
        actor=actor or advisor_context(),
        access_scope=access_scope(),
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        decided_at_utc=DECIDED_AT,
        suppression_reason=suppression_reason,
        snoozed_until_utc=snoozed_until_utc,
    )


def valid_decision_command(action: ReviewAction) -> ReviewDecisionCommand:
    if action is ReviewAction.SUPPRESS:
        return decision_command(
            action,
            suppression_reason=SuppressionReason.MANUAL_SUPPRESSION,
        )
    if action is ReviewAction.SNOOZE:
        return decision_command(
            action,
            snoozed_until_utc=datetime(2026, 6, 21, 11, 0, tzinfo=UTC),
        )
    return decision_command(action)


def test_advisor_can_approve_ready_candidate_without_downstream_authority() -> None:
    result = apply_review_action(
        candidate(),
        decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
    )

    assert result.candidate.lifecycle_status is IdeaLifecycleStatus.APPROVED
    assert result.candidate.review_posture is ReviewPosture.APPROVED_FOR_CONVERSION
    assert result.decision.grants_downstream_authority is False
    assert result.decision.reason_codes[0] is ReasonCode.REVIEW_APPROVED_FOR_CONVERSION
    assert result.audit_event.event_type == "idea.review.decision_recorded"
    assert result.audit_event.attributes["candidate_id"] == "idea-review-001"
    assert result.audit_event.attributes["prior_lifecycle_status"] == "ready_for_review"
    assert result.audit_event.attributes["prior_review_posture"] == "advisor_review_required"
    assert result.audit_event.attributes["requested_action"] == "approve_for_conversion"
    assert result.audit_event.attributes["policy_version"] == "idea-candidate-state-v1"
    assert "portfolio_id" not in result.audit_event.attributes
    assert "client_id" not in result.audit_event.attributes


def test_review_resource_identity_matches_the_persisted_decision_and_binds_business_fields() -> (
    None
):
    source_candidate = candidate()
    command = decision_command(ReviewAction.APPROVE_FOR_CONVERSION)
    result = apply_review_action(source_candidate, command)
    identity = review_mutation_identity_from_command(source_candidate, command)

    assert identity == result.decision.mutation_identity
    assert identity != replace(identity, candidate_id="idea-review-002")
    assert identity != replace(identity, event_name=ReviewAction.REJECT.value)
    assert identity != replace(identity, actor_subject="advisor-002")
    assert identity != replace(identity, evidence_content_hash="sha256:changed")
    assert identity != replace(identity, occurred_at_utc=DECIDED_AT + timedelta(seconds=1))


def test_feedback_resource_identity_matches_the_persisted_event() -> None:
    source_candidate = candidate()
    command = FeedbackCommand(
        feedback_id="feedback-identity-001",
        actor=advisor_context(),
        access_scope=access_scope(),
        outcome=FeedbackOutcome.USEFUL,
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        recorded_at_utc=DECIDED_AT,
    )
    result = record_feedback(source_candidate, command)

    assert feedback_mutation_identity_from_command(source_candidate, command) == (
        result.feedback_event.mutation_identity
    )


def test_review_entitlement_fails_closed_for_wrong_portfolio_scope() -> None:
    wrong_scope_actor = ReviewActorContext(
        actor_subject="advisor-001",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({"tenant-private-bank-sg"}),
        book_ids=frozenset({"book-advisor-001"}),
        portfolio_ids=frozenset({"different-portfolio"}),
        client_ids=frozenset({"client-001"}),
    )

    with pytest.raises(ReviewEntitlementDenied):
        apply_review_action(
            candidate(),
            decision_command(ReviewAction.REJECT, actor=wrong_scope_actor),
        )


def test_non_advisor_role_cannot_take_first_wave_review_action() -> None:
    pm_actor = ReviewActorContext(
        actor_subject="pm-001",
        role=ReviewActorRole.PORTFOLIO_MANAGER,
        tenant_ids=frozenset({"tenant-private-bank-sg"}),
        book_ids=frozenset({"book-advisor-001"}),
        portfolio_ids=frozenset({"PB_SG_GLOBAL_BAL_001"}),
        client_ids=frozenset({"client-001"}),
    )

    with pytest.raises(ReviewEntitlementDenied):
        apply_review_action(
            candidate(),
            decision_command(ReviewAction.APPROVE_FOR_CONVERSION, actor=pm_actor),
        )


def test_blocked_evidence_cannot_be_approved_for_conversion() -> None:
    with pytest.raises(InvalidReviewAction):
        apply_review_action(
            candidate(supportability=EvidenceSupportability.BLOCKED),
            decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
        )


def test_reject_and_no_action_remove_candidate_from_active_queue() -> None:
    rejected = apply_review_action(
        candidate("idea-reject"),
        decision_command(ReviewAction.REJECT),
    ).candidate
    no_action = apply_review_action(
        candidate("idea-no-action"),
        decision_command(ReviewAction.NO_ACTION),
    ).candidate

    queue = build_review_queue((rejected, no_action), evaluated_at_utc=DECIDED_AT)

    assert queue.items == ()
    assert [exclusion.reason for exclusion in queue.exclusions] == [
        QueueExclusionReason.REJECTED,
        QueueExclusionReason.CLOSED,
    ]


def test_suppress_and_snooze_update_queue_projection() -> None:
    suppressed = apply_review_action(
        candidate("idea-suppress"),
        decision_command(
            ReviewAction.SUPPRESS,
            suppression_reason=SuppressionReason.MANUAL_SUPPRESSION,
        ),
    )
    snoozed = apply_review_action(
        candidate("idea-snooze"),
        decision_command(
            ReviewAction.SNOOZE,
            snoozed_until_utc=datetime(2026, 6, 21, 11, 0, tzinfo=UTC),
        ),
    )
    assert snoozed.queue_snooze is not None

    queue = build_review_queue(
        (suppressed.candidate, snoozed.candidate),
        evaluated_at_utc=DECIDED_AT,
        snoozes=(snoozed.queue_snooze,),
    )

    assert queue.items == ()
    assert {exclusion.reason for exclusion in queue.exclusions} == {
        QueueExclusionReason.SUPPRESSED,
        QueueExclusionReason.SNOOZED,
    }


def test_escalation_changes_review_posture_without_granting_authority() -> None:
    pm_result = apply_review_action(
        candidate("idea-pm"),
        decision_command(ReviewAction.ESCALATE_TO_PM),
    )
    compliance_result = apply_review_action(
        candidate("idea-compliance"),
        decision_command(ReviewAction.ESCALATE_TO_COMPLIANCE),
    )

    assert pm_result.candidate.review_posture is ReviewPosture.PM_REVIEW_REQUIRED
    assert compliance_result.candidate.review_posture is ReviewPosture.COMPLIANCE_REVIEW_REQUIRED
    assert pm_result.decision.grants_downstream_authority is False
    assert compliance_result.decision.grants_downstream_authority is False


def test_feedback_event_is_source_provenanced_and_audited_without_sensitive_scope() -> None:
    result = record_feedback(
        candidate(),
        FeedbackCommand(
            feedback_id="feedback-001",
            actor=advisor_context(),
            access_scope=access_scope(),
            outcome=FeedbackOutcome.USEFUL,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            recorded_at_utc=DECIDED_AT,
        ),
    )

    assert result.feedback_event.candidate_id == "idea-review-001"
    assert result.feedback_event.evidence_packet_id == "iep_review_test"
    assert result.feedback_event.evidence_content_hash == "sha256:review-lineage"
    assert result.feedback_event.source_signal_ids == ("signal-review-001",)
    assert result.audit_event.event_type == "idea.feedback.recorded"
    assert "portfolio_id" not in result.audit_event.attributes
    assert "client_id" not in result.audit_event.attributes


def test_review_commands_validate_required_action_fields() -> None:
    with pytest.raises(ValueError, match="suppression_reason is required"):
        decision_command(ReviewAction.SUPPRESS)

    with pytest.raises(ValueError, match="snoozed_until_utc is required"):
        decision_command(ReviewAction.SNOOZE)

    with pytest.raises(ValueError, match="snoozed_until_utc must be after"):
        decision_command(
            ReviewAction.SNOOZE,
            snoozed_until_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="tenant_ids is required"):
        ReviewActorContext(
            actor_subject="advisor-001",
            role=ReviewActorRole.ADVISOR,
            tenant_ids=frozenset(),
            book_ids=frozenset({"book-advisor-001"}),
            portfolio_ids=frozenset({"PB_SG_GLOBAL_BAL_001"}),
            client_ids=frozenset({"client-001"}),
        )


def test_review_policy_and_scope_validation_fail_closed() -> None:
    with pytest.raises(ValueError, match="tenant_id is required"):
        ReviewAccessScope(
            tenant_id=" ",
            book_id="book-advisor-001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            client_id="client-001",
        )

    with pytest.raises(ValueError, match="portfolio_ids cannot contain blank"):
        ReviewActorContext(
            actor_subject="advisor-001",
            role=ReviewActorRole.ADVISOR,
            tenant_ids=frozenset({"tenant-private-bank-sg"}),
            book_ids=frozenset({"book-advisor-001"}),
            portfolio_ids=frozenset({" "}),
            client_ids=frozenset({"client-001"}),
        )

    with pytest.raises(ValueError, match="allowed roles missing"):
        ReviewActionPolicy(allowed_roles_by_action={})

    roles_by_action = {action: frozenset({ReviewActorRole.ADVISOR}) for action in ReviewAction}
    roles_by_action[ReviewAction.REJECT] = frozenset()

    with pytest.raises(ValueError, match="allowed roles required"):
        ReviewActionPolicy(allowed_roles_by_action=roles_by_action)


def test_review_and_feedback_commands_validate_required_reason_and_time_fields() -> None:
    with pytest.raises(ValueError, match="decided_at_utc must be timezone-aware"):
        ReviewDecisionCommand(
            review_id="review-naive",
            action=ReviewAction.REJECT,
            actor=advisor_context(),
            access_scope=access_scope(),
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            decided_at_utc=datetime(2026, 6, 21, 10, 0),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        ReviewDecisionCommand(
            review_id="review-no-reason",
            action=ReviewAction.REJECT,
            actor=advisor_context(),
            access_scope=access_scope(),
            reason_codes=(),
            decided_at_utc=DECIDED_AT,
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        GovernedReviewDecision(
            review_id="review-no-decision-reason",
            candidate_id="idea-review-001",
            evidence_packet_id="iep_review_test",
            evidence_content_hash="sha256:review-lineage",
            action=ReviewAction.REJECT,
            resulting_posture=ReviewPosture.REJECTED,
            actor_subject="advisor-001",
            actor_role=ReviewActorRole.ADVISOR,
            reason_codes=(),
            decided_at_utc=DECIDED_AT,
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        FeedbackCommand(
            feedback_id="feedback-no-reason",
            actor=advisor_context(),
            access_scope=access_scope(),
            outcome=FeedbackOutcome.NOT_USEFUL,
            reason_codes=(),
            recorded_at_utc=DECIDED_AT,
        )

    with pytest.raises(ValueError, match="source_signal_ids is required"):
        GovernedFeedbackEvent(
            feedback=IdeaFeedback(
                feedback_id="feedback-no-source",
                outcome=FeedbackOutcome.MISSING_CONTEXT,
                actor_role=ReviewActorRole.ADVISOR.value,
                reason_codes=(ReasonCode.FEEDBACK_RECORDED,),
                recorded_at_utc=DECIDED_AT,
            ),
            candidate_id="idea-review-001",
            evidence_packet_id="iep_review_test",
            evidence_content_hash="sha256:review-lineage",
            source_signal_ids=(),
            actor_subject="advisor-001",
            actor_role=ReviewActorRole.ADVISOR,
        )


def test_review_lifecycle_edges_are_explicit() -> None:
    approved_from_reviewed = apply_review_action(
        candidate(
            lifecycle_status=IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
            review_posture=ReviewPosture.ADVISOR_REVIEWED,
        ),
        decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
    )

    assert approved_from_reviewed.candidate.lifecycle_status is IdeaLifecycleStatus.APPROVED

    with pytest.raises(InvalidReviewAction):
        apply_review_action(
            candidate(lifecycle_status=IdeaLifecycleStatus.GENERATED),
            decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
        )

    with pytest.raises(InvalidReviewAction):
        apply_review_action(
            candidate(lifecycle_status=IdeaLifecycleStatus.GENERATED),
            decision_command(ReviewAction.REJECT),
        )


@pytest.mark.parametrize("action", list(ReviewAction))
@pytest.mark.parametrize(
    ("lifecycle_status", "review_posture"),
    (
        (IdeaLifecycleStatus.APPROVED, ReviewPosture.APPROVED_FOR_CONVERSION),
        (IdeaLifecycleStatus.REJECTED, ReviewPosture.REJECTED),
        (IdeaLifecycleStatus.EXPIRED, ReviewPosture.NO_ACTION),
        (IdeaLifecycleStatus.CLOSED, ReviewPosture.NO_ACTION),
    ),
)
def test_every_review_action_fails_closed_for_non_reviewable_states(
    action: ReviewAction,
    lifecycle_status: IdeaLifecycleStatus,
    review_posture: ReviewPosture,
) -> None:
    with pytest.raises(InvalidReviewAction) as captured:
        apply_review_action(
            candidate(
                lifecycle_status=lifecycle_status,
                review_posture=review_posture,
            ),
            valid_decision_command(action),
        )

    assert captured.value.lifecycle_status is lifecycle_status
    assert captured.value.review_posture is review_posture
    assert captured.value.policy_version == "idea-candidate-state-v1"


@pytest.mark.parametrize("action", list(ReviewAction))
def test_repeated_review_action_is_deterministic_or_terminally_rejected(
    action: ReviewAction,
) -> None:
    command = valid_decision_command(action)
    first = apply_review_action(candidate(), command)

    if action in {
        ReviewAction.APPROVE_FOR_CONVERSION,
        ReviewAction.REJECT,
        ReviewAction.NO_ACTION,
    }:
        with pytest.raises(InvalidReviewAction):
            apply_review_action(first.candidate, command)
        return

    repeated = apply_review_action(first.candidate, command)
    assert repeated.candidate == first.candidate
    assert repeated.decision == first.decision
