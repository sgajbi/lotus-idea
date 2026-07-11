from __future__ import annotations

from dataclasses import replace

from app.domain import (
    IdeaLifecycleStatus,
    ReviewPosture,
    apply_review_action,
    request_conversion_intent,
)
from app.domain.persistence import ConversionPersistenceDecision, ReviewPersistenceDecision
from app.domain.idempotency import IdempotencyDecision, evaluate_idempotency
from app.infrastructure.postgres_idempotency_reservation import reserve_replayed_idempotency
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    conversion_command,
    high_cash_candidate,
    review_command,
)


def test_postgres_review_and_conversion_idempotency_prechecks_are_bounded() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    review_ready = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_bounded_review_precheck",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    approved = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_bounded_conversion_precheck",
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    for candidate in (review_ready, approved):
        repository.persist_candidate(
            candidate,
            idempotency_key=f"candidate:{candidate.candidate_id}",
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )

    review_result = apply_review_action(
        review_ready,
        review_command(review_id="review-bounded-precheck"),
    )
    repository.record_review_action(
        review_result,
        idempotency_key="review:bounded-precheck",
        payload={"reviewId": review_result.decision.review_id},
    )
    conversion_result = request_conversion_intent(approved, conversion_command())
    repository.record_conversion_intent(
        conversion_result,
        idempotency_key="conversion:intent",
        payload={
            "conversionIntentId": (conversion_result.conversion_intent.intent.conversion_intent_id)
        },
    )

    connection.executed_sql.clear()
    review_replay = repository.precheck_review_mutation(
        idempotency_key="review:bounded-precheck",
        payload={"reviewId": review_result.decision.review_id},
        identity=review_result.decision.mutation_identity,
    )
    review_replay_sql = tuple(connection.executed_sql)
    connection.executed_sql.clear()
    review_conflict = repository.precheck_review_mutation(
        idempotency_key="review:bounded-precheck",
        payload={"reviewId": "different-review-payload"},
        identity=review_result.decision.mutation_identity,
    )
    review_conflict_sql = tuple(connection.executed_sql)
    connection.executed_sql.clear()
    conversion_replay = repository.precheck_conversion_mutation(
        idempotency_key="conversion:intent",
        payload={
            "conversionIntentId": (conversion_result.conversion_intent.intent.conversion_intent_id)
        },
    )
    conversion_replay_sql = tuple(connection.executed_sql)
    connection.executed_sql.clear()
    conversion_conflict = repository.precheck_conversion_mutation(
        idempotency_key="conversion:intent",
        payload={"conversionIntentId": "different-conversion-intent"},
    )
    conversion_conflict_sql = tuple(connection.executed_sql)

    assert review_replay is not None
    assert review_replay.decision is ReviewPersistenceDecision.REPLAYED
    assert review_replay.record is not None
    assert review_replay.record.candidate.candidate_id == review_ready.candidate_id
    assert_bounded_idempotency_precheck_sql(review_replay_sql)
    assert review_conflict is not None
    assert review_conflict.decision is ReviewPersistenceDecision.CONFLICT
    assert review_conflict.record is not None
    assert review_conflict.record.candidate.candidate_id == review_ready.candidate_id
    assert_bounded_idempotency_precheck_sql(review_conflict_sql)
    assert conversion_replay is not None
    assert conversion_replay.decision is ConversionPersistenceDecision.REPLAYED
    assert conversion_replay.record is not None
    assert conversion_replay.record.candidate.candidate_id == approved.candidate_id
    assert_bounded_idempotency_precheck_sql(conversion_replay_sql)
    assert conversion_conflict is not None
    assert conversion_conflict.decision is ConversionPersistenceDecision.CONFLICT
    assert conversion_conflict.record is not None
    assert conversion_conflict.record.candidate.candidate_id == approved.candidate_id
    assert_bounded_idempotency_precheck_sql(conversion_conflict_sql)


def test_postgres_review_identity_precheck_replays_and_reserves_a_new_transport_key() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_resource_identity_precheck",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:resource-identity-precheck",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    review_result = apply_review_action(
        candidate,
        review_command(review_id="review-resource-identity-precheck"),
    )
    repository.record_review_action(
        review_result,
        idempotency_key="review:resource-precheck:first",
        payload={"reviewId": review_result.decision.review_id},
    )

    connection.executed_sql.clear()
    replayed = repository.precheck_review_mutation(
        idempotency_key="review:resource-precheck:retry",
        payload={"reviewId": review_result.decision.review_id},
        identity=review_result.decision.mutation_identity,
    )
    replay_sql = tuple(connection.executed_sql)
    conflict = repository.precheck_review_mutation(
        idempotency_key="review:resource-precheck:changed",
        payload={"reviewId": review_result.decision.review_id, "action": "reject"},
        identity=replace(
            review_result.decision.mutation_identity,
            event_name="reject",
        ),
    )

    assert replayed is not None
    assert replayed.decision is ReviewPersistenceDecision.REPLAYED
    assert any(sql.startswith("/* lotus-idea review-identity-decision */") for sql in replay_sql)
    assert any(
        row["idempotency_key"] == "review:resource-precheck:retry"
        for row in connection.rows["idea_idempotency_record"]
    )
    assert conflict is not None
    assert conflict.decision is ReviewPersistenceDecision.IDENTITY_CONFLICT
    assert not any(
        row["idempotency_key"] == "review:resource-precheck:changed"
        for row in connection.rows["idea_idempotency_record"]
    )


def test_replay_reservation_revalidates_the_durable_winner() -> None:
    connection = FakePostgresConnection()
    _, winner = evaluate_idempotency(
        key="review:concurrent-reservation",
        payload={"reviewId": "review-001"},
        existing=None,
    )
    _, conflicting = evaluate_idempotency(
        key=winner.key,
        payload={"reviewId": "review-002"},
        existing=None,
    )

    accepted = reserve_replayed_idempotency(
        connection,
        record=winner,
        candidate_id="candidate-001",
        occurred_at_utc=EVALUATED_AT,
    )
    replayed = reserve_replayed_idempotency(
        connection,
        record=winner,
        candidate_id="candidate-001",
        occurred_at_utc=EVALUATED_AT,
    )
    conflict = reserve_replayed_idempotency(
        connection,
        record=conflicting,
        candidate_id="candidate-001",
        occurred_at_utc=EVALUATED_AT,
    )

    assert accepted is IdempotencyDecision.ACCEPTED
    assert replayed is IdempotencyDecision.REPLAYED
    assert conflict is IdempotencyDecision.CONFLICT


def assert_bounded_idempotency_precheck_sql(executed_sql: tuple[str, ...]) -> None:
    joined_sql = " ".join(executed_sql)
    assert "/* lotus-idea idempotency-lookup */" in joined_sql
    assert "where idempotency_key = %s" in joined_sql
    assert "/* lotus-idea candidate-detail-base */" in joined_sql
    assert (
        "select candidate_id, evidence_hash, candidate_json, persisted_at_utc "
        "from idea_candidate_record order by" not in joined_sql
    )
    assert "from idea_outbox_event" not in joined_sql
    assert "from idea_downstream_submission" not in joined_sql
