from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain import (
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    GovernedConversionIntent,
    IdeaLifecycleStatus,
    ReviewPosture,
    record_conversion_outcome,
    request_conversion_intent,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_conversion_outcome import (
    ConcurrentConversionOutcomeMutationError,
    insert_postgres_conversion_outcome,
)
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    StaleSnapshotRepository,
    access_scope,
    conversion_command,
    conversion_outcome_command,
    high_cash_candidate,
)


def repository_with_conversion_intent() -> tuple[
    FakePostgresConnection,
    PostgresIdeaRepository,
    GovernedConversionIntent,
]:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_conversion_outcome_lifecycle",
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:conversion-outcome-lifecycle",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    intent_result = request_conversion_intent(candidate, conversion_command())
    repository.record_conversion_intent(
        intent_result,
        idempotency_key=intent_result.conversion_intent.idempotency_key,
        payload={"conversionIntentId": intent_result.conversion_intent.intent.conversion_intent_id},
    )
    return connection, repository, intent_result.conversion_intent


def test_postgres_retries_equivalent_conversion_outcome_identity_as_replay() -> None:
    connection, repository, intent = repository_with_conversion_intent()
    base_snapshot = repository.snapshot()
    outcome = record_conversion_outcome(intent, conversion_outcome_command())

    first = StaleSnapshotRepository(connection, base_snapshot).record_conversion_outcome(
        outcome,
        idempotency_key="outcome:postgres-identity:first",
        payload={"conversionOutcomeId": outcome.conversion_outcome.outcome.conversion_outcome_id},
    )
    replayed = StaleSnapshotRepository(connection, base_snapshot).record_conversion_outcome(
        outcome,
        idempotency_key="outcome:postgres-identity:retry",
        payload={"conversionOutcomeId": outcome.conversion_outcome.outcome.conversion_outcome_id},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()
    record = recovered.candidate_records["idea_conversion_outcome_lifecycle"]

    assert first.decision is ConversionPersistenceDecision.ACCEPTED
    assert replayed.decision is ConversionPersistenceDecision.REPLAYED
    assert connection.rollbacks == 1
    assert len(record.conversion_outcomes) == 1
    assert len(record.audit_events) == 3
    assert len(recovered.outbox_events) == 3


def test_postgres_retries_changed_conversion_outcome_identity_as_conflict() -> None:
    connection, repository, intent = repository_with_conversion_intent()
    base_snapshot = repository.snapshot()
    accepted_command = conversion_outcome_command()
    accepted = record_conversion_outcome(intent, accepted_command)
    changed = record_conversion_outcome(
        intent,
        replace(
            accepted_command,
            status=ConversionOutcomeStatus.REJECTED,
            downstream_reference=None,
        ),
    )

    first = StaleSnapshotRepository(connection, base_snapshot).record_conversion_outcome(
        accepted,
        idempotency_key="outcome:postgres-conflict:first",
        payload={"status": "accepted"},
    )
    conflict = StaleSnapshotRepository(connection, base_snapshot).record_conversion_outcome(
        changed,
        idempotency_key="outcome:postgres-conflict:changed",
        payload={"status": "rejected"},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()
    record = recovered.candidate_records["idea_conversion_outcome_lifecycle"]

    assert first.decision is ConversionPersistenceDecision.ACCEPTED
    assert conflict.decision is ConversionPersistenceDecision.OUTCOME_CONFLICT
    assert connection.rollbacks == 1
    assert [outcome.outcome.status for outcome in record.conversion_outcomes] == [
        ConversionOutcomeStatus.ACCEPTED
    ]
    assert len(record.audit_events) == 3
    assert len(recovered.outbox_events) == 3


def test_postgres_serializes_competing_ids_for_the_same_source_version() -> None:
    connection, repository, intent = repository_with_conversion_intent()
    base_snapshot = repository.snapshot()
    accepted_command = conversion_outcome_command()
    accepted = record_conversion_outcome(intent, accepted_command)
    competing = record_conversion_outcome(
        intent,
        replace(
            accepted_command,
            conversion_outcome_id="conversion-outcome-competing-version",
            status=ConversionOutcomeStatus.REJECTED,
            downstream_reference=None,
        ),
    )

    first = StaleSnapshotRepository(connection, base_snapshot).record_conversion_outcome(
        accepted,
        idempotency_key="outcome:postgres-version:first",
        payload={"sourceEventVersion": 1, "status": "accepted"},
    )
    conflict = StaleSnapshotRepository(connection, base_snapshot).record_conversion_outcome(
        competing,
        idempotency_key="outcome:postgres-version:competing",
        payload={"sourceEventVersion": 1, "status": "rejected"},
    )
    recovered = PostgresIdeaRepository(connection).snapshot()
    record = recovered.candidate_records["idea_conversion_outcome_lifecycle"]

    assert first.decision is ConversionPersistenceDecision.ACCEPTED
    assert conflict.decision is ConversionPersistenceDecision.OUTCOME_CONFLICT
    assert connection.rollbacks == 1
    assert len(record.conversion_outcomes) == 1
    assert len(record.audit_events) == 3
    assert len(recovered.outbox_events) == 3


def test_postgres_conversion_outcome_read_and_precheck_are_restart_safe() -> None:
    connection, repository, intent = repository_with_conversion_intent()
    outcome = record_conversion_outcome(intent, conversion_outcome_command())
    payload = {"status": "accepted", "sourceEventVersion": 1}
    accepted = repository.record_conversion_outcome(
        outcome,
        idempotency_key="outcome:postgres-precheck:accepted",
        payload=payload,
    )
    restarted = PostgresIdeaRepository(connection)

    history = restarted.conversion_outcomes_for_intent(intent.intent.conversion_intent_id)
    replay = restarted.precheck_conversion_outcome_mutation(
        idempotency_key="outcome:postgres-precheck:recovered",
        payload=payload,
        identity=outcome.conversion_outcome.identity,
    )
    changed_payload = restarted.precheck_conversion_outcome_mutation(
        idempotency_key="outcome:postgres-precheck:recovered",
        payload={**payload, "status": "rejected"},
        identity=outcome.conversion_outcome.identity,
    )

    assert accepted.decision is ConversionPersistenceDecision.ACCEPTED
    assert history == (outcome.conversion_outcome,)
    assert replay is not None
    assert replay.decision is ConversionPersistenceDecision.REPLAYED
    assert replay.record is not None
    assert changed_payload is not None
    assert changed_payload.decision is ConversionPersistenceDecision.CONFLICT


def test_postgres_conversion_outcome_precheck_distinguishes_absent_and_changed_identity() -> None:
    connection, repository, intent = repository_with_conversion_intent()
    outcome = record_conversion_outcome(intent, conversion_outcome_command())
    repository.record_conversion_outcome(
        outcome,
        idempotency_key="outcome:postgres-identity:accepted",
        payload={"status": "accepted"},
    )
    restarted = PostgresIdeaRepository(connection)

    absent = restarted.precheck_conversion_outcome_mutation(
        idempotency_key="outcome:postgres-identity:absent",
        payload={"status": "accepted"},
        identity=replace(
            outcome.conversion_outcome.identity,
            conversion_outcome_id="conversion-outcome-absent",
        ),
    )
    conflict = restarted.precheck_conversion_outcome_mutation(
        idempotency_key="outcome:postgres-identity:conflict",
        payload={"status": "rejected"},
        identity=replace(
            outcome.conversion_outcome.identity,
            status=ConversionOutcomeStatus.REJECTED,
            downstream_reference=None,
        ),
    )

    assert absent is None
    assert conflict is not None
    assert conflict.decision is ConversionPersistenceDecision.OUTCOME_CONFLICT
    assert conflict.record is not None


def test_postgres_conversion_outcome_insert_reports_concurrent_identity() -> None:
    connection, _, intent = repository_with_conversion_intent()
    outcome = record_conversion_outcome(intent, conversion_outcome_command()).conversion_outcome

    with connection.cursor() as cursor:
        insert_postgres_conversion_outcome(cursor, outcome)
    with (
        connection.cursor() as cursor,
        pytest.raises(
            ConcurrentConversionOutcomeMutationError,
            match=outcome.outcome.conversion_outcome_id,
        ),
    ):
        insert_postgres_conversion_outcome(cursor, outcome)
