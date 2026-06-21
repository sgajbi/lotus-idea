from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.review_workflow import (
    ApplyReviewActionToRepositoryCommand,
    RecordFeedbackToRepositoryCommand,
    apply_review_action_to_repository,
    record_feedback_to_repository,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    EvidenceSupportability,
    FeedbackCommand,
    FeedbackOutcome,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    InMemoryIdeaRepository,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    record_feedback,
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


def review_candidate(candidate_id: str = "idea-review-001") -> IdeaCandidate:
    source = source_ref()
    lineage = LineageRef(
        lineage_id="lineage:lotus-idea:review-workflow:test",
        source_refs=(source,),
        content_hash="sha256:review-workflow-lineage",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id="iep_review_workflow_test",
        supportability=EvidenceSupportability.READY,
        source_refs=(source,),
        lineage_ref=lineage,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=EVALUATED_AT,
    )
    return IdeaCandidate(
        candidate_id=candidate_id,
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=("signal-review-workflow-001",),
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
    review_id: str | None = None,
    suppression_reason: SuppressionReason | None = None,
) -> ReviewDecisionCommand:
    return ReviewDecisionCommand(
        review_id=review_id or f"review-{action.value}",
        action=action,
        actor=advisor_context(),
        access_scope=access_scope(),
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        decided_at_utc=DECIDED_AT,
        suppression_reason=suppression_reason,
    )


def feedback_command() -> FeedbackCommand:
    return FeedbackCommand(
        feedback_id="feedback-review-workflow-001",
        actor=advisor_context(),
        access_scope=access_scope(),
        outcome=FeedbackOutcome.USEFUL,
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        recorded_at_utc=DECIDED_AT,
    )


def repository_with_candidate() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    result = repository.persist_candidate(
        review_candidate(),
        idempotency_key="signal-ingestion:review-workflow:001",
        payload={"candidate_id": "idea-review-001"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert result.decision is CandidatePersistenceDecision.ACCEPTED
    return repository


def test_apply_review_action_to_repository_persists_candidate_decision_and_audit() -> None:
    repository = repository_with_candidate()

    result = apply_review_action_to_repository(
        ApplyReviewActionToRepositoryCommand(
            candidate_id="idea-review-001",
            review=decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
            idempotency_key="review-action:approve:001",
        ),
        repository=repository,
    )

    assert result.review_result is not None
    assert result.persistence.decision is ReviewPersistenceDecision.ACCEPTED
    assert result.persistence.record is not None
    assert result.persistence.record.candidate.lifecycle_status is IdeaLifecycleStatus.APPROVED
    assert (
        result.persistence.record.candidate.review_posture is ReviewPosture.APPROVED_FOR_CONVERSION
    )
    assert len(result.persistence.record.review_decisions) == 1
    assert result.persistence.record.review_decisions[0].grants_downstream_authority is False
    assert result.persistence.record.audit_events[-1].event_type == "idea.review.decision_recorded"
    assert "portfolio_id" not in result.persistence.record.audit_events[-1].attributes
    assert (
        result.persistence.record.lifecycle_history[-1].target_status
        is IdeaLifecycleStatus.APPROVED
    )


def test_apply_review_action_to_repository_replays_before_reapplying_domain_transition() -> None:
    repository = repository_with_candidate()
    command = ApplyReviewActionToRepositoryCommand(
        candidate_id="idea-review-001",
        review=decision_command(ReviewAction.APPROVE_FOR_CONVERSION),
        idempotency_key="review-action:approve:001",
    )
    first = apply_review_action_to_repository(command, repository=repository)

    replayed = apply_review_action_to_repository(command, repository=repository)

    assert first.persistence.record is not None
    assert replayed.review_result is None
    assert replayed.persistence.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed.persistence.record == first.persistence.record
    assert len(replayed.persistence.record.review_decisions) == 1


def test_apply_review_action_to_repository_detects_idempotency_conflict_without_mutation() -> None:
    repository = repository_with_candidate()
    apply_review_action_to_repository(
        ApplyReviewActionToRepositoryCommand(
            candidate_id="idea-review-001",
            review=decision_command(
                ReviewAction.SUPPRESS, suppression_reason=SuppressionReason.MANUAL_SUPPRESSION
            ),
            idempotency_key="review-action:mutable:001",
        ),
        repository=repository,
    )

    conflict = apply_review_action_to_repository(
        ApplyReviewActionToRepositoryCommand(
            candidate_id="idea-review-001",
            review=decision_command(
                ReviewAction.SUPPRESS,
                review_id="review-suppress-different",
                suppression_reason=SuppressionReason.MANUAL_SUPPRESSION,
            ),
            idempotency_key="review-action:mutable:001",
        ),
        repository=repository,
    )

    assert conflict.review_result is None
    assert conflict.persistence.decision is ReviewPersistenceDecision.CONFLICT
    assert conflict.persistence.record is not None
    assert len(conflict.persistence.record.review_decisions) == 1


def test_record_feedback_to_repository_persists_source_provenanced_feedback() -> None:
    repository = repository_with_candidate()

    result = record_feedback_to_repository(
        RecordFeedbackToRepositoryCommand(
            candidate_id="idea-review-001",
            feedback=feedback_command(),
            idempotency_key="review-feedback:useful:001",
        ),
        repository=repository,
    )

    assert result.feedback_result is not None
    assert result.persistence.decision is ReviewPersistenceDecision.ACCEPTED
    assert result.persistence.record is not None
    assert len(result.persistence.record.feedback_events) == 1
    assert result.persistence.record.feedback_events[0].candidate_id == "idea-review-001"
    assert result.persistence.record.feedback_events[0].source_signal_ids == (
        "signal-review-workflow-001",
    )
    assert result.persistence.record.audit_events[-1].event_type == "idea.feedback.recorded"


def test_record_feedback_to_repository_replays_before_reapplying_domain_feedback() -> None:
    repository = repository_with_candidate()
    command = RecordFeedbackToRepositoryCommand(
        candidate_id="idea-review-001",
        feedback=feedback_command(),
        idempotency_key="review-feedback:useful:001",
    )
    first = record_feedback_to_repository(command, repository=repository)

    replayed = record_feedback_to_repository(command, repository=repository)

    assert first.persistence.record is not None
    assert replayed.feedback_result is None
    assert replayed.persistence.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed.persistence.record == first.persistence.record
    assert len(replayed.persistence.record.feedback_events) == 1


def test_record_feedback_to_repository_returns_not_found_for_missing_candidate() -> None:
    repository = InMemoryIdeaRepository()

    result = record_feedback_to_repository(
        RecordFeedbackToRepositoryCommand(
            candidate_id="missing-candidate",
            feedback=feedback_command(),
            idempotency_key="review-feedback:missing:001",
        ),
        repository=repository,
    )

    assert result.feedback_result is None
    assert result.persistence.decision is ReviewPersistenceDecision.NOT_FOUND
    assert result.persistence.record is None


def test_repository_feedback_event_returns_not_found_when_snapshot_lacks_candidate() -> None:
    repository = InMemoryIdeaRepository()
    feedback_result = record_feedback(review_candidate("missing-candidate"), feedback_command())

    result = repository.record_feedback_event(
        feedback_result,
        idempotency_key="review-feedback:repository-missing:001",
        payload={
            "candidate_id": "missing-candidate",
            "feedback_id": "feedback-review-workflow-001",
        },
    )

    assert result.decision is ReviewPersistenceDecision.NOT_FOUND
    assert result.record is None


def test_review_workflow_commands_reject_blank_identity() -> None:
    with pytest.raises(ValueError, match="candidate_id is required"):
        ApplyReviewActionToRepositoryCommand(
            candidate_id=" ",
            review=decision_command(ReviewAction.REJECT),
            idempotency_key="review-action:blank-candidate",
        )

    with pytest.raises(ValueError, match="idempotency_key is required"):
        RecordFeedbackToRepositoryCommand(
            candidate_id="idea-review-001",
            feedback=feedback_command(),
            idempotency_key=" ",
        )


def test_review_workflow_returns_not_found_for_missing_candidate() -> None:
    repository = InMemoryIdeaRepository()

    result = apply_review_action_to_repository(
        ApplyReviewActionToRepositoryCommand(
            candidate_id="missing-candidate",
            review=decision_command(ReviewAction.REJECT),
            idempotency_key="review-action:missing:001",
        ),
        repository=repository,
    )

    assert result.review_result is None
    assert result.persistence.decision is ReviewPersistenceDecision.NOT_FOUND
    assert result.persistence.record is None
