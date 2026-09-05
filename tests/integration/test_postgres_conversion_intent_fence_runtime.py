from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
from tests.support.http import managed_test_client

from app.application.candidate_expiry import (
    CandidateExpiryDecision,
    ExpireCandidateCommand,
    expire_candidate_if_due,
)
from app.domain import (
    CandidateEvidenceIdentity,
    ConversionIntentCommand,
    ConversionPersistenceDecision,
    ConversionTarget,
    IdeaLifecycleStatus,
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
from tests.support.review_authority_api import record_workbench_presentation


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
    record = _load_record(postgres_database_url, candidate_id)
    candidate = record.candidate
    authority_grant = record.review_decisions[-1].authority_grant
    assert authority_grant is not None
    competing_results = {
        "conversion:competing:advise": request_conversion_intent(
            candidate,
            _conversion_command(
                conversion_intent_id="postgres-competing-advise-001",
                target=ConversionTarget.ADVISE_PROPOSAL,
                idempotency_key="conversion:competing:advise",
                candidate=candidate,
            ),
            accepted_at_utc=datetime(2026, 6, 21, 10, 15, tzinfo=UTC),
            review_authority_grant=authority_grant,
        ),
        "conversion:competing:report": request_conversion_intent(
            candidate,
            _conversion_command(
                conversion_intent_id="postgres-competing-report-001",
                target=ConversionTarget.REPORT_EVIDENCE,
                idempotency_key="conversion:competing:report",
                candidate=candidate,
            ),
            accepted_at_utc=datetime(2026, 6, 21, 10, 15, tzinfo=UTC),
            review_authority_grant=authority_grant,
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


def test_postgres_serializes_conversion_immediately_before_expiry_against_expiry(
    postgres_database_url: str,
) -> None:
    expiry = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
    candidate_id = _persist_approved_candidate(
        database_url=postgres_database_url,
        applicability_expires_at_utc=expiry,
    )
    record = _load_record(postgres_database_url, candidate_id)
    authority_grant = record.review_decisions[-1].authority_grant
    assert authority_grant is not None
    conversion_key = "conversion:expiry-race:report"
    conversion_result = request_conversion_intent(
        record.candidate,
        _conversion_command(
            conversion_intent_id="postgres-expiry-race-report-001",
            target=ConversionTarget.REPORT_EVIDENCE,
            idempotency_key=conversion_key,
            candidate=record.candidate,
        ),
        accepted_at_utc=expiry - datetime.resolution,
        review_authority_grant=authority_grant,
    )
    before_counts = _tracked_counts(postgres_database_url)

    def race(
        repository: PostgresIdeaRepository,
        operation: str,
    ) -> ConversionPersistenceDecision | CandidateExpiryDecision | InvalidConversionIntent:
        if operation == "expiry":
            return expire_candidate_if_due(
                ExpireCandidateCommand(
                    candidate_id=candidate_id,
                    actor_subject="candidate-expiry-worker",
                    evaluated_at_utc=expiry,
                    reason_codes=(ReasonCode.OPPORTUNITY_NO_LONGER_ELIGIBLE,),
                ),
                repository=repository,
            ).decision
        try:
            return repository.record_conversion_intent(
                conversion_result,
                idempotency_key=conversion_key,
                payload={"conversionIntentId": "postgres-expiry-race-report-001"},
            ).decision
        except InvalidConversionIntent as exc:
            return exc

    outcomes = run_concurrent_repository_mutations(
        postgres_database_url,
        race,
        ("expiry", "conversion"),
    )
    final = _load_record(postgres_database_url, candidate_id)

    if ConversionPersistenceDecision.ACCEPTED in outcomes:
        assert CandidateExpiryDecision.TERMINAL_STATE_PRESERVED in outcomes
        assert final.candidate.lifecycle_status is IdeaLifecycleStatus.CONVERTED_TO_REPORT
        assert len(final.conversion_intents) == 1
    else:
        assert CandidateExpiryDecision.EXPIRED in outcomes
        conflict = next(
            outcome for outcome in outcomes if isinstance(outcome, InvalidConversionIntent)
        )
        assert conflict.reason == "candidate state changed after conversion readiness evaluation"
        assert final.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED
        assert final.conversion_intents == ()
    after_counts = _tracked_counts(postgres_database_url)
    for table in TRACKED_TABLES - {"idea_conversion_intent"}:
        assert after_counts[table] == before_counts[table] + 1


def _persist_approved_candidate(
    *,
    database_url: str | None = None,
    applicability_expires_at_utc: datetime | None = None,
) -> str:
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
    if applicability_expires_at_utc is not None:
        assert database_url is not None
        _set_candidate_expiry(
            database_url,
            candidate_id,
            applicability_expires_at_utc,
        )
        reset_idea_repository_for_tests(reload_from_environment=True)
    approved = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json={
            "reviewId": "postgres-conversion-fence-approval-001",
            "action": "approve_for_conversion",
            "reasonCodes": ["review_required"],
            "decidedAtUtc": "2026-06-21T10:05:00Z",
            **record_workbench_presentation(candidate_id),
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


def _set_candidate_expiry(
    database_url: str,
    candidate_id: str,
    expiry: datetime,
) -> None:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE idea_candidate_record
            SET candidate_json = jsonb_set(
                candidate_json,
                '{evidence_packet,applicability_expires_at_utc}',
                to_jsonb(%s::text),
                true
            )
            WHERE candidate_id = %s
            """,
            (expiry.isoformat(), candidate_id),
        )


def _conversion_command(
    *,
    conversion_intent_id: str,
    target: ConversionTarget,
    idempotency_key: str,
    candidate: Any,
) -> ConversionIntentCommand:
    return ConversionIntentCommand(
        conversion_intent_id=conversion_intent_id,
        target=target,
        actor_subject="advisor-001",
        idempotency_key=idempotency_key,
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        requested_at_utc=datetime(2026, 6, 21, 10, 6, tzinfo=UTC),
        expected_review_id="postgres-conversion-fence-approval-001",
        expected_candidate_evidence=CandidateEvidenceIdentity.from_candidate(candidate),
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
