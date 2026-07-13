from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from psycopg.types.json import Jsonb

from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIExplanationLineagePersistenceDecision,
    AIExplanationResult,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionTarget,
    DownstreamSubmissionPosture,
    EvidenceFreshness,
    EvidenceReplayStatus,
    FeedbackCommand,
    FeedbackOutcome,
    HighCashSignalInput,
    HighCashSignalPolicy,
    IdeaCandidate,
    IdeaLifecycleStatus,
    OutboxDeliveryDecision,
    OutboxEventStatus,
    ReasonCode,
    ReportEvidencePackCommand,
    ReportEvidencePackPurpose,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    build_ai_explanation_request,
    deterministic_ai_fallback,
    evaluate_high_cash_signal,
    record_conversion_outcome,
    record_feedback,
    request_conversion_intent,
    request_report_evidence_pack,
    apply_review_action,
)
from app.domain.persistence import (
    CandidatePersistenceDecision,
    ConversionPersistenceDecision,
    EvidencePackPersistenceDecision,
    IdeaRepositorySnapshot,
    LifecyclePersistenceDecision,
    ReviewPersistenceDecision,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.data_lifecycle.postgres_policy import DataLifecycleWriteBlockedError
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim
from app.infrastructure.postgres_mutation_metadata import idempotency_created_at
from app.infrastructure.postgres_codecs import (
    decode_datetime,
    read_json_object,
    read_row_value,
)
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.postgres_repository_query_assertions import assert_no_whole_store_snapshot


AS_OF_DATE = datetime(2026, 6, 21, 10, 0, tzinfo=UTC).date()
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_postgres_repository_rejects_unscoped_durable_candidate_atomically() -> None:
    connection = FakePostgresConnection()
    candidate = high_cash_candidate()

    with pytest.raises(DataLifecycleWriteBlockedError) as exc_info:
        PostgresIdeaRepository(connection).persist_candidate(
            candidate,
            idempotency_key="candidate:missing-tenant-scope",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )

    assert exc_info.value.blocker == "tenant_scope_missing"
    assert connection.rows["idea_candidate_record"] == []
    assert connection.rows["idea_data_lifecycle_control"] == []


def test_postgres_repository_persists_replays_and_hydrates_candidate_state() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())

    accepted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    replayed = PostgresIdeaRepository(connection).persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:001",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    snapshot = PostgresIdeaRepository(connection).snapshot()

    assert accepted.decision is CandidatePersistenceDecision.ACCEPTED
    assert replayed.decision is CandidatePersistenceDecision.REPLAYED
    assert snapshot.candidate_records[candidate.candidate_id] == accepted.record
    assert (
        snapshot.candidate_records[candidate.candidate_id].candidate.access_scope == access_scope()
    )
    assert connection.rows["idea_candidate_record"][0]["candidate_json"]["access_scope"] == {
        "tenant_id": "tenant-001",
        "book_id": "book-001",
        "portfolio_id": "portfolio-001",
        "client_id": "client-001",
    }
    assert connection.rows["idea_outbox_event"][0]["event_type"] == ("idea.candidate.persisted.v1")
    assert connection.rows["idea_outbox_event"][0]["status"] == OutboxEventStatus.PENDING.value
    assert (
        snapshot.idempotency_candidates["signal-ingestion:high-cash:001"] == candidate.candidate_id
    )
    assert tuple(snapshot.outbox_events.values())[0].event_type == "idea.candidate.persisted.v1"
    assert connection.commits == 2


def test_postgres_repository_rejects_uncontracted_outbox_rows_on_load() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:bad-outbox-row",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    connection.rows["idea_outbox_event"][0]["event_type"] = "idea.uncontracted.event.v1"

    with pytest.raises(ValueError, match="unsupported outbox event_type"):
        PostgresIdeaRepository(connection).snapshot()

    connection.rows["idea_outbox_event"][0]["event_type"] = "idea.candidate.persisted.v1"
    connection.rows["idea_outbox_event"][0]["schema_version"] = "v2"

    with pytest.raises(ValueError, match="unsupported outbox schema_version"):
        PostgresIdeaRepository(connection).snapshot()


