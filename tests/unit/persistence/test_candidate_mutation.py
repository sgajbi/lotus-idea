from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import pytest

from app.domain import CandidatePersistenceDecision
from app.domain.idempotency import IdempotencyRecord
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.persistence.candidate_mutation import (
    load_candidate_persistence_snapshot,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
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
    assert "candidate-persistence-candidate-lock" in connection.executed_sql[0]
    assert "candidate-persistence-idempotency-lock" in connection.executed_sql[1]
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
        "app.infrastructure.persistence.candidate_mutation.load_idempotency_record_by_key",
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
        "app.infrastructure.persistence.candidate_mutation.load_candidate_record_for_mutation",
        load_candidate,
    )

    snapshot = load_candidate_persistence_snapshot(
        FakePostgresConnection(),
        candidate_id=candidate.candidate_id,
        idempotency_key="candidate:linked-replay",
    )

    assert loaded_candidate_ids == sorted((candidate.candidate_id, linked.candidate_id))
    assert tuple(snapshot.candidate_records) == (linked.candidate_id,)
    assert snapshot.idempotency_candidates == {"candidate:linked-replay": linked.candidate_id}
