from __future__ import annotations

from app.main import app
from app.runtime.repository_state import (
    get_idea_repository,
    reset_idea_repository_for_tests,
)
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    table_count,
)
from tests.integration.test_review_workflow_api import (
    approve_review_payload,
    conversion_intent_headers,
    conversion_intent_payload,
    review_headers,
    transition_candidate_to_review_ready,
)
from tests.support.http import managed_test_client


SIDE_EFFECT_TABLES = frozenset(
    {
        "idea_review_decision",
        "idea_conversion_intent",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_idempotency_record",
    }
)


def test_postgres_causal_revision_contradiction_survives_reload_and_refuses_authority(
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    request = high_cash_payload()
    holdings = request["sourceEvidence"]["holdingsRef"]
    holdings["revisionClaims"]["sourceRevision"] = "holdings-revision-2"
    request["sourceEvidence"]["portfolioStateRef"]["revisionClaims"]["causalInputRevisions"] = [
        {
            "productId": holdings["productId"],
            "sourceRevision": "holdings-revision-1",
        }
    ]
    headers = persistence_headers("postgres-causal-revision-conflict-001")

    accepted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=request,
        headers=headers,
    )
    assert accepted.status_code == 200
    candidate_id = accepted.json()["persistence"]["candidateId"]

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=request,
        headers={**headers, "X-Trace-Id": "trace-postgres-causal-revision-replay"},
    )
    assert replayed.status_code == 200
    assert replayed.json()["persistence"]["decision"] == "replayed"
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.candidate.evidence_packet.source_cut_posture.value == "mixed"

    transition_candidate_to_review_ready(client, candidate_id)
    counts_before_refusal = _side_effect_counts(postgres_database_url)
    review = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=approve_review_payload(candidate_id),
        headers=review_headers("postgres-causal-revision-review-001"),
    )
    conversion = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(
            conversion_intent_id="postgres-causal-revision-conversion-001"
        ),
        headers=conversion_intent_headers("postgres-causal-revision-conversion-001"),
    )

    assert review.status_code == 409
    assert review.json()["code"] == "review_action_conflict"
    assert conversion.status_code == 409
    assert conversion.json()["code"] == "conversion_intent_conflict"
    assert _side_effect_counts(postgres_database_url) == counts_before_refusal


def _side_effect_counts(postgres_database_url: str) -> dict[str, int]:
    return {
        table: table_count(
            postgres_database_url,
            table,
            allowed_tables=SIDE_EFFECT_TABLES,
        )
        for table in SIDE_EFFECT_TABLES
    }