def test_postgres_repository_round_trips_mutating_workflow_details() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    review_ready = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_review_ready",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    approved = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_approved",
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )

    repository.persist_candidate(
        review_ready,
        idempotency_key="candidate:review-ready",
        payload={"candidateId": review_ready.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    repository.persist_candidate(
        approved,
        idempotency_key="candidate:approved",
        payload={"candidateId": approved.candidate_id, "state": "approved"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    lifecycle = repository.record_lifecycle_transition(
        review_ready.candidate_id,
        IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
        idempotency_key="lifecycle:reviewed",
        payload={"candidateId": review_ready.candidate_id, "target": "reviewed_by_advisor"},
        actor_subject="advisor-001",
        occurred_at_utc=EVALUATED_AT + timedelta(minutes=1),
        transition_id="transition-review-001",
        reason_codes=("review_required",),
    )
    assert lifecycle.record is not None

    review_result = apply_review_action(
        lifecycle.record.candidate,
        review_command(),
    )
    review = repository.record_review_action(
        review_result,
        idempotency_key="review:approve",
        payload={"reviewId": review_result.decision.review_id},
    )
    assert review.record is not None
    feedback_result = record_feedback(
        review.record.candidate,
        feedback_command(),
    )
    feedback = repository.record_feedback_event(
        feedback_result,
        idempotency_key="feedback:useful",
        payload={"feedbackId": feedback_result.feedback_event.feedback.feedback_id},
    )

    conversion_result = request_conversion_intent(
        approved,
        conversion_command(),
    )
    conversion = repository.record_conversion_intent(
        conversion_result,
        idempotency_key="conversion:intent",
        payload={
            "conversionIntentId": conversion_result.conversion_intent.intent.conversion_intent_id
        },
    )
    assert conversion.record is not None
    outcome_result = record_conversion_outcome(
        conversion_result.conversion_intent,
        conversion_outcome_command(),
    )
    outcome = repository.record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion:outcome",
        payload={
            "conversionOutcomeId": outcome_result.conversion_outcome.outcome.conversion_outcome_id
        },
    )
    pack_result = request_report_evidence_pack(
        conversion.record.candidate,
        conversion_result.conversion_intent,
        report_pack_command(),
    )
    pack = repository.record_report_evidence_pack(
        pack_result,
        idempotency_key="report:evidence-pack",
        payload={"reportEvidencePackId": pack_result.evidence_pack.report_evidence_pack_id},
    )
    replay = repository.replay_evidence(
        review_ready.candidate_id,
        current_source_refs=review_ready.evidence_packet.source_refs,
        evaluated_at_utc=EVALUATED_AT + timedelta(minutes=7),
    )
    review_precheck = repository.precheck_review_mutation(
        idempotency_key="review:approve",
        payload={"reviewId": review_result.decision.review_id},
        identity=review_result.decision.mutation_identity,
    )
    conversion_precheck = repository.precheck_conversion_mutation(
        idempotency_key="conversion:intent",
        payload={
            "conversionIntentId": conversion_result.conversion_intent.intent.conversion_intent_id
        },
    )
    evidence_pack_precheck = repository.precheck_evidence_pack_mutation(
        idempotency_key="report:evidence-pack",
        payload={"reportEvidencePackId": pack_result.evidence_pack.report_evidence_pack_id},
    )
    loaded_intent = repository.conversion_intent_by_id("conversion-report-001")
    loaded_conversion_record = repository.candidate_record_for_conversion_intent(
        "conversion-report-001"
    )
    bounded_workflow_sql = tuple(connection.executed_sql)
    _append_orphan_detail_rows(connection)

    recovered = PostgresIdeaRepository(connection).snapshot()
    reviewed_record = recovered.candidate_records[review_ready.candidate_id]
    converted_record = recovered.candidate_records[approved.candidate_id]

    assert lifecycle.decision is LifecyclePersistenceDecision.ACCEPTED
    assert review.decision is ReviewPersistenceDecision.ACCEPTED
    assert feedback.decision is ReviewPersistenceDecision.ACCEPTED
    assert conversion.decision is ConversionPersistenceDecision.ACCEPTED
    assert outcome.decision is ConversionPersistenceDecision.ACCEPTED
    assert pack.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert_no_whole_store_snapshot(bounded_workflow_sql)
    assert replay.status is EvidenceReplayStatus.MATCHED
    assert review_precheck is not None
    assert review_precheck.decision is ReviewPersistenceDecision.REPLAYED
    assert conversion_precheck is not None
    assert conversion_precheck.decision is ConversionPersistenceDecision.REPLAYED
    assert evidence_pack_precheck is not None
    assert evidence_pack_precheck.decision is EvidencePackPersistenceDecision.REPLAYED
    assert loaded_intent == conversion_result.conversion_intent
    assert loaded_conversion_record is not None
    assert loaded_conversion_record.candidate.candidate_id == approved.candidate_id
    assert len(reviewed_record.lifecycle_history) == 2
    assert len(reviewed_record.review_decisions) == 1
    assert len(reviewed_record.feedback_events) == 1
    assert len(converted_record.conversion_intents) == 1
    assert len(converted_record.conversion_outcomes) == 1
    assert len(converted_record.report_evidence_packs) == 1
    assert [event.event_type for event in recovered.outbox_events.values()] == [
        "idea.candidate.persisted.v1",
        "idea.candidate.persisted.v1",
        "idea.lifecycle.transitioned.v1",
        "idea.review.decision_recorded.v1",
        "idea.feedback.recorded.v1",
        "idea.conversion.intent_requested.v1",
        "idea.conversion.outcome_recorded.v1",
        "idea.report_evidence_pack.requested.v1",
    ]
    assert recovered.conversion_intent_candidates["conversion-report-001"] == approved.candidate_id
    assert (
        recovered.report_evidence_pack_candidates["report-evidence-pack-001"]
        == approved.candidate_id
    )

    replacement_connection = FakePostgresConnection()
    PostgresIdeaRepository(replacement_connection).replace_snapshot(recovered)
    replaced = PostgresIdeaRepository(replacement_connection).snapshot()

    assert replacement_connection.commits == 1
    assert replacement_connection.rollbacks == 0
    assert replaced.candidate_records.keys() == recovered.candidate_records.keys()
    assert len(replacement_connection.rows["idea_lifecycle_history"]) == 3
    assert len(replacement_connection.rows["idea_review_decision"]) == 1
    assert len(replacement_connection.rows["idea_feedback_event"]) == 1
    assert len(replacement_connection.rows["idea_conversion_intent"]) == 1
    assert len(replacement_connection.rows["idea_conversion_outcome"]) == 1
    assert len(replacement_connection.rows["idea_report_evidence_pack_request"]) == 1
    assert len(replacement_connection.rows["idea_outbox_event"]) == 8


def test_postgres_repository_rejects_mismatched_conversion_intent_idempotency() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    approved = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_idempotency_mismatch",
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    repository.persist_candidate(
        approved,
        idempotency_key="candidate:approved-idempotency-mismatch",
        payload={"candidateId": approved.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    conversion_result = request_conversion_intent(approved, conversion_command())

    with pytest.raises(
        ValueError,
        match="conversion intent idempotency key must match repository idempotency key",
    ):
        repository.record_conversion_intent(
            conversion_result,
            idempotency_key="conversion:mismatched-ledger-key",
            payload={
                "conversionIntentId": (
                    conversion_result.conversion_intent.intent.conversion_intent_id
                )
            },
        )

    assert connection.rows["idea_conversion_intent"] == []
    assert not any(
        row["idempotency_key"] == "conversion:mismatched-ledger-key"
        for row in connection.rows["idea_idempotency_record"]
    )


def test_postgres_repository_rolls_back_failed_snapshot_replacement() -> None:
    source_connection = FakePostgresConnection()
    source_repository = PostgresIdeaRepository(source_connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    source_repository.persist_candidate(
        candidate,
        idempotency_key="candidate:replace-rollback",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    target_connection = FakePostgresConnection(fail_on_insert="idea_outbox_event")

    with pytest.raises(RuntimeError, match="insert failed for idea_outbox_event"):
        PostgresIdeaRepository(target_connection).replace_snapshot(source_repository.snapshot())

    assert target_connection.commits == 0
    assert target_connection.rollbacks == 1


def test_postgres_repository_row_scoped_mutations_preserve_independent_rows() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    first_candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_row_scoped_first",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    second_candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_row_scoped_second",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        first_candidate,
        idempotency_key="candidate:row-scoped-first",
        payload={"candidateId": first_candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    repository.persist_candidate(
        second_candidate,
        idempotency_key="candidate:row-scoped-second",
        payload={"candidateId": second_candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    first_review = apply_review_action(
        first_candidate,
        review_command(review_id="review-row-scoped-first"),
    )
    second_review = apply_review_action(
        second_candidate,
        review_command(review_id="review-row-scoped-second"),
    )

    repository.record_review_action(
        first_review,
        idempotency_key="review:row-scoped-first",
        payload={"reviewId": first_review.decision.review_id},
    )
    repository.record_review_action(
        second_review,
        idempotency_key="review:row-scoped-second",
        payload={"reviewId": second_review.decision.review_id},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()

    assert connection.deletes == 0
    assert {
        decision.review_id
        for record in recovered.candidate_records.values()
        for decision in record.review_decisions
    } == {"review-row-scoped-first", "review-row-scoped-second"}
    assert len(connection.rows["idea_review_decision"]) == 2


def test_postgres_repository_serializes_same_candidate_mutations_from_fresh_state() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_stale_same_candidate",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:stale-same-candidate",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    first_review = apply_review_action(
        candidate,
        review_command(review_id="review-stale-same-candidate-first"),
    )
    second_review = apply_review_action(
        candidate,
        review_command(review_id="review-stale-same-candidate-second"),
    )

    repository.record_review_action(
        first_review,
        idempotency_key="review:stale-same-candidate-first",
        payload={"reviewId": first_review.decision.review_id},
    )
    repository.record_review_action(
        second_review,
        idempotency_key="review:stale-same-candidate-second",
        payload={"reviewId": second_review.decision.review_id},
    )

    recovered = PostgresIdeaRepository(connection).snapshot()

    assert connection.commits == 3
    assert connection.rollbacks == 0
    assert [
        decision.review_id
        for decision in recovered.candidate_records[candidate.candidate_id].review_decisions
    ] == [
        "review-stale-same-candidate-first",
        "review-stale-same-candidate-second",
    ]
    assert any(
        row["idempotency_key"] == "review:stale-same-candidate-second"
        for row in connection.rows["idea_idempotency_record"]
    )


def test_postgres_repository_reads_exact_idempotency_state_as_replay() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_idempotency_collision_replay",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:idempotency-collision-replay",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    review = apply_review_action(
        candidate,
        review_command(review_id="review-idempotency-collision-replay"),
    )
    first = repository.record_review_action(
        review,
        idempotency_key="review:idempotency-collision-replay",
        payload={"reviewId": review.decision.review_id},
    )
    replayed = repository.record_review_action(
        review,
        idempotency_key="review:idempotency-collision-replay",
        payload={"reviewId": review.decision.review_id},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert connection.rollbacks == 0
    assert connection.commits == 3
    assert [
        decision.review_id
        for decision in recovered.candidate_records[candidate.candidate_id].review_decisions
    ] == ["review-idempotency-collision-replay"]
    assert [
        row["idempotency_key"]
        for row in connection.rows["idea_idempotency_record"]
        if row["idempotency_key"] == "review:idempotency-collision-replay"
    ] == ["review:idempotency-collision-replay"]


def test_postgres_repository_reads_exact_idempotency_state_as_conflict() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_idempotency_collision_conflict",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:idempotency-collision-conflict",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    review = apply_review_action(
        candidate,
        review_command(review_id="review-idempotency-collision-conflict"),
    )
    first = repository.record_review_action(
        review,
        idempotency_key="review:idempotency-collision-conflict",
        payload={"reviewId": review.decision.review_id},
    )
    conflict = repository.record_review_action(
        review,
        idempotency_key="review:idempotency-collision-conflict",
        payload={"reviewId": "different-review-payload"},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()

    assert first.decision is ReviewPersistenceDecision.ACCEPTED
    assert conflict.decision is ReviewPersistenceDecision.CONFLICT
    assert conflict.record is not None
    assert conflict.record.candidate.candidate_id == candidate.candidate_id
    assert connection.rollbacks == 0
    assert connection.commits == 3
    assert [
        decision.review_id
        for decision in recovered.candidate_records[candidate.candidate_id].review_decisions
    ] == ["review-idempotency-collision-conflict"]
    assert [
        row["idempotency_key"]
        for row in connection.rows["idea_idempotency_record"]
        if row["idempotency_key"] == "review:idempotency-collision-conflict"
    ] == ["review:idempotency-collision-conflict"]


def test_postgres_candidate_updates_use_optimistic_snapshot_guard() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_optimistic_guard",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:optimistic-guard",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    review = apply_review_action(
        candidate,
        review_command(review_id="review-optimistic-guard"),
    )
    repository.record_review_action(
        review,
        idempotency_key="review:optimistic-guard",
        payload={"reviewId": review.decision.review_id},
    )

    update_sql = next(
        statement
        for statement in connection.executed_sql
        if statement.startswith("update idea_candidate_record")
    )
    assert "where candidate_id = %s and updated_at_utc = %s" in update_sql
    assert "returning candidate_id" in update_sql


def test_postgres_repository_persists_outbox_delivery_status_updates() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:outbox-delivery",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    event = next(iter(PostgresIdeaRepository(connection).snapshot().outbox_events.values()))

    first_claim = repository.claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        lease_owner="worker-1",
        lease_attempt_id="attempt-1",
        claimed_at_utc=EVALUATED_AT,
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
    )
    second_claim = repository.claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        lease_owner="worker-2",
        lease_attempt_id="attempt-2",
        claimed_at_utc=EVALUATED_AT,
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
    )
    wrong_owner = repository.mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-2",
        lease_attempt_id="attempt-2",
        published_at_utc=EVALUATED_AT + timedelta(minutes=1),
    )
    failed = repository.mark_outbox_event_failed(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-1",
        failure_reason="publisher_unavailable",
        failed_at_utc=EVALUATED_AT,
        max_retry_count=2,
    )
    not_due_retryable = PostgresIdeaRepository(connection).outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        evaluated_at_utc=EVALUATED_AT + timedelta(seconds=59),
    )
    due_retryable = PostgresIdeaRepository(connection).outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        evaluated_at_utc=EVALUATED_AT + timedelta(seconds=60),
    )
    retry_claim = PostgresIdeaRepository(connection).claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        lease_owner="worker-1",
        lease_attempt_id="attempt-3",
        claimed_at_utc=EVALUATED_AT + timedelta(seconds=60),
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=6),
    )
    published = PostgresIdeaRepository(connection).mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-3",
        published_at_utc=EVALUATED_AT + timedelta(minutes=1),
    )
    already_published = PostgresIdeaRepository(connection).mark_outbox_event_published(
        event.event_id,
        lease_owner="worker-1",
        lease_attempt_id="attempt-3",
        published_at_utc=EVALUATED_AT + timedelta(minutes=2),
    )
    missing_failure = PostgresIdeaRepository(connection).mark_outbox_event_failed(
        "missing-event",
        lease_owner="worker-1",
        lease_attempt_id="attempt-missing",
        failure_reason="publisher_unavailable",
        max_retry_count=2,
    )
    reloaded = PostgresIdeaRepository(connection).snapshot().outbox_events[event.event_id]

    assert first_claim[0].status is OutboxEventStatus.LEASED
    assert first_claim[0].lease_owner == "worker-1"
    assert second_claim == ()
    assert wrong_owner.decision is OutboxDeliveryDecision.LEASE_LOST
    assert failed.decision is OutboxDeliveryDecision.ACCEPTED
    assert failed.event is not None
    assert failed.event.status is OutboxEventStatus.FAILED
    assert failed.event.first_failed_at_utc == EVALUATED_AT
    assert failed.event.last_failed_at_utc == EVALUATED_AT
    assert failed.event.next_attempt_at_utc == EVALUATED_AT + timedelta(seconds=60)
    assert not_due_retryable == ()
    assert due_retryable == (failed.event,)
    assert retry_claim[0].status is OutboxEventStatus.LEASED
    assert retry_claim[0].first_failed_at_utc == EVALUATED_AT
    assert retry_claim[0].last_failed_at_utc == EVALUATED_AT
    assert retry_claim[0].next_attempt_at_utc is None
    assert published.decision is OutboxDeliveryDecision.ACCEPTED
    assert already_published.decision is OutboxDeliveryDecision.ALREADY_PUBLISHED
    assert missing_failure.decision is OutboxDeliveryDecision.NOT_FOUND
    assert reloaded.status is OutboxEventStatus.PUBLISHED
    assert reloaded.published_at_utc == EVALUATED_AT + timedelta(minutes=1)
    assert reloaded.failure_reason == "publisher_unavailable"
    assert reloaded.first_failed_at_utc == EVALUATED_AT
    assert reloaded.last_failed_at_utc == EVALUATED_AT
    assert reloaded.next_attempt_at_utc is None


def test_postgres_repository_rejects_sensitive_outbox_failure_reason() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:outbox-sensitive-failure",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    event = next(iter(repository.snapshot().outbox_events.values()))
    repository.claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        lease_owner="worker-1",
        lease_attempt_id="attempt-sensitive",
        claimed_at_utc=EVALUATED_AT,
        lease_expires_at_utc=EVALUATED_AT + timedelta(minutes=5),
    )

    with pytest.raises(ValueError, match="sensitive keys"):
        repository.mark_outbox_event_failed(
            event.event_id,
            lease_owner="worker-1",
            lease_attempt_id="attempt-sensitive",
            failure_reason="portfolio_id leaked in downstream error",
            max_retry_count=2,
        )

    reloaded = repository.snapshot().outbox_events[event.event_id]
    assert reloaded.status is OutboxEventStatus.LEASED
    assert reloaded.failure_reason is None


def test_postgres_repository_round_trips_downstream_submission_records() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = build_downstream_submission_claim(
        idempotency_key="downstream-submit-postgres-001",
        request_fingerprint="sha256:downstream-submit-postgres",
        resource_id="conversion-postgres-001",
        correlation_id="corr-postgres",
        trace_id="trace-postgres",
        submitted_at_utc=EVALUATED_AT,
    )

    repository.claim_downstream_submission(claim)
    finalized = repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=EVALUATED_AT,
    )
    assert finalized.record is not None
    record = finalized.record
    reloaded = PostgresIdeaRepository(connection).downstream_submission_by_idempotency_key(
        "downstream-submit-postgres-001"
    )
    missing = PostgresIdeaRepository(connection).downstream_submission_by_idempotency_key(
        "missing-submission"
    )

    assert reloaded == record
    assert missing is None


def test_postgres_repository_round_trips_ai_explanation_lineage() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:ai-lineage",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    explanation_result = ai_explanation_result_for_candidate(candidate)

    accepted = repository.record_ai_explanation_lineage(explanation_result)
    assert_no_whole_store_snapshot(tuple(connection.executed_sql))
    assert any("ai-lineage-identity-candidates" in sql for sql in connection.executed_sql)
    ai_identity_query = next(
        sql for sql in connection.executed_sql if "ai-lineage-identity-candidates" in sql
    )
    assert ai_identity_query.count("%s::text") == 4
    recovered = PostgresIdeaRepository(connection).snapshot()
    replayed = PostgresIdeaRepository(connection).record_ai_explanation_lineage(explanation_result)

    assert accepted.decision is AIExplanationLineagePersistenceDecision.ACCEPTED
    assert replayed.decision is AIExplanationLineagePersistenceDecision.REPLAYED
    assert accepted.lineage_record is not None
    assert recovered.ai_explanation_lineage_candidates == {
        "ai-lineage-request-001": candidate.candidate_id,
    }
    recovered_record = recovered.candidate_records[candidate.candidate_id]
    assert recovered_record.ai_explanation_lineage_records == (accepted.lineage_record,)
    assert (
        connection.rows["idea_ai_explanation_lineage"][0]["lineage_json"][
            "grants_downstream_authority"
        ]
        is False
    )
    assert "portfolio_id" not in connection.rows["idea_ai_explanation_lineage"][0]["lineage_json"]
    lineage_row = connection.rows["idea_ai_explanation_lineage"][0]
    assert lineage_row["output_integrity_version"] == "lotus-idea.ai-output-integrity.v1"
    assert lineage_row["output_content_digest"] == explanation_result.output_integrity.digest
    assert (
        lineage_row["lineage_json"]["output_content_digest"]
        == (lineage_row["output_content_digest"])
    )
    assert lineage_row["execution_provenance_posture"] == "not_applicable_fallback"
    assert lineage_row["lotus_ai_run_id"] is None
    assert lineage_row["lotus_ai_replay_nonce"] is None
    assert lineage_row["lotus_ai_attestation_key_id"] is None
    assert (
        lineage_row["lineage_json"]["execution_provenance_posture"]
        == (lineage_row["execution_provenance_posture"])
    )


def test_postgres_repository_applies_idempotency_to_ai_lineage_requests() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:ai-lineage-idempotency",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    explanation_result = ai_explanation_result_for_candidate(candidate)
    idempotency_key = "ai-lineage-request:idempotency-001"
    idempotency_payload = {
        "candidateId": candidate.candidate_id,
        "requestId": explanation_result.request.request_id,
    }

    accepted = repository.record_ai_explanation_lineage_request(
        explanation_result,
        idempotency_key=idempotency_key,
        payload=idempotency_payload,
    )
    replayed = PostgresIdeaRepository(connection).record_ai_explanation_lineage_request(
        explanation_result,
        idempotency_key=idempotency_key,
        payload=idempotency_payload,
    )
    conflict = PostgresIdeaRepository(connection).record_ai_explanation_lineage_request(
        explanation_result,
        idempotency_key=idempotency_key,
        payload={**idempotency_payload, "requestId": "changed-ai-lineage-request"},
    )

    assert accepted.decision is AIExplanationLineagePersistenceDecision.ACCEPTED
    assert replayed.decision is AIExplanationLineagePersistenceDecision.REPLAYED
    assert conflict.decision is AIExplanationLineagePersistenceDecision.CONFLICT
    assert conflict.lineage_record is None
    assert len(connection.rows["idea_ai_explanation_lineage"]) == 1
    assert [
        row["idempotency_key"]
        for row in connection.rows["idea_idempotency_record"]
        if row["idempotency_key"] == idempotency_key
    ] == [idempotency_key]


def test_postgres_repository_ignores_orphan_detail_rows_during_hydration() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:orphan-guard",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    repository.record_lifecycle_transition(
        candidate.candidate_id,
        IdeaLifecycleStatus.ENRICHED,
        idempotency_key="lifecycle:enriched",
        payload={"candidateId": candidate.candidate_id, "target": "enriched"},
        actor_subject="advisor-001",
        occurred_at_utc=EVALUATED_AT + timedelta(minutes=1),
    )

    for table_name in (
        "idea_lifecycle_history",
        "idea_review_decision",
        "idea_feedback_event",
        "idea_conversion_intent",
        "idea_report_evidence_pack_request",
    ):
        if connection.rows[table_name]:
            orphan = dict(connection.rows[table_name][0])
            orphan["candidate_id"] = "missing-candidate"
            connection.rows[table_name].append(orphan)
    if connection.rows["idea_audit_event"]:
        orphan_audit = dict(connection.rows["idea_audit_event"][0])
        orphan_audit["candidate_id"] = None
        connection.rows["idea_audit_event"].append(orphan_audit)
    connection.rows["idea_conversion_outcome"].append(
        {
            "conversion_outcome_id": "orphan-outcome",
            "conversion_intent_id": "missing-intent",
            "source_system": SourceSystem.LOTUS_REPORT.value,
            "status": ConversionOutcomeStatus.ACCEPTED.value,
            "outcome_json": {
                "outcome": {
                    "conversion_outcome_id": "orphan-outcome",
                    "conversion_intent_id": "missing-intent",
                    "status": ConversionOutcomeStatus.ACCEPTED.value,
                    "downstream_reference": None,
                    "recorded_at_utc": EVALUATED_AT.isoformat(),
                },
                "conversion_intent_id": "missing-intent",
                "target": ConversionTarget.REPORT_EVIDENCE.value,
                "source_system": SourceSystem.LOTUS_REPORT.value,
                "boundary": "downstream_realization_required",
            },
            "recorded_at_utc": EVALUATED_AT,
        }
    )

    recovered = PostgresIdeaRepository(connection).snapshot()

    assert tuple(recovered.candidate_records) == (candidate.candidate_id,)
    assert len(recovered.candidate_records[candidate.candidate_id].lifecycle_history) == 1


def test_postgres_repository_row_and_json_guards() -> None:
    assert read_json_object({"payload": Jsonb({"ok": True})}, "payload") == {"ok": True}
    assert decode_datetime(EVALUATED_AT) is EVALUATED_AT
    assert isinstance(idempotency_created_at(None, IdeaRepositorySnapshot({}, {}, {})), datetime)
    with pytest.raises(TypeError, match="mapping rows"):
        read_row_value(("not", "mapping"), "payload")
    with pytest.raises(TypeError, match="must be a JSON object"):
        read_json_object({"payload": "not-json"}, "payload")


def test_postgres_repository_rolls_back_when_flush_fails() -> None:
    connection = FakePostgresConnection(fail_on_insert="idea_candidate_record")
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())

    with pytest.raises(RuntimeError, match="insert failed"):
        repository.persist_candidate(
            candidate,
            idempotency_key="signal-ingestion:high-cash:001",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1


def high_cash_candidate(candidate_scope: ReviewAccessScope | None = None) -> IdeaCandidate:
    refs = source_refs()
    result = evaluate_high_cash_signal(
        HighCashSignalInput(
            as_of_date=AS_OF_DATE,
            source_reported_cash_weight=Decimal("0.18"),
            portfolio_state_ref=refs[0],
            holdings_ref=refs[1],
            cash_movement_ref=refs[2],
            cashflow_projection_ref=refs[3],
            evaluated_at_utc=EVALUATED_AT,
            access_scope=candidate_scope,
        ),
        HighCashSignalPolicy(
            policy_version="idle-liquidity-v1",
            cash_weight_threshold=Decimal("0.12"),
            candidate_score=Decimal("82"),
        ),
    )
    assert result.candidate is not None
    return result.candidate


def source_refs() -> tuple[SourceRef, ...]:
    return (
        source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        source_ref("lotus-core:HoldingsAsOf:v1"),
        source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )


def source_ref(product_id: str) -> SourceRef:
    routes = {
        "lotus-core:PortfolioStateSnapshot:v1": "/integration/portfolios/{portfolio_id}/core-snapshot",
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/cash-balances",
        "lotus-core:PortfolioCashMovementSummary:v1": "/portfolios/{portfolio_id}/cash-movement-summary",
        "lotus-core:PortfolioCashflowProjection:v1": "/portfolios/{portfolio_id}/cashflow-projection",
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=routes[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def actor() -> ReviewActorContext:
    return ReviewActorContext(
        actor_subject="advisor-001",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({"tenant-001"}),
        book_ids=frozenset({"book-001"}),
        portfolio_ids=frozenset({"portfolio-001"}),
        client_ids=frozenset({"client-001"}),
    )


def access_scope() -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="tenant-001",
        book_id="book-001",
        portfolio_id="portfolio-001",
        client_id="client-001",
    )


def review_command(review_id: str = "review-approve-001") -> ReviewDecisionCommand:
    return ReviewDecisionCommand(
        review_id=review_id,
        action=ReviewAction.APPROVE_FOR_CONVERSION,
        actor=actor(),
        access_scope=access_scope(),
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        decided_at_utc=EVALUATED_AT + timedelta(minutes=2),
    )


def feedback_command() -> FeedbackCommand:
    return FeedbackCommand(
        feedback_id="feedback-useful-001",
        actor=actor(),
        access_scope=access_scope(),
        outcome=FeedbackOutcome.USEFUL,
        reason_codes=(ReasonCode.FEEDBACK_RECORDED,),
        recorded_at_utc=EVALUATED_AT + timedelta(minutes=3),
    )


def conversion_command() -> ConversionIntentCommand:
    return ConversionIntentCommand(
        conversion_intent_id="conversion-report-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        actor_subject="advisor-001",
        idempotency_key="conversion:intent",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=EVALUATED_AT + timedelta(minutes=4),
    )


def conversion_outcome_command() -> ConversionOutcomeCommand:
    return ConversionOutcomeCommand(
        conversion_outcome_id="conversion-outcome-001",
        status=ConversionOutcomeStatus.ACCEPTED,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=1,
        recorded_at_utc=EVALUATED_AT + timedelta(minutes=5),
        downstream_reference="report-evidence-pack-001",
        actor_subject="lotus-report",
    )


def report_pack_command() -> ReportEvidencePackCommand:
    return ReportEvidencePackCommand(
        report_evidence_pack_id="report-evidence-pack-001",
        purpose=ReportEvidencePackPurpose.CLIENT_REVIEW_REPORT_SECTION,
        actor_subject="advisor-001",
        idempotency_key="report:evidence-pack",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=EVALUATED_AT + timedelta(minutes=6),
        retention_policy_ref="lotus-report:idea-evidence-retention:v1",
    )


def ai_explanation_result_for_candidate(candidate: IdeaCandidate) -> AIExplanationResult:
    request = build_ai_explanation_request(
        candidate,
        AIExplanationCommand(
            request_id="ai-lineage-request-001",
            actor_subject="advisor-001",
            workflow_pack=AIWorkflowPackRef(
                workflow_pack_id="lotus-ai:idea-explanation:v1",
                workflow_pack_version="v1",
                purpose=AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
                evaluation_ref="lotus-ai:governed-verifier:v1",
            ),
            approved_metadata={"channel": "advisor-workbench"},
            requested_at_utc=EVALUATED_AT + timedelta(minutes=10),
        ),
    )
    return deterministic_ai_fallback(
        request,
        fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        occurred_at_utc=EVALUATED_AT + timedelta(minutes=10),
    )


def _append_orphan_detail_rows(connection: FakePostgresConnection) -> None:
    for table_name in (
        "idea_lifecycle_history",
        "idea_review_decision",
        "idea_feedback_event",
        "idea_conversion_intent",
        "idea_report_evidence_pack_request",
    ):
        orphan = dict(connection.rows[table_name][0])
        orphan["candidate_id"] = "missing-candidate"
        connection.rows[table_name].append(orphan)
    orphan_audit = dict(connection.rows["idea_audit_event"][0])
    orphan_audit["candidate_id"] = None
    connection.rows["idea_audit_event"].append(orphan_audit)
    orphan_outcome = dict(connection.rows["idea_conversion_outcome"][0])
    orphan_outcome["conversion_intent_id"] = "missing-intent"
    connection.rows["idea_conversion_outcome"].append(orphan_outcome)
