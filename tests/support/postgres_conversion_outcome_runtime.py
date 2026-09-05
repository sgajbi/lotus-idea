from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row
from tests.support.http import ManagedTestClient, managed_test_client

from app.domain import (
    ConversionOutcomeCommand,
    ConversionOutcomeResult,
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    SourceSystem,
    record_conversion_outcome,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
    run_concurrent_repository_mutations,
)


_CONVERSION_OUTCOME_PROOF_TABLES = frozenset(
    {
        "idea_audit_event",
        "idea_conversion_outcome",
        "idea_outbox_event",
    }
)


def assert_postgres_conversion_outcome_identity_and_source_version_runtime_proof(
    app: Any,
    postgres_database_url: str,
) -> None:
    client = managed_test_client(app)
    intent_id = "postgres-concurrent-conversion-intent"
    intent = _persist_review_approved_conversion_intent(
        client,
        postgres_database_url,
        intent_id,
    )
    _assert_concurrent_conversion_outcome_identity_replays(postgres_database_url, intent)
    history = _conversion_outcome_history(postgres_database_url, intent_id)
    _assert_concurrent_conversion_source_version_conflict(
        postgres_database_url,
        intent,
        history,
    )


def _persist_review_approved_conversion_intent(
    client: ManagedTestClient,
    postgres_database_url: str,
    intent_id: str,
) -> GovernedConversionIntent:
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-conversion-lifecycle-persist"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    _transition_candidate_to_review_ready(client, candidate_id)
    approved = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=_approve_review_payload(),
        headers=_review_headers("postgres-conversion-lifecycle-review"),
    )
    assert approved.status_code == 200
    intent_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json={**_conversion_intent_payload(), "conversionIntentId": intent_id},
        headers=_conversion_intent_headers("postgres-conversion-lifecycle-intent"),
    )
    assert intent_response.status_code == 200
    reset_idea_repository_for_tests()
    return _conversion_intent(postgres_database_url, intent_id)


def _transition_candidate_to_review_ready(
    client: ManagedTestClient,
    candidate_id: str,
) -> None:
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        response = client.post(
            f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
            json=_lifecycle_payload(
                transition_id=f"lifecycle-{target_status}-001",
                target_status=target_status,
                changed_at_utc=f"2026-06-21T10:{index:02d}:00Z",
            ),
            headers=_lifecycle_headers(f"postgres-runtime-proof-lifecycle-{target_status}-001"),
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["durableStorageBacked"] is True
        assert payload["persistence"]["decision"] == "accepted"
        assert payload["persistence"]["lifecycleStatus"] == target_status
        reset_idea_repository_for_tests(reload_from_environment=True)


def _conversion_intent(
    postgres_database_url: str,
    intent_id: str,
) -> GovernedConversionIntent:
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        intent = repository.conversion_intent_by_id(intent_id)
    assert intent is not None
    return intent


def _assert_concurrent_conversion_outcome_identity_replays(
    postgres_database_url: str,
    intent: GovernedConversionIntent,
) -> None:
    accepted_command, accepted_result = _accepted_conversion_outcome(intent)
    before_audit = _table_count(postgres_database_url, "idea_audit_event")
    before_outbox = _table_count(postgres_database_url, "idea_outbox_event")

    identity_decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: (
            repository.record_conversion_outcome(
                accepted_result,
                idempotency_key=key,
                payload={"conversionOutcomeId": accepted_command.conversion_outcome_id},
            ).decision
        ),
        ("outcome:concurrent-identity:first", "outcome:concurrent-identity:second"),
    )

    assert set(identity_decisions) == {
        ConversionPersistenceDecision.ACCEPTED,
        ConversionPersistenceDecision.REPLAYED,
    }
    assert _table_count(postgres_database_url, "idea_conversion_outcome") == 1
    assert _table_count(postgres_database_url, "idea_audit_event") == before_audit + 1
    assert _table_count(postgres_database_url, "idea_outbox_event") == before_outbox + 1


def _accepted_conversion_outcome(
    intent: GovernedConversionIntent,
) -> tuple[ConversionOutcomeCommand, ConversionOutcomeResult]:
    accepted_command = ConversionOutcomeCommand(
        conversion_outcome_id="postgres-concurrent-outcome-v1",
        status=ConversionOutcomeStatus.ACCEPTED,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=1,
        downstream_reference="postgres-report-reference",
        recorded_at_utc=datetime(2026, 6, 21, 10, 20, tzinfo=UTC),
        actor_subject="lotus-report-worker",
    )
    return accepted_command, record_conversion_outcome(
        intent,
        accepted_command,
        accepted_at_utc=accepted_command.recorded_at_utc,
    )


