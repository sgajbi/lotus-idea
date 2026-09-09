from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg

from app.main import app
from app.application.candidate_lifecycle import (
    ApplyCandidateLifecycleTransitionCommand,
    apply_candidate_lifecycle_transition_to_repository,
)
from app.domain import IdeaLifecycleStatus, LifecyclePersistenceDecision, QueueAccessScopeFilter
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    run_concurrent_repository_mutations,
    table_count,
)
from tests.integration.test_review_workflow_api import (
    lifecycle_headers,
    lifecycle_payload,
    persisted_candidate_id,
)
from tests.support.http import managed_test_client


MUTATION_TABLES = frozenset(
    {
        "idea_idempotency_record",
        "idea_audit_event",
        "idea_outbox_event",
    }
)


def test_postgres_lifecycle_scope_denial_is_mutation_free_and_recoverable(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key="postgres-lifecycle-scope-seed-001",
    )
    before_counts = _mutation_counts(postgres_database_url)
    before_candidate = _candidate_payload(postgres_database_url, candidate_id)
    idempotency_key = "postgres-lifecycle-scope-001"
    request = lifecycle_payload()
    foreign_headers = lifecycle_headers(idempotency_key)
    foreign_headers["X-Caller-Tenant-Ids"] = "tenant-private-bank-hk"

    denied = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=request,
        headers=foreign_headers,
    )

    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert _mutation_counts(postgres_database_url) == before_counts
    assert _candidate_payload(postgres_database_url, candidate_id) == before_candidate

    accepted = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=request,
        headers=lifecycle_headers(idempotency_key),
    )
    after_acceptance_counts = _mutation_counts(postgres_database_url)
    after_acceptance_candidate = _candidate_payload(postgres_database_url, candidate_id)

    assert accepted.status_code == 200
    assert accepted.json()["persistence"]["decision"] == "accepted"
    assert after_acceptance_counts == {
        **before_counts,
        "idea_idempotency_record": before_counts["idea_idempotency_record"] + 1,
        "idea_audit_event": before_counts["idea_audit_event"] + 1,
        "idea_outbox_event": before_counts["idea_outbox_event"] + 1,
    }
    assert after_acceptance_candidate != before_candidate

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = managed_test_client(app).post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=request,
        headers=lifecycle_headers(idempotency_key),
    )

    assert replayed.status_code == 200
    assert replayed.json()["transition"] == accepted.json()["transition"]
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert _mutation_counts(postgres_database_url) == after_acceptance_counts
    assert _candidate_payload(postgres_database_url, candidate_id) == after_acceptance_candidate


def test_postgres_lifecycle_scope_authorization_preserves_concurrent_exact_replay(
    postgres_database_url: str,
) -> None:
    candidate_id = persisted_candidate_id(
        managed_test_client(app),
        idempotency_key="postgres-lifecycle-concurrent-scope-seed-001",
    )
    before_counts = _mutation_counts(postgres_database_url)

    decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: _record_lifecycle_transition(
            repository,
            candidate_id=candidate_id,
            idempotency_key=key,
        ),
        (
            "postgres-lifecycle-concurrent-scope-001",
            "postgres-lifecycle-concurrent-scope-001",
        ),
    )

    assert set(decisions) == {
        LifecyclePersistenceDecision.ACCEPTED,
        LifecyclePersistenceDecision.REPLAYED,
    }
    assert _mutation_counts(postgres_database_url) == {
        **before_counts,
        "idea_idempotency_record": before_counts["idea_idempotency_record"] + 1,
        "idea_audit_event": before_counts["idea_audit_event"] + 1,
        "idea_outbox_event": before_counts["idea_outbox_event"] + 1,
    }


def _record_lifecycle_transition(
    repository: PostgresIdeaRepository,
    *,
    candidate_id: str,
    idempotency_key: str,
) -> LifecyclePersistenceDecision:
    result = apply_candidate_lifecycle_transition_to_repository(
        ApplyCandidateLifecycleTransitionCommand(
            candidate_id=candidate_id,
            transition_id="postgres-lifecycle-concurrent-scope-transition-001",
            target_status=IdeaLifecycleStatus.ENRICHED,
            changed_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
            accepted_at_utc=datetime(2026, 6, 21, 10, 15, tzinfo=UTC),
            reason_codes=("review_required",),
            actor_subject="idea-lifecycle-worker",
            idempotency_key=idempotency_key,
            access_scope_filter=QueueAccessScopeFilter(
                tenant_id="tenant-private-bank-sg",
                book_id="book-advisor-001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                client_id="client-001",
            ),
        ),
        repository=repository,
    )
    return result.persistence.decision


def _mutation_counts(database_url: str) -> dict[str, int]:
    return {
        table_name: table_count(
            database_url,
            table_name,
            allowed_tables=MUTATION_TABLES,
        )
        for table_name in sorted(MUTATION_TABLES)
    }


def _candidate_payload(database_url: str, candidate_id: str) -> Any:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT candidate_json FROM idea_candidate_record WHERE candidate_id = %s",
            (candidate_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"Candidate {candidate_id} was not retained")
    return row[0]
