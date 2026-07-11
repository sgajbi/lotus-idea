from __future__ import annotations

from app.domain import IdeaLifecycleStatus
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    high_cash_candidate,
)


def test_postgres_repository_loads_candidate_detail_without_whole_snapshot() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:high-cash:detail",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    repository.record_lifecycle_transition(
        candidate.candidate_id,
        IdeaLifecycleStatus.ENRICHED,
        idempotency_key="candidate-detail:lifecycle",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="idea-lifecycle-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    connection.executed_sql.clear()

    loaded = PostgresIdeaRepository(connection).candidate_record_by_id(candidate.candidate_id)

    assert loaded is not None
    assert loaded.candidate.candidate_id == candidate.candidate_id
    assert [entry.target_status for entry in loaded.lifecycle_history] == [
        IdeaLifecycleStatus.ENRICHED
    ]
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea candidate-detail-base */" in executed_sql
    assert "candidate.candidate_id = %s" in executed_sql
    assert "join idea_data_lifecycle_control" in executed_sql
    assert "idea_candidate_record" in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql
    assert "idea_idempotency_record" not in executed_sql


def test_postgres_repository_candidate_detail_returns_none_for_missing_candidate() -> None:
    connection = FakePostgresConnection()

    loaded = PostgresIdeaRepository(connection).candidate_record_by_id("missing-candidate")

    assert loaded is None
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea candidate-detail-base */" in executed_sql
    assert "candidate-detail-lifecycle" not in executed_sql


def test_postgres_repository_hides_erased_candidate_detail() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:hidden-erased-detail",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    control = connection.rows["idea_data_lifecycle_control"][0]
    control["state"] = "erased"

    assert repository.candidate_record_by_id(candidate.candidate_id) is None
