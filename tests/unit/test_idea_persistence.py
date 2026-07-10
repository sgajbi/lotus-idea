from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIExplanationLineagePersistenceDecision,
    AIExplanationResult,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    CandidatePersistenceDecision,
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    ConversionTarget,
    EvidencePackPersistenceDecision,
    EvidenceFreshness,
    EvidenceReplayStatus,
    EventLineageContext,
    FeedbackCommand,
    FeedbackOutcome,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    InvalidLifecycleTransition,
    LifecyclePersistenceDecision,
    OutboxEventStatus,
    ReasonCode,
    ReportEvidencePackCommand,
    ReportEvidencePackPurpose,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    apply_review_action,
    build_ai_explanation_request,
    evaluate_high_cash_signal,
    deterministic_ai_fallback,
    record_feedback,
    record_conversion_outcome,
    request_conversion_intent,
    request_report_evidence_pack,
)


AS_OF_DATE = datetime(2026, 6, 21, 10, 0, tzinfo=UTC).date()
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    content_hash: str | None = None,
) -> SourceRef:
    route_by_product = {
        "lotus-core:PortfolioStateSnapshot:v1": "/integration/portfolios/{portfolio_id}/core-snapshot",
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/cash-balances",
        "lotus-core:PortfolioCashMovementSummary:v1": "/portfolios/{portfolio_id}/cash-movement-summary",
        "lotus-core:PortfolioCashflowProjection:v1": "/portfolios/{portfolio_id}/cashflow-projection",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=content_hash or f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=freshness,
    )


def high_cash_candidate_source_refs(
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    cashflow_hash: str | None = None,
) -> tuple[SourceRef, ...]:
    return (
        source_ref("lotus-core:PortfolioStateSnapshot:v1", freshness=freshness),
        source_ref("lotus-core:HoldingsAsOf:v1", freshness=freshness),
        source_ref("lotus-core:PortfolioCashMovementSummary:v1", freshness=freshness),
        source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            freshness=freshness,
            content_hash=cashflow_hash,
        ),
    )


def high_cash_candidate() -> tuple[IdeaCandidate, tuple[SourceRef, ...]]:
    refs = high_cash_candidate_source_refs()
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=AS_OF_DATE,
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=refs[0],
            holdings_ref=refs[1],
            cash_movement_ref=refs[2],
            cashflow_projection_ref=refs[3],
            evaluated_at_utc=EVALUATED_AT,
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    assert result.candidate is not None
    return result.candidate, refs


def approved_high_cash_candidate() -> tuple[IdeaCandidate, tuple[SourceRef, ...]]:
    candidate, refs = high_cash_candidate()
    return (
        replace(
            candidate,
            lifecycle_status=IdeaLifecycleStatus.APPROVED,
            review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        ),
        refs,
    )


def review_ready_high_cash_candidate() -> tuple[IdeaCandidate, tuple[SourceRef, ...]]:
    candidate, refs = high_cash_candidate()
    return (
        replace(
            candidate,
            lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ),
        refs,
    )


def review_access_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-sg-001",
        book_id="book-private-bank-sg",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        client_id="client-001",
    )


def advisor_actor_context() -> ReviewActorContext:
    return ReviewActorContext(
        actor_subject="advisor-001",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({"tenant-sg-001"}),
        book_ids=frozenset({"book-private-bank-sg"}),
        portfolio_ids=frozenset({"PB_SG_GLOBAL_BAL_001"}),
        client_ids=frozenset({"client-001"}),
    )


def review_decision_command(
    *,
    review_id: str = "review-decision-001",
    decided_at_utc: datetime = datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
) -> ReviewDecisionCommand:
    return ReviewDecisionCommand(
        review_id=review_id,
        action=ReviewAction.APPROVE_FOR_CONVERSION,
        actor=advisor_actor_context(),
        access_scope=review_access_scope(),
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        decided_at_utc=decided_at_utc,
    )


def feedback_command(
    *,
    feedback_id: str = "feedback-001",
    recorded_at_utc: datetime = datetime(2026, 6, 21, 10, 8, tzinfo=UTC),
) -> FeedbackCommand:
    return FeedbackCommand(
        feedback_id=feedback_id,
        actor=advisor_actor_context(),
        access_scope=review_access_scope(),
        outcome=FeedbackOutcome.USEFUL,
        reason_codes=(ReasonCode.FEEDBACK_RECORDED,),
        recorded_at_utc=recorded_at_utc,
    )


