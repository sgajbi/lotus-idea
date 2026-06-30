from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Sequence

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
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
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
from app.infrastructure.postgres_repository import (
    PostgresIdeaRepository,
    _idempotency_created_at,
)
from app.infrastructure.postgres_codecs import (
    decode_datetime,
    read_json_object,
    read_row_value,
)
from tests.unit.postgres_outbox_fake_helpers import (
    claim_outbox_event_rows,
    fail_outbox_event_row,
    outbox_delivery_ready_rows,
    outbox_readiness_summary_row,
    publish_outbox_event_row,
)
from tests.unit.postgres_repository_lookup_fake_helpers import (
    candidate_detail_rows,
    downstream_lookup_rows,
)
from tests.unit.postgres_review_queue_fake_helpers import (
    review_queue_count_rows,
    review_queue_page_rows,
)


AS_OF_DATE = datetime(2026, 6, 21, 10, 0, tzinfo=UTC).date()
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class FakePostgresCursor:
    def __init__(self, connection: FakePostgresConnection) -> None:
        self.connection = connection
        self._rows: list[dict[str, Any]] = []

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        normalized = " ".join(query.lower().split())
        self.connection.executed_sql.append(normalized)
        if normalized.startswith("/* lotus-idea review-queue-count */"):
            assert params is not None
            self._rows = review_queue_count_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea review-queue-page */"):
            assert params is not None
            self._rows = review_queue_page_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea outbox-delivery-ready-events */"):
            assert params is not None
            self._rows = outbox_delivery_ready_rows(self.connection, params)
            return
        if normalized.startswith("/* lotus-idea outbox-readiness-summary */"):
            assert params is not None
            self._rows = outbox_readiness_summary_row(self.connection, params)
            return
        if normalized.startswith("/* lotus-idea downstream-realization-readiness-summary */"):
            self._rows = [
                {
                    "conversion_intent_count": len(self.connection.rows["idea_conversion_intent"]),
                    "conversion_outcome_count": len(
                        self.connection.rows["idea_conversion_outcome"]
                    ),
                    "report_evidence_pack_request_count": len(
                        self.connection.rows["idea_report_evidence_pack_request"]
                    ),
                }
            ]
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-summary */"):
            self._rows = runtime_trust_telemetry_summary_rows(self.connection)
            return
        if normalized.startswith(
            "/* lotus-idea runtime-trust-telemetry-source-authority-counts */"
        ):
            self._rows = runtime_trust_telemetry_count_rows(
                self.connection,
                "source_system",
            )
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-freshness-counts */"):
            self._rows = runtime_trust_telemetry_count_rows(self.connection, "freshness")
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-supportability-counts */"):
            self._rows = candidate_json_count_rows(
                self.connection,
                ("evidence_packet", "supportability"),
            )
            return
        if normalized.startswith("/* lotus-idea runtime-trust-telemetry-lifecycle-counts */"):
            self._rows = table_count_rows(
                self.connection, "idea_candidate_record", "lifecycle_status"
            )
            return
        if normalized.startswith("/* lotus-idea candidate-detail"):
            assert params is not None
            self._rows = candidate_detail_rows(self.connection, normalized, params)
            return
        if normalized.startswith("/* lotus-idea downstream-lookup"):
            assert params is not None
            self._rows = downstream_lookup_rows(self.connection, normalized, params)
            return
        if normalized.startswith("with selected"):
            assert params is not None
            self._rows = claim_outbox_event_rows(self.connection, params)
            return
        if normalized.startswith("update idea_candidate_record"):
            assert params is not None
            self._rows = update_candidate_record_row(self.connection, params)
            return
        if normalized.startswith("update idea_outbox_event"):
            assert params is not None
            if "set status = %s, published_at_utc = %s" in normalized:
                self._rows = publish_outbox_event_row(self.connection, params)
            else:
                self._rows = fail_outbox_event_row(self.connection, params)
            return
        if normalized.startswith("select"):
            if (
                "from idea_outbox_event" in normalized
                and "where outbox_event_id = %s" in normalized
            ):
                assert params is not None
                self._rows = [
                    row
                    for row in self.connection.rows["idea_outbox_event"]
                    if row["outbox_event_id"] == params[0]
                ]
                return
            self._rows = list(self.connection.rows[_table_from_select(normalized)])
            return
        if normalized.startswith("delete from"):
            self.connection.deletes += 1
            self.connection.rows[normalized.split()[2]].clear()
            return
        if normalized.startswith("insert into"):
            table_name = normalized.split()[2]
            if table_name == self.connection.fail_on_insert:
                raise RuntimeError(f"insert failed for {table_name}")
            assert params is not None
            self.connection.rows[table_name].append(_row_for_insert(table_name, params))
            return
        raise AssertionError(f"unexpected SQL: {query}")

    def fetchall(self) -> Sequence[dict[str, Any]]:
        return self._rows

    def __enter__(self) -> FakePostgresCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakePostgresConnection:
    def __init__(self, *, fail_on_insert: str | None = None) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {
            "idea_candidate_record": [],
            "idea_idempotency_record": [],
            "idea_lifecycle_history": [],
            "idea_audit_event": [],
            "idea_outbox_event": [],
            "idea_review_decision": [],
            "idea_feedback_event": [],
            "idea_conversion_intent": [],
            "idea_conversion_outcome": [],
            "idea_report_evidence_pack_request": [],
            "idea_downstream_submission": [],
            "idea_ai_explanation_lineage": [],
        }
        self.fail_on_insert = fail_on_insert
        self.commits = 0
        self.rollbacks = 0
        self.deletes = 0
        self.executed_sql: list[str] = []

    def cursor(self) -> FakePostgresCursor:
        return FakePostgresCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


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
        high_cash_candidate(),
        candidate_id="idea_high_cash_review_ready",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    approved = replace(
        high_cash_candidate(),
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


def test_postgres_repository_rolls_back_failed_snapshot_replacement() -> None:
    source_connection = FakePostgresConnection()
    source_repository = PostgresIdeaRepository(source_connection)
    candidate = high_cash_candidate()
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
        high_cash_candidate(),
        candidate_id="idea_high_cash_row_scoped_first",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    second_candidate = replace(
        high_cash_candidate(),
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
    base_snapshot = PostgresIdeaRepository(connection).snapshot()

    class StaleSnapshotRepository(PostgresIdeaRepository):
        def __init__(
            self,
            stale_connection: FakePostgresConnection,
            stale_snapshot: IdeaRepositorySnapshot,
        ) -> None:
            super().__init__(stale_connection)
            self._stale_snapshot = stale_snapshot

        def snapshot(self) -> IdeaRepositorySnapshot:
            return self._stale_snapshot

    first_review = apply_review_action(
        first_candidate,
        review_command(review_id="review-row-scoped-first"),
    )
    second_review = apply_review_action(
        second_candidate,
        review_command(review_id="review-row-scoped-second"),
    )

    StaleSnapshotRepository(connection, base_snapshot).record_review_action(
        first_review,
        idempotency_key="review:row-scoped-first",
        payload={"reviewId": first_review.decision.review_id},
    )
    StaleSnapshotRepository(connection, base_snapshot).record_review_action(
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


def test_postgres_repository_persists_outbox_delivery_status_updates() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
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
        max_retry_count=2,
    )
    retryable = PostgresIdeaRepository(connection).outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
    )
    retry_claim = PostgresIdeaRepository(connection).claim_outbox_events_for_delivery(
        limit=10,
        max_retry_count=2,
        lease_owner="worker-1",
        lease_attempt_id="attempt-3",
        claimed_at_utc=EVALUATED_AT + timedelta(minutes=1),
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
    assert retryable == (failed.event,)
    assert retry_claim[0].status is OutboxEventStatus.LEASED
    assert published.decision is OutboxDeliveryDecision.ACCEPTED
    assert already_published.decision is OutboxDeliveryDecision.ALREADY_PUBLISHED
    assert missing_failure.decision is OutboxDeliveryDecision.NOT_FOUND
    assert reloaded.status is OutboxEventStatus.PUBLISHED
    assert reloaded.published_at_utc == EVALUATED_AT + timedelta(minutes=1)
    assert reloaded.failure_reason is None


def test_postgres_repository_rejects_sensitive_outbox_failure_reason() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
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
    record = DownstreamSubmissionRecord(
        idempotency_key="downstream-submit-postgres-001",
        request_fingerprint="sha256:downstream-submit-postgres",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="conversion-postgres-001",
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        status=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        downstream_failure_reason=None,
        correlation_id="corr-postgres",
        trace_id="trace-postgres",
        submitted_at_utc=EVALUATED_AT,
    )

    repository.record_downstream_submission(record)
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
        high_cash_candidate(),
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


def test_postgres_repository_ignores_orphan_detail_rows_during_hydration() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
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
    assert isinstance(_idempotency_created_at(None, IdeaRepositorySnapshot({}, {}, {})), datetime)
    with pytest.raises(TypeError, match="mapping rows"):
        read_row_value(("not", "mapping"), "payload")
    with pytest.raises(TypeError, match="must be a JSON object"):
        read_json_object({"payload": "not-json"}, "payload")


def test_postgres_repository_rolls_back_when_flush_fails() -> None:
    connection = FakePostgresConnection(fail_on_insert="idea_candidate_record")
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()

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
            approved_metadata={"audience": "internal_advisor_review"},
            requested_at_utc=EVALUATED_AT + timedelta(minutes=10),
        ),
    )
    return deterministic_ai_fallback(
        request,
        fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        occurred_at_utc=EVALUATED_AT + timedelta(minutes=10),
    )


