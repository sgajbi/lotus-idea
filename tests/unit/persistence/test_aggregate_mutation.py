from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import pytest

from app.domain import CandidatePersistenceDecision, EvidenceReplayStatus
from app.domain.idempotency import IdempotencyDecision
from app.domain.idempotency import IdempotencyRecord
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.persistence.aggregate_mutation import (
    load_candidate_mutation_snapshot,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.postgres_repository_query_assertions import assert_no_whole_store_snapshot
from tests.unit.test_postgres_repository import access_scope, high_cash_candidate


EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def test_candidate_persistence_loads_only_candidate_scoped_state() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())

    result = repository.persist_candidate(
        candidate,
        idempotency_key="candidate:bounded-write",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )

    assert result.decision is CandidatePersistenceDecision.ACCEPTED
    assert "aggregate-mutation-candidate-lock" in connection.executed_sql[0]
    assert "aggregate-mutation-idempotency-lock" in connection.executed_sql[1]
    assert any("candidate-detail-mutation-base" in sql for sql in connection.executed_sql)
    assert not any("from idea_review_decision" in sql for sql in connection.executed_sql)
    assert not any("from idea_feedback_event" in sql for sql in connection.executed_sql)
    assert not any("from idea_conversion_intent" in sql for sql in connection.executed_sql)
    assert not any("from idea_outbox_event" in sql for sql in connection.executed_sql)


def test_candidate_persistence_snapshot_loads_idempotency_linked_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_candidate_ids: list[str] = []
    candidate = high_cash_candidate(candidate_scope=access_scope())
    linked = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_linked",
    )

    monkeypatch.setattr(
        "app.infrastructure.persistence.aggregate_mutation.load_idempotency_record_by_key",
        lambda connection, key: (
            IdempotencyRecord(key=key, payload_hash="hash"),
            linked.candidate_id,
        ),
    )

    def load_candidate(connection: object, candidate_id: str) -> CandidatePersistenceRecord | None:
        del connection
        loaded_candidate_ids.append(candidate_id)
        if candidate_id == linked.candidate_id:
            return CandidatePersistenceRecord(
                candidate=linked,
                evidence_hash="evidence-hash",
                persisted_at_utc=EVALUATED_AT,
            )
        return None

    monkeypatch.setattr(
        "app.infrastructure.persistence.aggregate_mutation.load_candidate_record_for_mutation",
        load_candidate,
    )

    snapshot = load_candidate_mutation_snapshot(
        FakePostgresConnection(),
        candidate_ids=(candidate.candidate_id,),
        idempotency_key="candidate:linked-replay",
    )

    assert loaded_candidate_ids == sorted((candidate.candidate_id, linked.candidate_id))
    assert tuple(snapshot.candidate_records) == (linked.candidate_id,)
    assert snapshot.idempotency_candidates == {"candidate:linked-replay": linked.candidate_id}


def test_outbox_run_idempotency_does_not_load_candidate_or_event_state() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)

    decision = repository.record_outbox_delivery_run_request(
        idempotency_key="outbox-run:bounded",
        payload={"maxEvents": 25},
    )
    replayed = repository.record_outbox_delivery_run_request(
        idempotency_key="outbox-run:bounded",
        payload={"maxEvents": 25},
    )

    assert decision is IdempotencyDecision.ACCEPTED
    assert replayed is IdempotencyDecision.REPLAYED
    assert "aggregate-mutation-idempotency-lock" in connection.executed_sql[0]
    assert any("idempotency-lookup" in sql for sql in connection.executed_sql)
    assert not any("candidate-detail" in sql for sql in connection.executed_sql)
    assert not any("from idea_outbox_event" in sql for sql in connection.executed_sql)


def test_replay_and_idempotency_precheck_use_exact_candidate_state() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    payload = {"candidateId": candidate.candidate_id}
    repository.persist_candidate(
        candidate,
        idempotency_key="candidate:bounded-replay",
        payload=payload,
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    connection.executed_sql.clear()

    absent_precheck = repository.precheck_evidence_pack_mutation(
        idempotency_key="report-pack:absent",
        payload={"reportEvidencePackId": "missing"},
    )
    replay = repository.replay_evidence(
        candidate.candidate_id,
        current_source_refs=candidate.evidence_packet.source_refs,
        evaluated_at_utc=EVALUATED_AT,
    )
    precheck = repository.precheck_evidence_pack_mutation(
        idempotency_key="candidate:bounded-replay",
        payload=payload,
    )

    assert absent_precheck is None
    assert replay.status is EvidenceReplayStatus.MATCHED
    assert precheck is not None
    assert any("candidate-detail-mutation-base" in sql for sql in connection.executed_sql)
    assert any("idempotency-lookup" in sql for sql in connection.executed_sql)
    assert_no_whole_store_snapshot(connection.executed_sql)
