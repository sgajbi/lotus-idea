from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
from tests.support.http import managed_test_client

from app.domain import (
    ConversionIntentCommand,
    ConversionPersistenceDecision,
    ConversionTarget,
    InvalidConversionIntent,
    ReasonCode,
    request_conversion_intent,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    run_concurrent_repository_mutations,
    table_count,
)


TRACKED_TABLES = frozenset(
    {
        "idea_conversion_intent",
        "idea_lifecycle_history",
        "idea_audit_event",
        "idea_outbox_event",
        "idea_idempotency_record",
    }
)


def test_postgres_fences_competing_conversion_intents(
    postgres_database_url: str,
) -> None:
    candidate_id = _persist_approved_candidate()
    candidate = _load_record(postgres_database_url, candidate_id).candidate
    competing_results = {
        "conversion:competing:advise": request_conversion_intent(
            candidate,
            _conversion_command(
                conversion_intent_id="postgres-competing-advise-001",
                target=ConversionTarget.ADVISE_PROPOSAL,
                idempotency_key="conversion:competing:advise",
            ),
        ),
        "conversion:competing:report": request_conversion_intent(
            candidate,
            _conversion_command(
                conversion_intent_id="postgres-competing-report-001",
                target=ConversionTarget.REPORT_EVIDENCE,
                idempotency_key="conversion:competing:report",
            ),
        ),
    }
    before_counts = _tracked_counts(postgres_database_url)

    def persist(
        repository: PostgresIdeaRepository,
        idempotency_key: str,
    ) -> ConversionPersistenceDecision | InvalidConversionIntent:
        result = competing_results[idempotency_key]
        try:
            return repository.record_conversion_intent(
                result,
                idempotency_key=idempotency_key,
                payload={
                    "conversionIntentId": result.conversion_intent.intent.conversion_intent_id,
                    "target": result.conversion_intent.intent.target.value,
                },
            ).decision
        except InvalidConversionIntent as exc:
            return exc

    outcomes = run_concurrent_repository_mutations(
        postgres_database_url,
        persist,
        ("conversion:competing:advise", "conversion:competing:report"),
    )

    assert sum(outcome is ConversionPersistenceDecision.ACCEPTED for outcome in outcomes) == 1
    stale_conflict = next(
        outcome for outcome in outcomes if isinstance(outcome, InvalidConversionIntent)
    )
    assert stale_conflict.candidate_id == candidate_id
    assert stale_conflict.reason == (
        "candidate state changed after conversion readiness evaluation"
    )
    assert _tracked_counts(postgres_database_url) == {
        table: count + 1 for table, count in before_counts.items()
    }
    record = _load_record(postgres_database_url, candidate_id)
    assert len(record.conversion_intents) == 1
    assert record.conversion_intents[0].intent.target.value in {
        "advise_proposal",
        "report_evidence",
    }
    assert record.conversion_intents[0].intent.source_status.value == "approved"


def _persist_approved_candidate() -> str:
    client = managed_test_client(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-conversion-intent-fence-persist-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    for minute, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        transitioned = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json={
                "transitionId": f"postgres-conversion-fence-{target_status}-001",
                "targetLifecycleStatus": target_status,
                "reasonCodes": ["review_required"],
                "changedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
            },
            headers={
                "X-Caller-Subject": "idea-lifecycle-worker",
                "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
                "X-Correlation-Id": "corr-postgres-conversion-intent-fence",
                "X-Trace-Id": f"trace-postgres-conversion-fence-{target_status}",
                "Idempotency-Key": f"postgres-conversion-fence-{target_status}-001",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["persistence"]["decision"] == "accepted"
        reset_idea_repository_for_tests(reload_from_environment=True)
    approved = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json={
            "reviewId": "postgres-conversion-fence-approval-001",
            "action": "approve_for_conversion",
            "reasonCodes": ["review_required"],
            "decidedAtUtc": "2026-06-21T10:05:00Z",
        },
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Roles": "advisor",
            "X-Caller-Capabilities": "idea.review.record",
            "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
            "X-Caller-Book-Ids": "book-advisor-001",
            "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
            "X-Caller-Client-Ids": "client-001",
            "X-Correlation-Id": "corr-postgres-conversion-intent-fence",
            "X-Trace-Id": "trace-postgres-conversion-fence-approval",
            "Idempotency-Key": "postgres-conversion-fence-approval-001",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["persistence"]["lifecycleStatus"] == "approved"
    reset_idea_repository_for_tests(reload_from_environment=True)
    return candidate_id


def _conversion_command(
    *,
    conversion_intent_id: str,
    target: ConversionTarget,
    idempotency_key: str,
) -> ConversionIntentCommand:
    return ConversionIntentCommand(
        conversion_intent_id=conversion_intent_id,
        target=target,
        actor_subject="advisor-001",
        idempotency_key=idempotency_key,
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=datetime(2026, 6, 21, 10, 6, tzinfo=UTC),
    )


def _load_record(database_url: str, candidate_id: str) -> Any:
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        record = PostgresIdeaRepository(cast(Any, connection)).candidate_record_by_id(candidate_id)
    assert record is not None
    return record


def _tracked_counts(database_url: str) -> dict[str, int]:
    return {
        table: table_count(database_url, table, allowed_tables=TRACKED_TABLES)
        for table in TRACKED_TABLES
    }