def conversion_intent_command(
    *,
    target: ConversionTarget = ConversionTarget.REPORT_EVIDENCE,
) -> ConversionIntentCommand:
    return ConversionIntentCommand(
        conversion_intent_id=f"conversion-{target.value}-001",
        target=target,
        actor_subject="advisor-001",
        idempotency_key=f"conversion-{target.value}-key-001",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=datetime(2026, 6, 21, 10, 15, tzinfo=UTC),
    )


def report_evidence_pack_command() -> ReportEvidencePackCommand:
    return ReportEvidencePackCommand(
        report_evidence_pack_id="report-evidence-pack-001",
        purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
        actor_subject="advisor-001",
        idempotency_key="report-evidence-pack-key-001",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=datetime(2026, 6, 21, 10, 25, tzinfo=UTC),
        retention_policy_ref="lotus-report:idea-evidence-retention:v1",
    )


def ai_explanation_result_for_candidate(
    candidate: IdeaCandidate,
    *,
    request_id: str = "ai-lineage-request-001",
    fallback_reason: AIFallbackReason = AIFallbackReason.AI_UNAVAILABLE,
) -> AIExplanationResult:
    request = build_ai_explanation_request(
        candidate,
        AIExplanationCommand(
            request_id=request_id,
            actor_subject="advisor-001",
            workflow_pack=AIWorkflowPackRef(
                workflow_pack_id="lotus-ai:idea-explanation:v1",
                workflow_pack_version="v1",
                purpose=AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
                evaluation_ref="lotus-ai:governed-verifier:v1",
            ),
            approved_metadata={"audience": "internal_advisor_review"},
            requested_at_utc=datetime(2026, 6, 21, 10, 12, tzinfo=UTC),
        ),
    )
    return deterministic_ai_fallback(
        request,
        fallback_reason=fallback_reason,
        occurred_at_utc=datetime(2026, 6, 21, 10, 12, tzinfo=UTC),
    )


def test_persist_candidate_accepts_once_and_replays_same_idempotency_payload() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    first_lineage = EventLineageContext(
        correlation_id="corr-candidate-workflow-001",
        trace_id="trace-candidate-request-001",
    )

    first = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
        event_lineage=first_lineage,
    )
    second = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
        event_lineage=EventLineageContext(
            correlation_id="corr-candidate-workflow-001",
            trace_id="trace-candidate-retry-002",
        ),
    )

    assert first.decision is CandidatePersistenceDecision.ACCEPTED
    assert second.decision is CandidatePersistenceDecision.REPLAYED
    assert first.record == second.record
    assert first.record is not None
    assert len(first.record.audit_events) == 1
    assert first.record.audit_events[0].event_type == "idea.candidate.persisted"
    assert len(repository.snapshot().outbox_events) == 1
    event = next(iter(repository.snapshot().outbox_events.values()))
    assert event.event_type == "idea.candidate.persisted.v1"
    assert event.status is OutboxEventStatus.PENDING
    assert event.aggregate_id == candidate.candidate_id
    assert event.payload == {
        "candidate_family": "high_cash",
        "lifecycle_status": "generated",
        "review_posture": "advisor_review_required",
    }
    assert event.idempotency_fingerprint is not None
    assert "signal-ingestion:high-cash:001" not in event.idempotency_fingerprint
    assert event.correlation_id == first_lineage.correlation_id
    assert event.trace_id == first_lineage.trace_id


def test_persist_candidate_rejects_idempotency_conflict_without_extra_audit_event() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    conflict = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": ["sha256:different"]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert conflict.decision is CandidatePersistenceDecision.CONFLICT
    assert conflict.audit_event is None
    assert conflict.record is not None
    assert len(conflict.record.audit_events) == 1
    assert len(repository.snapshot().outbox_events) == 1


def test_duplicate_candidate_identity_is_not_persisted_twice() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    duplicate = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:002",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert duplicate.decision is CandidatePersistenceDecision.DUPLICATE_CANDIDATE
    assert duplicate.record is not None
    assert len(duplicate.record.audit_events) == 1