def runtime_trust_telemetry_summary_rows(
    connection: FakePostgresConnection,
) -> list[dict[str, Any]]:
    candidate_rows = connection.rows["idea_candidate_record"]
    source_refs = _runtime_trust_source_refs(connection)
    current_source_refs = [
        source_ref for source_ref in source_refs if source_ref.get("freshness") == "current"
    ]
    generated_at_values = [
        str(source_ref["generated_at_utc"])
        for source_ref in source_refs
        if source_ref.get("generated_at_utc") is not None
    ]
    latest_generated_at = max(generated_at_values, default=None)
    return [
        {
            "candidate_snapshot_count": len(candidate_rows),
            "current_source_ref_count": len(current_source_refs),
            "stale_or_unavailable_source_ref_count": len(source_refs) - len(current_source_refs),
            "source_batch_evidence_available": bool(source_refs),
            "lineage_materialized": bool(candidate_rows)
            and all(_candidate_lineage_materialized(row) for row in candidate_rows),
            "data_quality_status": _runtime_trust_data_quality_status(source_refs),
            "latest_source_generated_at_utc": latest_generated_at,
            "source_as_of_dates": sorted(
                {
                    str(source_ref["as_of_date"])
                    for source_ref in source_refs
                    if source_ref.get("as_of_date")
                }
            ),
            "review_decision_count": len(connection.rows["idea_review_decision"]),
            "feedback_event_count": len(connection.rows["idea_feedback_event"]),
            "conversion_intent_count": len(connection.rows["idea_conversion_intent"]),
            "conversion_outcome_count": len(connection.rows["idea_conversion_outcome"]),
            "report_evidence_pack_count": len(connection.rows["idea_report_evidence_pack_request"]),
        }
    ]