def _conversion_outcome_history(
    postgres_database_url: str,
    intent_id: str,
) -> tuple[GovernedConversionOutcome, ...]:
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        return repository.conversion_outcomes_for_intent(intent_id)


def _assert_concurrent_conversion_source_version_conflict(
    postgres_database_url: str,
    intent: GovernedConversionIntent,
    history: tuple[GovernedConversionOutcome, ...],
) -> None:
    first_completion, second_completion = _conflicting_source_version_completions(
        intent,
        history,
    )
    before_audit = _table_count(postgres_database_url, "idea_audit_event")
    before_outbox = _table_count(postgres_database_url, "idea_outbox_event")

    version_decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: (
            repository.record_conversion_outcome(
                first_completion if key.endswith("first") else second_completion,
                idempotency_key=key,
                payload={"sourceEventVersion": 2},
            ).decision
        ),
        ("outcome:concurrent-version:first", "outcome:concurrent-version:second"),
    )

    assert set(version_decisions) == {
        ConversionPersistenceDecision.ACCEPTED,
        ConversionPersistenceDecision.OUTCOME_CONFLICT,
    }
    assert _table_count(postgres_database_url, "idea_conversion_outcome") == 2
    assert _table_count(postgres_database_url, "idea_audit_event") == before_audit + 1
    assert _table_count(postgres_database_url, "idea_outbox_event") == before_outbox + 1


def _conflicting_source_version_completions(
    intent: GovernedConversionIntent,
    history: tuple[GovernedConversionOutcome, ...],
) -> tuple[ConversionOutcomeResult, ConversionOutcomeResult]:
    first_command = _completed_conversion_outcome_command("postgres-concurrent-completion-a")
    second_command = _completed_conversion_outcome_command("postgres-concurrent-completion-b")
    return (
        record_conversion_outcome(
            intent,
            first_command,
            accepted_at_utc=first_command.recorded_at_utc,
            existing_outcomes=history,
        ),
        record_conversion_outcome(
            intent,
            second_command,
            accepted_at_utc=second_command.recorded_at_utc,
            existing_outcomes=history,
        ),
    )


def _completed_conversion_outcome_command(conversion_outcome_id: str) -> ConversionOutcomeCommand:
    return ConversionOutcomeCommand(
        conversion_outcome_id=conversion_outcome_id,
        status=ConversionOutcomeStatus.COMPLETED,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=2,
        downstream_reference="postgres-report-reference",
        recorded_at_utc=datetime(2026, 6, 21, 10, 21, tzinfo=UTC),
        actor_subject="lotus-report-worker",
    )


def _table_count(database_url: str, table_name: str) -> int:
    if table_name not in _CONVERSION_OUTCOME_PROOF_TABLES:
        raise ValueError(f"Unsupported conversion-outcome proof table: {table_name}")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])


def _lifecycle_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "idea-lifecycle-worker",
        "X-Caller-Capabilities": "idea.candidate.lifecycle.transition",
        "X-Correlation-Id": "corr-postgres-runtime-proof-lifecycle",
        "X-Trace-Id": "trace-postgres-runtime-proof-lifecycle",
        "Idempotency-Key": idempotency_key,
    }


def _review_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-postgres-runtime-proof-review",
        "X-Trace-Id": "trace-postgres-runtime-proof-review",
        "Idempotency-Key": idempotency_key,
    }


def _conversion_intent_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.conversion.intent.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-postgres-runtime-proof-conversion-intent",
        "X-Trace-Id": "trace-postgres-runtime-proof-conversion-intent",
        "Idempotency-Key": idempotency_key,
    }


def _lifecycle_payload(
    *,
    transition_id: str,
    target_status: str,
    changed_at_utc: str,
) -> dict[str, Any]:
    return {
        "transitionId": transition_id,
        "targetLifecycleStatus": target_status,
        "changedAtUtc": changed_at_utc,
        "reasonCodes": ["review_required"],
    }


def _approve_review_payload() -> dict[str, Any]:
    return {
        "reviewId": "review-approve-001",
        "action": "approve_for_conversion",
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
    }


def _conversion_intent_payload() -> dict[str, Any]:
    return {
        "conversionIntentId": "conversion-report-001",
        "target": "report_evidence",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }
