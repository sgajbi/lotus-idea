from __future__ import annotations

from typing import cast

import psycopg
from psycopg.rows import dict_row

from app.domain import (
    CandidatePersistenceDecision,
    CandidatePersistenceResult,
    InMemoryIdeaRepository,
)
from app.domain.idempotency import IdempotencyDecision
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.infrastructure.postgres_protocols import PostgresConnection
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    run_concurrent_repository_mutations,
)
from tests.support.http import managed_test_client
from tests.unit.test_idea_persistence import EVALUATED_AT, high_cash_candidate


def test_postgres_candidate_idempotency_is_tenant_scoped_across_restart(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    shared_headers = persistence_headers("postgres-shared-client-key")
    tenant_a_payload = high_cash_payload()
    tenant_b_payload = high_cash_payload()
    tenant_b_payload["accessScope"] = {
        "tenantId": "tenant-private-bank-hk",
        "bookId": "book-advisor-hk",
        "portfolioId": "PB_HK_GLOBAL_BAL_001",
        "clientId": "client-hk-001",
    }

    accepted_a = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=tenant_a_payload,
        headers=shared_headers,
    )
    reset_idea_repository_for_tests(reload_from_environment=True)
    accepted_b = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=tenant_b_payload,
        headers=shared_headers,
    )
    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_a = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=tenant_a_payload,
        headers=shared_headers,
    )
    replayed_b = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=tenant_b_payload,
        headers=shared_headers,
    )

    assert [
        accepted_a.json()["persistence"]["decision"],
        accepted_b.json()["persistence"]["decision"],
        replayed_a.json()["persistence"]["decision"],
        replayed_b.json()["persistence"]["decision"],
    ] == ["accepted", "accepted", "replayed", "replayed"]
    assert (
        accepted_a.json()["persistence"]["candidateId"]
        != (accepted_b.json()["persistence"]["candidateId"])
    )
    assert (
        replayed_a.json()["persistence"]["candidateId"]
        == (accepted_a.json()["persistence"]["candidateId"])
    )
    assert (
        replayed_b.json()["persistence"]["candidateId"]
        == (accepted_b.json()["persistence"]["candidateId"])
    )
    with psycopg.connect(postgres_database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tenant_id
            FROM idea_idempotency_record
            WHERE idempotency_key = 'postgres-shared-client-key'
            ORDER BY tenant_id
            """
        )
        assert [row[0] for row in cursor.fetchall()] == [
            "tenant-private-bank-hk",
            "tenant-private-bank-sg",
        ]


def test_postgres_concurrent_tenants_reserve_the_same_raw_key_independently(
    postgres_database_url: str,
) -> None:
    candidate_a, _ = high_cash_candidate(tenant_id="tenant-concurrent-a")
    candidate_b, _ = high_cash_candidate(tenant_id="tenant-concurrent-b")
    candidates = {
        "tenant-concurrent-a": candidate_a,
        "tenant-concurrent-b": candidate_b,
    }
    shared_key = "postgres-concurrent-shared-key"

    def persist(
        repository: PostgresIdeaRepository,
        tenant_id: str,
    ) -> CandidatePersistenceResult:
        candidate = candidates[tenant_id]
        return repository.persist_candidate(
            candidate,
            idempotency_key=shared_key,
            payload={"candidateId": candidate.candidate_id},
            actor_subject="signal-ingestion-worker",
            occurred_at_utc=EVALUATED_AT,
        )

    accepted_a, accepted_b = run_concurrent_repository_mutations(
        postgres_database_url,
        persist,
        ("tenant-concurrent-a", "tenant-concurrent-b"),
    )

    assert accepted_a.decision is CandidatePersistenceDecision.ACCEPTED
    assert accepted_b.decision is CandidatePersistenceDecision.ACCEPTED
    with psycopg.connect(postgres_database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tenant_id, candidate_id
            FROM idea_idempotency_record
            WHERE idempotency_key = %s
            ORDER BY tenant_id
            """,
            (shared_key,),
        )
        assert cursor.fetchall() == [
            ("tenant-concurrent-a", candidate_a.candidate_id),
            ("tenant-concurrent-b", candidate_b.candidate_id),
        ]


def test_postgres_snapshot_preserves_system_idempotency_replay(
    postgres_database_url: str,
) -> None:
    raw_key = "outbox-delivery-run:postgres-snapshot"
    payload = {"maxEvents": 25}
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(PostgresConnection, connection))
        accepted = repository.record_outbox_delivery_run_request(
            idempotency_key=raw_key,
            payload=payload,
        )
        snapshot = repository.snapshot()

    restored = InMemoryIdeaRepository(snapshot)
    replayed = restored.record_outbox_delivery_run_request(
        idempotency_key=raw_key,
        payload=payload,
    )

    assert accepted is IdempotencyDecision.ACCEPTED
    assert replayed is IdempotencyDecision.REPLAYED