def runtime_trust_telemetry_count_rows(
    connection: FakePostgresConnection,
    source_ref_key: str,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for source_ref in _runtime_trust_source_refs(connection):
        value = source_ref.get(source_ref_key)
        if value is not None:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items())]


def candidate_json_count_rows(
    connection: FakePostgresConnection,
    path: tuple[str, ...],
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in connection.rows["idea_candidate_record"]:
        value: Any = row["candidate_json"]
        for key in path:
            value = value[key]
        counts[str(value)] = counts.get(str(value), 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items())]


def table_count_rows(
    connection: FakePostgresConnection,
    table_name: str,
    column_name: str,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in connection.rows[table_name]:
        value = row.get(column_name)
        if value is not None:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items())]


def _runtime_trust_source_refs(connection: FakePostgresConnection) -> list[dict[str, Any]]:
    source_refs: list[dict[str, Any]] = []
    for row in connection.rows["idea_candidate_record"]:
        candidate_json = row["candidate_json"]
        source_refs.extend(candidate_json["evidence_packet"]["source_refs"])
    return source_refs


def _candidate_lineage_materialized(row: dict[str, Any]) -> bool:
    lineage_ref = row["candidate_json"]["evidence_packet"]["lineage_ref"]
    return bool(lineage_ref.get("lineage_id") and lineage_ref.get("source_refs"))


def _runtime_trust_data_quality_status(source_refs: list[dict[str, Any]]) -> str:
    if not source_refs:
        return "quality_unknown"
    if all(source_ref.get("data_quality_status") == "complete" for source_ref in source_refs):
        return "quality_passed"
    return "quality_warning"