def test_replay_matches_hash_or_returns_stale_and_mismatch_posture() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    matched = repository.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=refs,
        evaluated_at_utc=EVALUATED_AT,
    )
    stale = repository.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=high_cash_candidate_source_refs(freshness=EvidenceFreshness.STALE),
        evaluated_at_utc=EVALUATED_AT,
    )
    mismatch = repository.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=high_cash_candidate_source_refs(
            cashflow_hash="sha256:changed-cashflow"
        ),
        evaluated_at_utc=EVALUATED_AT,
    )

    assert matched.status is EvidenceReplayStatus.MATCHED
    assert matched.current_evidence_hash == persisted.record.evidence_hash
    assert stale.status is EvidenceReplayStatus.STALE_SOURCE
    assert mismatch.status is EvidenceReplayStatus.HASH_MISMATCH


def test_replay_returns_not_found_for_missing_candidate() -> None:
    repository = InMemoryIdeaRepository()

    replay = repository.replay_evidence(
        "missing-candidate",
        current_source_refs=high_cash_candidate_source_refs(),
        evaluated_at_utc=EVALUATED_AT,
    )

    assert replay.status is EvidenceReplayStatus.NOT_FOUND
    assert replay.record is None


def test_expired_candidate_replay_returns_expired_posture_with_audit_history() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    expired = repository.transition_candidate(
        persisted.record.candidate.candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        actor_subject="signal-expiry-worker",
        occurred_at_utc=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
    )
    replay = repository.replay_evidence(
        expired.candidate.candidate_id,
        current_source_refs=refs,
        evaluated_at_utc=datetime(2026, 6, 22, 10, 1, tzinfo=UTC),
    )

    assert replay.status is EvidenceReplayStatus.EXPIRED
    assert expired.lifecycle_history[-1].target_status is IdeaLifecycleStatus.EXPIRED
    assert expired.audit_events[-1].event_type == "idea.lifecycle.transitioned"


def test_lifecycle_transition_records_idempotent_audit_history() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    first = repository.record_lifecycle_transition(
        persisted.record.candidate.candidate_id,
        IdeaLifecycleStatus.ENRICHED,
        idempotency_key="lifecycle:enriched:001",
        payload={"target_status": "enriched", "transition_id": "transition-enriched-001"},
        actor_subject="idea-lifecycle-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
        transition_id="transition-enriched-001",
        reason_codes=("review_required",),
    )
    replayed = repository.record_lifecycle_transition(
        persisted.record.candidate.candidate_id,
        IdeaLifecycleStatus.ENRICHED,
        idempotency_key="lifecycle:enriched:001",
        payload={"target_status": "enriched", "transition_id": "transition-enriched-001"},
        actor_subject="idea-lifecycle-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
        transition_id="transition-enriched-001",
        reason_codes=("review_required",),
    )
    conflict = repository.record_lifecycle_transition(
        persisted.record.candidate.candidate_id,
        IdeaLifecycleStatus.SCORED,
        idempotency_key="lifecycle:enriched:001",
        payload={"target_status": "scored", "transition_id": "transition-scored-001"},
        actor_subject="idea-lifecycle-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 2, tzinfo=UTC),
        transition_id="transition-scored-001",
        reason_codes=("review_required",),
    )

    assert first.decision is LifecyclePersistenceDecision.ACCEPTED
    assert replayed.decision is LifecyclePersistenceDecision.REPLAYED
    assert conflict.decision is LifecyclePersistenceDecision.CONFLICT
    assert first.record is not None
    assert first.record.candidate.lifecycle_status is IdeaLifecycleStatus.ENRICHED
    assert first.record.lifecycle_history[-1].actor_subject == "idea-lifecycle-worker"
    assert first.record.audit_events[-1].attributes["transition_id"] == "transition-enriched-001"
    assert [event.event_type for event in repository.snapshot().outbox_events.values()] == [
        "idea.candidate.persisted.v1",
        "idea.lifecycle.transitioned.v1",
    ]
    lifecycle_event = tuple(repository.snapshot().outbox_events.values())[-1]
    assert lifecycle_event.payload == {
        "source_status": "generated",
        "target_status": "enriched",
    }
    assert lifecycle_event.status is OutboxEventStatus.PENDING


