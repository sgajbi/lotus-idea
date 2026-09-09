from __future__ import annotations

from tests.support.http import ManagedTestClient, managed_test_client

from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import table_count
from tests.integration.test_review_workflow_api import (
    approve_candidate_for_conversion,
    conversion_intent_headers,
    conversion_intent_payload,
    conversion_outcome_headers,
    conversion_outcome_payload,
    persisted_candidate_id,
)


MUTATION_TABLES = frozenset(
    {
        "idea_conversion_outcome",
        "idea_idempotency_record",
        "idea_audit_event",
        "idea_outbox_event",
    }
)


def test_postgres_conversion_outcome_scope_denial_is_mutation_free_and_recoverable(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    intent_id = _seed_conversion_intent(client)
    before_denial = _mutation_counts(postgres_database_url)
    idempotency_key = "postgres-outcome-scope-001"
    payload = conversion_outcome_payload(conversion_outcome_id="postgres-outcome-scope-event-001")
    foreign_headers = conversion_outcome_headers(idempotency_key)
    foreign_headers.update(
        {
            "X-Caller-Tenant-Ids": "tenant-private-bank-hk",
            "X-Caller-Book-Ids": "book-other",
            "X-Caller-Portfolio-Ids": "portfolio-other",
            "X-Caller-Client-Ids": "client-other",
        }
    )

    denied = client.post(
        f"/api/v1/conversion-intents/{intent_id}/outcomes",
        json=payload,
        headers=foreign_headers,
    )

    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert _mutation_counts(postgres_database_url) == before_denial

    accepted = client.post(
        f"/api/v1/conversion-intents/{intent_id}/outcomes",
        json=payload,
        headers=conversion_outcome_headers(idempotency_key),
    )
    after_acceptance = _mutation_counts(postgres_database_url)

    assert accepted.status_code == 200
    assert accepted.json()["persistence"]["decision"] == "accepted"
    assert after_acceptance == {
        **before_denial,
        "idea_conversion_outcome": before_denial["idea_conversion_outcome"] + 1,
        "idea_idempotency_record": before_denial["idea_idempotency_record"] + 1,
        "idea_audit_event": before_denial["idea_audit_event"] + 1,
        "idea_outbox_event": before_denial["idea_outbox_event"] + 1,
    }

    reset_idea_repository_for_tests(reload_from_environment=True)
    replay_client = managed_test_client(app)
    replayed = replay_client.post(
        f"/api/v1/conversion-intents/{intent_id}/outcomes",
        json=payload,
        headers=conversion_outcome_headers(idempotency_key),
    )

    assert replayed.status_code == 200
    assert replayed.json()["conversionOutcome"] == accepted.json()["conversionOutcome"]
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert _mutation_counts(postgres_database_url) == after_acceptance


def _seed_conversion_intent(client: ManagedTestClient) -> str:
    candidate_id = persisted_candidate_id(client, idempotency_key="postgres-outcome-scope-seed")
    approve_candidate_for_conversion(client, candidate_id)
    intent_id = "postgres-outcome-scope-intent-001"
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=intent_id),
        headers=conversion_intent_headers("postgres-outcome-scope-intent-key-001"),
    )
    assert response.status_code == 200
    return intent_id


def _mutation_counts(database_url: str) -> dict[str, int]:
    return {
        table_name: table_count(
            database_url,
            table_name,
            allowed_tables=MUTATION_TABLES,
        )
        for table_name in sorted(MUTATION_TABLES)
    }