def _table_from_select(query: str) -> str:
    for table_name in (
        "idea_candidate_record",
        "idea_idempotency_record",
        "idea_lifecycle_history",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_review_decision",
        "idea_feedback_event",
        "idea_conversion_intent",
        "idea_conversion_outcome",
        "idea_report_evidence_pack_request",
        "idea_downstream_submission",
        "idea_ai_explanation_lineage",
    ):
        if f" from {table_name}" in query:
            return table_name
    raise AssertionError(f"unknown select table: {query}")


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


def _row_for_insert(table_name: str, params: Sequence[Any]) -> dict[str, Any]:
    values = [_unwrap_jsonb(value) for value in params]
    columns_by_table = {
        "idea_candidate_record": (
            "candidate_id",
            "family",
            "lifecycle_status",
            "review_posture",
            "evidence_packet_id",
            "evidence_hash",
            "candidate_json",
            "persisted_at_utc",
            "updated_at_utc",
        ),
        "idea_idempotency_record": (
            "idempotency_key",
            "operation_name",
            "payload_hash",
            "candidate_id",
            "created_at_utc",
        ),
        "idea_lifecycle_history": (
            "lifecycle_history_id",
            "candidate_id",
            "source_status",
            "target_status",
            "actor_subject",
            "changed_at_utc",
        ),
        "idea_audit_event": (
            "audit_event_id",
            "candidate_id",
            "event_type",
            "actor_subject",
            "outcome",
            "attributes_json",
            "occurred_at_utc",
        ),
        "idea_outbox_event": (
            "outbox_event_id",
            "event_type",
            "aggregate_type",
            "aggregate_id",
            "schema_version",
            "payload_json",
            "status",
            "occurred_at_utc",
            "idempotency_fingerprint",
            "correlation_id",
            "causation_id",
            "published_at_utc",
            "failure_reason",
            "retry_count",
            "lease_owner",
            "lease_attempt_id",
            "lease_expires_at_utc",
        ),
        "idea_review_decision": (
            "review_decision_id",
            "candidate_id",
            "action",
            "actor_subject",
            "decision_json",
            "decided_at_utc",
        ),
        "idea_feedback_event": (
            "feedback_event_id",
            "candidate_id",
            "actor_subject",
            "feedback_json",
            "recorded_at_utc",
        ),
        "idea_conversion_intent": (
            "conversion_intent_id",
            "candidate_id",
            "target",
            "actor_subject",
            "intent_json",
            "requested_at_utc",
        ),
        "idea_conversion_outcome": (
            "conversion_outcome_id",
            "conversion_intent_id",
            "source_system",
            "status",
            "outcome_json",
            "recorded_at_utc",
        ),
        "idea_report_evidence_pack_request": (
            "report_evidence_pack_id",
            "candidate_id",
            "conversion_intent_id",
            "purpose",
            "evidence_hash",
            "evidence_pack_json",
            "requested_at_utc",
        ),
        "idea_downstream_submission": (
            "idempotency_key",
            "request_fingerprint",
            "resource_type",
            "resource_id",
            "target",
            "source_authority",
            "status",
            "downstream_failure_reason",
            "correlation_id",
            "trace_id",
            "submitted_at_utc",
        ),
        "idea_ai_explanation_lineage": (
            "ai_explanation_request_id",
            "candidate_id",
            "evidence_packet_id",
            "evidence_content_hash",
            "workflow_pack_id",
            "workflow_pack_version",
            "purpose",
            "posture",
            "verifier_outcome",
            "fallback_used",
            "fallback_reason",
            "lineage_hash",
            "lineage_json",
            "requested_at_utc",
            "evaluated_at_utc",
        ),
    }
    return dict(zip(columns_by_table[table_name], values, strict=True))


def update_candidate_record_row(
    connection: FakePostgresConnection,
    params: Sequence[Any],
) -> list[dict[str, Any]]:
    (
        family,
        lifecycle_status,
        review_posture,
        evidence_packet_id,
        evidence_hash,
        candidate_json,
        updated_at_utc,
        candidate_id,
    ) = [_unwrap_jsonb(value) for value in params]
    for row in connection.rows["idea_candidate_record"]:
        if row["candidate_id"] != candidate_id:
            continue
        row["family"] = family
        row["lifecycle_status"] = lifecycle_status
        row["review_posture"] = review_posture
        row["evidence_packet_id"] = evidence_packet_id
        row["evidence_hash"] = evidence_hash
        row["candidate_json"] = candidate_json
        row["updated_at_utc"] = updated_at_utc
        return [dict(row)]
    return []


def _unwrap_jsonb(value: Any) -> Any:
    if hasattr(value, "obj"):
        return value.obj
    return value