def test_lifecycle_transition_returns_not_found_and_blocks_invalid_transition() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    not_found = repository.record_lifecycle_transition(
        "missing-candidate",
        IdeaLifecycleStatus.ENRICHED,
        idempotency_key="lifecycle:missing:001",
        payload={"target_status": "enriched", "transition_id": "transition-missing-001"},
        actor_subject="idea-lifecycle-worker",
        occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
        transition_id="transition-missing-001",
        reason_codes=("review_required",),
    )

    assert not_found.decision is LifecyclePersistenceDecision.NOT_FOUND
    with pytest.raises(InvalidLifecycleTransition):
        repository.record_lifecycle_transition(
            persisted.record.candidate.candidate_id,
            IdeaLifecycleStatus.READY_FOR_REVIEW,
            idempotency_key="lifecycle:invalid:001",
            payload={
                "target_status": "ready_for_review",
                "transition_id": "transition-invalid-001",
            },
            actor_subject="idea-lifecycle-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
            transition_id="transition-invalid-001",
            reason_codes=("review_required",),
        )


def test_lifecycle_transition_blocks_downstream_authority_targets_before_outbox() -> None:
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:approved-high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    with pytest.raises(InvalidLifecycleTransition):
        repository.record_lifecycle_transition(
            persisted.record.candidate.candidate_id,
            IdeaLifecycleStatus.ACCEPTED,
            idempotency_key="lifecycle:accepted:forbidden",
            payload={
                "target_status": "accepted",
                "transition_id": "transition-accepted-forbidden-001",
            },
            actor_subject="idea-lifecycle-worker",
            occurred_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
            transition_id="transition-accepted-forbidden-001",
            reason_codes=("review_required",),
        )

    snapshot = repository.snapshot()
    assert snapshot.candidate_records[candidate.candidate_id].candidate.lifecycle_status is (
        IdeaLifecycleStatus.APPROVED
    )
    lifecycle_outbox_targets = {
        event.payload.get("target_status")
        for event in snapshot.outbox_events.values()
        if event.event_type == "idea.lifecycle.transitioned.v1"
    }
    assert lifecycle_outbox_targets.isdisjoint({"accepted", "executed"})


def test_repository_snapshot_recovers_candidate_idempotency_and_replay_state() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None

    recovered = InMemoryIdeaRepository(repository.snapshot())
    replayed = recovered.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    replay = recovered.replay_evidence(
        persisted.record.candidate.candidate_id,
        current_source_refs=refs,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert replayed.decision is CandidatePersistenceDecision.REPLAYED
    assert replay.status is EvidenceReplayStatus.MATCHED
    assert recovered.snapshot().outbox_events == repository.snapshot().outbox_events


def test_ai_explanation_lineage_records_replays_and_conflicts_by_request_id() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:ai-lineage:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    result = ai_explanation_result_for_candidate(persisted.record.candidate)
    changed_result = ai_explanation_result_for_candidate(
        persisted.record.candidate,
        fallback_reason=AIFallbackReason.WORKFLOW_NOT_APPROVED,
    )

    accepted = repository.record_ai_explanation_lineage(result)
    replayed = repository.record_ai_explanation_lineage(result)
    conflict = repository.record_ai_explanation_lineage(changed_result)

    assert accepted.decision is AIExplanationLineagePersistenceDecision.ACCEPTED
    assert replayed.decision is AIExplanationLineagePersistenceDecision.REPLAYED
    assert conflict.decision is AIExplanationLineagePersistenceDecision.CONFLICT
    assert accepted.lineage_record is not None
    assert accepted.lineage_record.request_id == "ai-lineage-request-001"
    assert accepted.lineage_record.candidate_id == candidate.candidate_id
    assert accepted.lineage_record.fallback_used is True
    assert accepted.lineage_record.grants_downstream_authority is False
    assert accepted.lineage_record.claim_ids == ()
    assert accepted.lineage_record.proposed_action_types == ()
    assert accepted.record is not None
    assert len(accepted.record.ai_explanation_lineage_records) == 1
    assert accepted.audit_event is not None
    assert accepted.audit_event.event_type == "idea.ai_explanation.evaluated"
    assert len(repository.snapshot().outbox_events) == 1


def test_ai_explanation_lineage_snapshot_recovers_request_index() -> None:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:ai-lineage-snapshot:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    result = ai_explanation_result_for_candidate(persisted.record.candidate)
    accepted = repository.record_ai_explanation_lineage(result)
    assert accepted.lineage_record is not None

    recovered = InMemoryIdeaRepository(repository.snapshot())
    replayed = recovered.record_ai_explanation_lineage(result)

    assert replayed.decision is AIExplanationLineagePersistenceDecision.REPLAYED
    assert replayed.lineage_record == accepted.lineage_record
    assert recovered.snapshot().ai_explanation_lineage_candidates == {
        "ai-lineage-request-001": candidate.candidate_id,
    }


def test_review_action_persistence_replays_conflicts_and_returns_not_found() -> None:
    candidate, refs = review_ready_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:review-ready:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    result = apply_review_action(persisted.record.candidate, review_decision_command())
    payload = {"review_id": result.decision.review_id, "action": result.decision.action.value}

    first = repository.record_review_action(
        result,
        idempotency_key="review-action-key-001",
        payload=payload,
    )
    replayed = repository.record_review_action(
        result,
        idempotency_key="review-action-key-001",
        payload=payload,
    )
    conflict = repository.record_review_action(
        result,
        idempotency_key="review-action-key-001",
        payload={"review_id": result.decision.review_id, "action": "reject"},
    )
    missing_candidate, _ = review_ready_high_cash_candidate()
    missing_result = apply_review_action(missing_candidate, review_decision_command())
    not_found = InMemoryIdeaRepository().record_review_action(
        missing_result,
        idempotency_key="review-action-key-missing",
        payload=payload,
    )

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed.record == first.record
    assert conflict.decision is ReviewPersistenceDecision.CONFLICT
    assert conflict.record == first.record
    assert not_found.decision is ReviewPersistenceDecision.NOT_FOUND
    assert not_found.record is None


def test_feedback_persistence_replays_conflicts_and_returns_not_found() -> None:
    candidate, refs = review_ready_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:feedback-ready:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    result = record_feedback(persisted.record.candidate, feedback_command())
    payload = {
        "feedback_id": result.feedback_event.feedback.feedback_id,
        "outcome": result.feedback_event.feedback.outcome.value,
    }

    first = repository.record_feedback_event(
        result,
        idempotency_key="feedback-key-001",
        payload=payload,
    )
    replayed = repository.record_feedback_event(
        result,
        idempotency_key="feedback-key-001",
        payload=payload,
    )
    conflict = repository.record_feedback_event(
        result,
        idempotency_key="feedback-key-001",
        payload={"feedback_id": result.feedback_event.feedback.feedback_id, "outcome": "ignored"},
    )
    missing_candidate, _ = review_ready_high_cash_candidate()
    missing_result = record_feedback(missing_candidate, feedback_command())
    not_found = InMemoryIdeaRepository().record_feedback_event(
        missing_result,
        idempotency_key="feedback-key-missing",
        payload=payload,
    )

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert replayed.record == first.record
    assert conflict.decision is ReviewPersistenceDecision.CONFLICT
    assert conflict.record == first.record
    assert not_found.decision is ReviewPersistenceDecision.NOT_FOUND
    assert not_found.record is None


def test_ai_explanation_lineage_returns_not_found_without_candidate_record() -> None:
    candidate, _ = high_cash_candidate()
    result = ai_explanation_result_for_candidate(candidate)

    missing = InMemoryIdeaRepository().record_ai_explanation_lineage(result)

    assert missing.decision is AIExplanationLineagePersistenceDecision.NOT_FOUND
    assert missing.record is None
    assert missing.lineage_record is None


def test_conversion_intent_persistence_records_lifecycle_audit_and_idempotency() -> None:
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:approved-high-cash:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    command = conversion_intent_command()
    result = request_conversion_intent(candidate, command)
    payload = {"candidate_id": candidate.candidate_id, "target": command.target.value}

    first = repository.record_conversion_intent(
        result,
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    replayed = repository.record_conversion_intent(
        result,
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    conflict = repository.record_conversion_intent(
        result,
        idempotency_key=command.idempotency_key,
        payload={"candidate_id": candidate.candidate_id, "target": "manage_review"},
    )

    assert first.decision is ConversionPersistenceDecision.ACCEPTED
    assert replayed.decision is ConversionPersistenceDecision.REPLAYED
    assert conflict.decision is ConversionPersistenceDecision.CONFLICT
    assert first.record is not None
    assert first.record.candidate.lifecycle_status is IdeaLifecycleStatus.CONVERTED_TO_REPORT
    assert (
        first.record.lifecycle_history[-1].target_status is IdeaLifecycleStatus.CONVERTED_TO_REPORT
    )
    assert first.record.conversion_intents[-1].intent.conversion_intent_id == (
        "conversion-report_evidence-001"
    )
    assert first.record.conversion_intents[-1].idempotency_key == command.idempotency_key
    assert first.record.audit_events[-1].event_type == "idea.conversion.intent_requested"


def test_conversion_intent_persistence_rejects_mismatched_idempotency_key() -> None:
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:approved-high-cash:mismatch",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    command = conversion_intent_command()
    result = request_conversion_intent(candidate, command)

    with pytest.raises(
        ValueError,
        match="conversion intent idempotency key must match repository idempotency key",
    ):
        repository.record_conversion_intent(
            result,
            idempotency_key="conversion:intent:mismatched-ledger-key",
            payload={"candidate_id": candidate.candidate_id, "target": command.target.value},
        )

    snapshot = repository.snapshot()
    assert "conversion:intent:mismatched-ledger-key" not in snapshot.idempotency_records
    assert repository.conversion_intent_by_id(command.conversion_intent_id) is None


def test_conversion_intent_persistence_returns_not_found_without_candidate_record() -> None:
    candidate, _ = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    command = conversion_intent_command()
    result = request_conversion_intent(candidate, command)

    missing = repository.record_conversion_intent(
        result,
        idempotency_key=command.idempotency_key,
        payload={"candidate_id": candidate.candidate_id, "target": command.target.value},
    )

    assert missing.decision is ConversionPersistenceDecision.NOT_FOUND
    assert missing.record is None


def test_conversion_outcome_persistence_records_source_reported_result_and_snapshot_lookup() -> (
    None
):
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:conversion-outcome:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    command = conversion_intent_command()
    intent_result = request_conversion_intent(candidate, command)
    repository.record_conversion_intent(
        intent_result,
        idempotency_key=command.idempotency_key,
        payload={"candidate_id": candidate.candidate_id, "target": command.target.value},
    )
    recovered = InMemoryIdeaRepository(repository.snapshot())
    conversion_intent = recovered.conversion_intent_by_id(command.conversion_intent_id)
    assert conversion_intent is not None
    outcome_result = record_conversion_outcome(
        conversion_intent,
        ConversionOutcomeCommand(
            conversion_outcome_id="conversion-report-outcome-001",
            status=ConversionOutcomeStatus.ACCEPTED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=1,
            downstream_reference="report-evidence-pack-001",
            recorded_at_utc=datetime(2026, 6, 21, 10, 20, tzinfo=UTC),
            actor_subject="lotus-report-worker",
        ),
    )

    first = recovered.record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion-outcome-report-001",
        payload={"conversion_outcome_id": "conversion-report-outcome-001"},
    )
    replayed = recovered.record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion-outcome-report-001",
        payload={"conversion_outcome_id": "conversion-report-outcome-001"},
    )

    assert first.decision is ConversionPersistenceDecision.ACCEPTED
    assert replayed.decision is ConversionPersistenceDecision.REPLAYED
    assert first.record is not None
    assert first.record.conversion_outcomes[-1].outcome.downstream_reference == (
        "report-evidence-pack-001"
    )
    assert first.record.audit_events[-1].event_type == "idea.conversion.outcome_recorded"
    assert first.record.audit_events[-1].actor_subject == "lotus-report-worker"


def test_conversion_intent_lookup_handles_stale_snapshot_index() -> None:
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:stale-conversion-index:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    no_record_index = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={"missing-intent": "missing-candidate"},
        )
    )
    no_matching_intent = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={candidate.candidate_id: persisted.record},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={"missing-intent": candidate.candidate_id},
        )
    )

    assert no_record_index.conversion_intent_by_id("missing-intent") is None
    assert no_matching_intent.conversion_intent_by_id("missing-intent") is None


