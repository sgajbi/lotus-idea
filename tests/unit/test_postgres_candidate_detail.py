from __future__ import annotations

import pytest

from app.domain import IdeaLifecycleStatus
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    high_cash_candidate,
)
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim


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


def test_postgres_repository_loads_only_candidate_scoped_downstream_submissions() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate(candidate_scope=access_scope())
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:detail-submission",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    connection.rows["idea_conversion_intent"].extend(
        (
            {
                "conversion_intent_id": "conversion-detail-owned",
                "candidate_id": candidate.candidate_id,
            },
            {
                "conversion_intent_id": "conversion-detail-other",
                "candidate_id": "candidate-other",
            },
        )
    )
    repository.claim_downstream_submission(
        build_downstream_submission_claim(
            idempotency_key="submission-detail-owned",
            request_fingerprint="sha256:submission-detail-owned",
            resource_id="conversion-detail-owned",
            submitted_at_utc=EVALUATED_AT,
        )
    )
    connection.rows["idea_downstream_submission"].append(
        {
            **connection.rows["idea_downstream_submission"][0],
            "idempotency_key": "submission-detail-other",
            "resource_id": "conversion-detail-other",
        }
    )
    connection.executed_sql.clear()

    submissions = repository.downstream_submissions_for_candidate(candidate.candidate_id)

    assert [submission.resource_id for submission in submissions] == ["conversion-detail-owned"]
    matching_queries = [
        sql for sql in connection.executed_sql if "candidate-detail-downstream-submissions" in sql
    ]
    assert len(matching_queries) == 1
    assert "idea_conversion_intent" in matching_queries[0]
    assert "idea_report_evidence_pack_request" in matching_queries[0]


def test_postgres_candidate_submission_projection_rejects_blank_candidate_id() -> None:
    repository = PostgresIdeaRepository(FakePostgresConnection())

    with pytest.raises(ValueError, match="candidate_id is required"):
        repository.downstream_submissions_for_candidate(" ")