def test_conversion_outcome_persistence_handles_conflict_and_missing_intent_mapping() -> None:
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:conversion-outcome-conflict:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    command = conversion_intent_command()
    intent_result = request_conversion_intent(candidate, command)
    repository.record_conversion_intent(
        intent_result,
        idempotency_key=command.idempotency_key,
        payload={"candidate_id": candidate.candidate_id, "target": command.target.value},
    )
    outcome_result = record_conversion_outcome(
        intent_result.conversion_intent,
        ConversionOutcomeCommand(
            conversion_outcome_id="conversion-report-outcome-conflict-001",
            status=ConversionOutcomeStatus.ACCEPTED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=1,
            downstream_reference="report-evidence-pack-001",
            recorded_at_utc=datetime(2026, 6, 21, 10, 20, tzinfo=UTC),
            actor_subject="lotus-report-worker",
        ),
    )

    accepted = repository.record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion-outcome-conflict-001",
        payload={"conversion_outcome_id": "conversion-report-outcome-conflict-001"},
    )
    conflict = repository.record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion-outcome-conflict-001",
        payload={"conversion_outcome_id": "changed-outcome-id"},
    )
    no_mapping = InMemoryIdeaRepository().record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion-outcome-missing-mapping-001",
        payload={"conversion_outcome_id": "conversion-report-outcome-conflict-001"},
    )
    stale_mapping = InMemoryIdeaRepository(
        IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
            conversion_intent_candidates={command.conversion_intent_id: "missing-candidate"},
        )
    ).record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion-outcome-stale-mapping-001",
        payload={"conversion_outcome_id": "conversion-report-outcome-conflict-001"},
    )

    assert accepted.decision is ConversionPersistenceDecision.ACCEPTED
    assert conflict.decision is ConversionPersistenceDecision.CONFLICT
    assert no_mapping.decision is ConversionPersistenceDecision.NOT_FOUND
    assert stale_mapping.decision is ConversionPersistenceDecision.NOT_FOUND


def test_report_evidence_pack_persistence_records_idempotent_request() -> None:
    candidate, refs = approved_high_cash_candidate()
    repository = InMemoryIdeaRepository()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:report-evidence-pack:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    conversion_command = conversion_intent_command()
    conversion_result = request_conversion_intent(candidate, conversion_command)
    repository.record_conversion_intent(
        conversion_result,
        idempotency_key=conversion_command.idempotency_key,
        payload={"candidate_id": candidate.candidate_id, "target": conversion_command.target.value},
    )
    recovered = InMemoryIdeaRepository(repository.snapshot())
    conversion_intent = recovered.conversion_intent_by_id(conversion_command.conversion_intent_id)
    record = recovered.candidate_record_for_conversion_intent(
        conversion_command.conversion_intent_id
    )
    assert conversion_intent is not None
    assert record is not None
    pack_command = report_evidence_pack_command()
    pack_result = request_report_evidence_pack(
        record.candidate,
        conversion_intent,
        pack_command,
    )
    payload = {
        "conversion_intent_id": conversion_command.conversion_intent_id,
        "report_evidence_pack_id": pack_command.report_evidence_pack_id,
    }

    first = recovered.record_report_evidence_pack(
        pack_result,
        idempotency_key=pack_command.idempotency_key,
        payload=payload,
    )
    replayed = recovered.record_report_evidence_pack(
        pack_result,
        idempotency_key=pack_command.idempotency_key,
        payload=payload,
    )
    conflict = recovered.record_report_evidence_pack(
        pack_result,
        idempotency_key=pack_command.idempotency_key,
        payload={
            "conversion_intent_id": conversion_command.conversion_intent_id,
            "report_evidence_pack_id": "changed-report-evidence-pack",
        },
    )

    assert first.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert replayed.decision is EvidencePackPersistenceDecision.REPLAYED
    assert conflict.decision is EvidencePackPersistenceDecision.CONFLICT
    assert first.record is not None
    assert first.record.report_evidence_packs[-1].report_evidence_pack_id == (
        "report-evidence-pack-001"
    )
    assert first.record.audit_events[-1].event_type == "idea.report_evidence_pack.requested"


def test_report_evidence_pack_persistence_handles_missing_candidate_record() -> None:
    candidate, _ = approved_high_cash_candidate()
    pack_command = report_evidence_pack_command()
    conversion_command = conversion_intent_command()
    conversion_result = request_conversion_intent(candidate, conversion_command)
    pack_result = request_report_evidence_pack(
        conversion_result.candidate,
        conversion_result.conversion_intent,
        pack_command,
    )

    missing = InMemoryIdeaRepository().record_report_evidence_pack(
        pack_result,
        idempotency_key=pack_command.idempotency_key,
        payload={"report_evidence_pack_id": pack_command.report_evidence_pack_id},
    )

    assert missing.decision is EvidencePackPersistenceDecision.NOT_FOUND
    assert missing.record is None
