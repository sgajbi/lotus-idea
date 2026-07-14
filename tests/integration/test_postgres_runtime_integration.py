from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.application.source_ingestion import (
    HighCashSourceIngestionDecision,
    IngestHighCashSourceSignalCommand,
    ingest_high_cash_signal_from_core,
)
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.domain import (
    EvidenceFreshness,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    FeedbackCommand,
    FeedbackOutcome,
    ReasonCode,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewDecisionCommand,
    ReviewPersistenceDecision,
    SourceRef,
    SourceSystem,
    apply_review_action,
    record_conversion_outcome,
    record_feedback,
)
from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    MigrationExecutionPlan,
    build_migration_plan,
    execute_migration_plan,
)
from app.main import app
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
)
from app.runtime.repository_state import get_idea_repository
from tests.integration.postgres_runtime_support import (
    MIGRATIONS_DIR,
    execute_migrations,
    high_cash_payload,
    persistence_headers,
    run_concurrent_repository_mutations,
)


POSTGRES_SCHEMA_TABLES = (
    "idea_candidate_record",
    "idea_idempotency_record",
    "idea_lifecycle_history",
    "idea_audit_event",
    "idea_outbox_event",
    "idea_review_decision",
    "idea_feedback_event",
    "idea_conversion_intent",
    "idea_conversion_outcome",
    "idea_conversion_outcome_quarantine",
    "idea_report_evidence_pack_request",
    "idea_ai_explanation_lineage",
)


def test_postgres_runtime_provider_persists_api_state_across_reloaded_connections(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    headers = persistence_headers("postgres-runtime-proof-high-cash-001")
    payload = high_cash_payload()

    accepted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=payload,
        headers=headers,
    )
    reset_idea_repository_for_tests(reload_from_environment=True)
    replay_headers = {**headers, "X-Trace-Id": "trace-postgres-runtime-retry"}
    replayed = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=payload,
        headers=replay_headers,
    )

    assert accepted.status_code == 200
    assert replayed.status_code == 200
    accepted_payload = accepted.json()
    replayed_payload = replayed.json()
    assert accepted_payload["durableStorageBacked"] is True
    assert replayed_payload["durableStorageBacked"] is True
    assert accepted_payload["persistence"]["decision"] == "accepted"
    assert replayed_payload["persistence"]["decision"] == "replayed"
    assert (
        replayed_payload["persistence"]["candidateId"]
        == accepted_payload["persistence"]["candidateId"]
    )
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1
    outbox_events = tuple(get_idea_repository().snapshot().outbox_events.values())
    assert len(outbox_events) == 1
    assert outbox_events[0].correlation_id == "corr-postgres-runtime-proof"
    assert outbox_events[0].trace_id == "trace-postgres-runtime-proof"
    assert outbox_events[0].lineage_origin.value == "request"
    with psycopg.connect(postgres_database_url) as connection:
        with pytest.raises(psycopg.errors.CheckViolation):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE idea_outbox_event
                    SET causation_id = 'event-parent-invalid-for-request'
                    WHERE outbox_event_id = %s
                    """,
                    (outbox_events[0].event_id,),
                )
        connection.rollback()


def test_outbox_lineage_migration_preserves_and_sanitizes_legacy_event(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-lineage-legacy-event-001"),
    )
    assert response.status_code == 200
    event_id = next(iter(get_idea_repository().snapshot().outbox_events))
    reset_idea_repository_for_tests()
    apply_plan = build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY)
    migration = next(step for step in apply_plan.steps if step.version == "007")

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(
            cast(MigrationConnection, connection),
            MigrationExecutionPlan(direction=MigrationDirection.ROLLBACK, steps=(migration,)),
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE idea_outbox_event
                SET correlation_id = 'bearer-secret-token',
                    causation_id = 'PB_SG_GLOBAL_BAL_001'
                WHERE outbox_event_id = %s
                """,
                (event_id,),
            )
        connection.commit()
        execute_migration_plan(
            cast(MigrationConnection, connection),
            MigrationExecutionPlan(direction=MigrationDirection.APPLY, steps=(migration,)),
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT correlation_id, trace_id, causation_id, lineage_origin
                FROM idea_outbox_event
                WHERE outbox_event_id = %s
                """,
                (event_id,),
            )
            row = cursor.fetchone()

    assert row is not None
    assert row["correlation_id"].startswith("corr-system-")
    assert row["trace_id"].startswith("trace-system-")
    assert row["causation_id"] is None
    assert row["lineage_origin"] == "legacy_migrated"
    assert _table_count(postgres_database_url, "idea_outbox_event") == 1


def test_conversion_outcome_migration_quarantines_invalid_legacy_history(
    postgres_database_url: str,
) -> None:
    apply_plan = build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY)
    migration = next(step for step in apply_plan.steps if step.version == "006")
    rollback_plan = MigrationExecutionPlan(
        direction=MigrationDirection.ROLLBACK,
        steps=(migration,),
    )
    migration_apply_plan = MigrationExecutionPlan(
        direction=MigrationDirection.APPLY,
        steps=(migration,),
    )
    with psycopg.connect(postgres_database_url) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback_plan)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO idea_candidate_record (
                    candidate_id, family, lifecycle_status, review_posture,
                    evidence_packet_id, evidence_hash, candidate_json,
                    persisted_at_utc, updated_at_utc
                ) VALUES (
                    'legacy-outcome-candidate', 'high_cash', 'approved',
                    'approved_for_conversion', 'legacy-evidence', 'legacy-hash',
                    '{}'::jsonb, '2026-06-21T10:00:00Z', '2026-06-21T10:00:00Z'
                );
                INSERT INTO idea_conversion_intent (
                    conversion_intent_id, candidate_id, target, actor_subject,
                    intent_json, requested_at_utc
                ) VALUES (
                    'legacy-outcome-intent', 'legacy-outcome-candidate', 'report_evidence',
                    'legacy-worker', '{}'::jsonb, '2026-06-21T10:01:00Z'
                );
                INSERT INTO idea_conversion_outcome (
                    conversion_outcome_id, conversion_intent_id, source_system,
                    status, outcome_json, recorded_at_utc
                ) VALUES
                    (
                        'legacy-outcome-rejected', 'legacy-outcome-intent', 'lotus-report',
                        'rejected', '{}'::jsonb, '2026-06-21T10:02:00Z'
                    ),
                    (
                        'legacy-outcome-accepted', 'legacy-outcome-intent', 'lotus-report',
                        'accepted', '{}'::jsonb, '2026-06-21T10:03:00Z'
                    );
                """
            )
        connection.commit()
        execute_migration_plan(cast(MigrationConnection, connection), migration_apply_plan)
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM idea_conversion_outcome")
            active_count = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM idea_conversion_outcome_quarantine")
            quarantine_count = cursor.fetchone()
            cursor.execute(
                """
                SELECT COUNT(DISTINCT outcome.conversion_intent_id)
                FROM idea_conversion_outcome AS outcome
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM idea_conversion_outcome_quarantine AS quarantine
                    WHERE quarantine.conversion_intent_id = outcome.conversion_intent_id
                )
                """
            )
            readiness_count = cursor.fetchone()

    assert active_count == (2,)
    assert quarantine_count == (2,)
    assert readiness_count == (0,)


def test_postgres_migration_rollback_and_reapply_restores_runtime_contract(
    postgres_database_url: str,
) -> None:
    assert _schema_tables_exist(postgres_database_url) is True

    execute_migrations(postgres_database_url, MigrationDirection.ROLLBACK)
    assert _schema_tables_exist(postgres_database_url) is False

    execute_migrations(postgres_database_url, MigrationDirection.APPLY)
    assert _schema_tables_exist(postgres_database_url) is True

    reset_idea_repository_for_tests(reload_from_environment=True)
    client = TestClient(app)
    recovered = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-runtime-proof-recovery-001"),
    )

    assert recovered.status_code == 200
    recovered_payload = recovered.json()
    assert recovered_payload["durableStorageBacked"] is True
    assert recovered_payload["persistence"]["decision"] == "accepted"
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1


def test_postgres_runtime_provider_recovers_source_ingestion_replay_and_conflict(
    postgres_database_url: str,
) -> None:
    source = RecordingCoreSource(evidence=_core_high_cash_evidence())
    first = ingest_high_cash_signal_from_core(
        _source_ingestion_command(),
        core_source=source,
        repository=get_idea_repository(),
    )

    assert first.decision is HighCashSourceIngestionDecision.ACCEPTED
    assert first.signal_result.persistence is not None
    assert first.signal_result.persistence.record is not None
    candidate_id = first.signal_result.persistence.record.candidate.candidate_id
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = ingest_high_cash_signal_from_core(
        _source_ingestion_command(),
        core_source=source,
        repository=get_idea_repository(),
    )

    assert replayed.decision is HighCashSourceIngestionDecision.REPLAYED
    assert replayed.signal_result.persistence is not None
    assert replayed.signal_result.persistence.record is not None
    assert replayed.signal_result.persistence.record.candidate.candidate_id == candidate_id
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1

    source.evidence = _core_high_cash_evidence(holdings_hash="sha256:changed-holdings")
    reset_idea_repository_for_tests(reload_from_environment=True)
    conflict = ingest_high_cash_signal_from_core(
        _source_ingestion_command(),
        core_source=source,
        repository=get_idea_repository(),
    )

    assert conflict.decision is HighCashSourceIngestionDecision.CONFLICT
    assert conflict.signal_result.persistence is not None
    assert conflict.signal_result.persistence.record is not None
    assert conflict.signal_result.persistence.record.candidate.candidate_id == candidate_id
    assert conflict.signal_result.persistence.audit_event is None
    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_idempotency_record") == 1


def test_postgres_runtime_provider_persists_review_conversion_and_report_workflow(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    persist_headers = persistence_headers("postgres-runtime-proof-workflow-persist-001")
    high_cash_request = high_cash_payload()

    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_request,
        headers=persist_headers,
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])

    reset_idea_repository_for_tests(reload_from_environment=True)
    queue = client.get(
        "/api/v1/review-queues/advisor",
        params={"evaluatedAtUtc": "2026-06-21T10:10:00Z"},
        headers=_review_queue_headers(),
    )
    assert queue.status_code == 200
    queue_payload = queue.json()
    assert queue_payload["durableStorageBacked"] is True
    assert queue_payload["items"][0]["candidate"]["candidateId"] == candidate_id

    _transition_candidate_to_review_ready(client, candidate_id)
    review_headers = _review_headers("postgres-runtime-proof-review-approve-001")
    review_payload = _approve_review_payload()
    review = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=review_payload,
        headers=review_headers,
    )
    assert review.status_code == 200
    review_payload_response = review.json()
    assert review_payload_response["durableStorageBacked"] is True
    assert review_payload_response["persistence"]["decision"] == "accepted"
    assert review_payload_response["persistence"]["lifecycleStatus"] == "approved"
    assert review_payload_response["persistence"]["reviewPosture"] == "approved_for_conversion"

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_review = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=review_payload,
        headers=review_headers,
    )
    assert replayed_review.status_code == 200
    assert replayed_review.json()["durableStorageBacked"] is True
    assert replayed_review.json()["persistence"]["decision"] == "replayed"

    feedback = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=_feedback_payload(),
        headers=_feedback_headers("postgres-runtime-proof-feedback-001"),
    )
    assert feedback.status_code == 200
    assert feedback.json()["durableStorageBacked"] is True
    assert feedback.json()["persistence"]["decision"] == "accepted"

    reset_idea_repository_for_tests(reload_from_environment=True)
    conversion_headers = _conversion_intent_headers("postgres-runtime-proof-conversion-intent-001")
    conversion_payload = _conversion_intent_payload()
    conversion = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_payload,
        headers=conversion_headers,
    )
    assert conversion.status_code == 200
    conversion_response = conversion.json()
    assert conversion_response["durableStorageBacked"] is True
    assert conversion_response["persistence"]["decision"] == "accepted"
    assert conversion_response["persistence"]["lifecycleStatus"] == "converted_to_report"

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_conversion = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_payload,
        headers=conversion_headers,
    )
    assert replayed_conversion.status_code == 200
    assert replayed_conversion.json()["durableStorageBacked"] is True
    assert replayed_conversion.json()["persistence"]["decision"] == "replayed"

    outcome = client.post(
        "/api/v1/conversion-intents/conversion-report-001/outcomes",
        json=_conversion_outcome_payload(),
        headers=_conversion_outcome_headers("postgres-runtime-proof-conversion-outcome-001"),
    )
    assert outcome.status_code == 200
    assert outcome.json()["durableStorageBacked"] is True
    assert outcome.json()["persistence"]["decision"] == "accepted"

    reset_idea_repository_for_tests(reload_from_environment=True)
    report_headers = _report_evidence_pack_headers(
        "postgres-runtime-proof-report-evidence-pack-001"
    )
    report_payload = _report_evidence_pack_payload()
    report_pack = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json=report_payload,
        headers=report_headers,
    )
    assert report_pack.status_code == 200
    report_response = report_pack.json()
    assert report_response["durableStorageBacked"] is True
    assert report_response["persistence"]["decision"] == "accepted"
    assert report_response["reportEvidencePack"]["candidateId"] == candidate_id
    assert report_response["reportEvidencePack"]["createsRenderedOutput"] is False
    assert report_response["reportEvidencePack"]["createsArchiveRecord"] is False

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed_report_pack = client.post(
        "/api/v1/conversion-intents/conversion-report-001/report-evidence-packs",
        json=report_payload,
        headers=report_headers,
    )
    assert replayed_report_pack.status_code == 200
    assert replayed_report_pack.json()["durableStorageBacked"] is True
    assert replayed_report_pack.json()["persistence"]["decision"] == "replayed"

    assert _table_count(postgres_database_url, "idea_candidate_record") == 1
    assert _table_count(postgres_database_url, "idea_review_decision") == 1
    assert _table_count(postgres_database_url, "idea_feedback_event") == 1
    assert _table_count(postgres_database_url, "idea_conversion_intent") == 1
    assert _table_count(postgres_database_url, "idea_conversion_outcome") == 1
    assert _table_count(postgres_database_url, "idea_report_evidence_pack_request") == 1
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT event_type, correlation_id, trace_id, lineage_origin
                FROM idea_outbox_event
                ORDER BY occurred_at_utc, outbox_event_id
                """
            )
            lineage_rows = cursor.fetchall()

    expected_lineage = {
        "idea.candidate.persisted.v1": (
            "corr-postgres-runtime-proof",
            "trace-postgres-runtime-proof",
        ),
        "idea.lifecycle.transitioned.v1": (
            "corr-postgres-runtime-proof-lifecycle",
            "trace-postgres-runtime-proof-lifecycle",
        ),
        "idea.review.decision_recorded.v1": (
            "corr-postgres-runtime-proof-review",
            "trace-postgres-runtime-proof-review",
        ),
        "idea.feedback.recorded.v1": (
            "corr-postgres-runtime-proof-feedback",
            "trace-postgres-runtime-proof-feedback",
        ),
        "idea.conversion.intent_requested.v1": (
            "corr-postgres-runtime-proof-conversion-intent",
            "trace-postgres-runtime-proof-conversion-intent",
        ),
        "idea.conversion.outcome_recorded.v1": (
            "corr-postgres-runtime-proof-conversion-outcome",
            "trace-postgres-runtime-proof-conversion-outcome",
        ),
        "idea.report_evidence_pack.requested.v1": (
            "corr-postgres-runtime-proof-report-pack",
            "trace-postgres-runtime-proof-report-pack",
        ),
    }
    assert set(expected_lineage).issubset({row["event_type"] for row in lineage_rows})
    for row in lineage_rows:
        expected = expected_lineage.get(row["event_type"])
        if expected is not None:
            assert (row["correlation_id"], row["trace_id"]) == expected
            assert row["lineage_origin"] == "request"


def test_postgres_runtime_serializes_concurrent_review_and_feedback_resource_identity(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-runtime-identity-persist-001"),
    )
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    _transition_candidate_to_review_ready(client, candidate_id)
    reset_idea_repository_for_tests()

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        record = PostgresIdeaRepository(cast(Any, connection)).candidate_record_by_id(candidate_id)
    assert record is not None
    candidate = record.candidate
    scope = candidate.access_scope
    assert scope is not None
    actor = ReviewActorContext(
        actor_subject="advisor-001",
        role=ReviewActorRole.ADVISOR,
        tenant_ids=frozenset({scope.tenant_id}),
        book_ids=frozenset({scope.book_id}),
        portfolio_ids=frozenset({scope.portfolio_id}),
        client_ids=frozenset({scope.client_id}),
    )
    review = apply_review_action(
        candidate,
        ReviewDecisionCommand(
            review_id="postgres-concurrent-review-identity-001",
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            actor=actor,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            decided_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
        ),
    )
    before_audit = _table_count(postgres_database_url, "idea_audit_event")
    before_outbox = _table_count(postgres_database_url, "idea_outbox_event")

    review_decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: (
            repository.record_review_action(
                review,
                idempotency_key=key,
                payload={"reviewId": review.decision.review_id},
            ).decision
        ),
        ("review:concurrent:first", "review:concurrent:second"),
    )

    assert set(review_decisions) == {
        ReviewPersistenceDecision.ACCEPTED,
        ReviewPersistenceDecision.REPLAYED,
    }
    assert _table_count(postgres_database_url, "idea_review_decision") == 1
    assert _table_count(postgres_database_url, "idea_audit_event") == before_audit + 1
    assert _table_count(postgres_database_url, "idea_outbox_event") == before_outbox + 1

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        approved = PostgresIdeaRepository(cast(Any, connection)).candidate_record_by_id(
            candidate_id
        )
    assert approved is not None
    feedback = record_feedback(
        approved.candidate,
        FeedbackCommand(
            feedback_id="postgres-concurrent-feedback-identity-001",
            actor=actor,
            outcome=FeedbackOutcome.USEFUL,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            recorded_at_utc=datetime(2026, 6, 21, 10, 6, tzinfo=UTC),
        ),
    )
    before_audit = _table_count(postgres_database_url, "idea_audit_event")
    before_outbox = _table_count(postgres_database_url, "idea_outbox_event")

    feedback_decisions = run_concurrent_repository_mutations(
        postgres_database_url,
        lambda repository, key: (
            repository.record_feedback_event(
                feedback,
                idempotency_key=key,
                payload={"feedbackId": feedback.feedback_event.feedback.feedback_id},
            ).decision
        ),
        ("feedback:concurrent:first", "feedback:concurrent:second"),
    )

    assert set(feedback_decisions) == {
        ReviewPersistenceDecision.ACCEPTED,
        ReviewPersistenceDecision.REPLAYED,
    }
    assert _table_count(postgres_database_url, "idea_feedback_event") == 1
    assert _table_count(postgres_database_url, "idea_audit_event") == before_audit + 1
    assert _table_count(postgres_database_url, "idea_outbox_event") == before_outbox + 1


def test_postgres_runtime_serializes_conversion_outcome_identity_and_source_version(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-conversion-lifecycle-persist"),
    )
    candidate_id = str(persisted.json()["persistence"]["candidateId"])
    _transition_candidate_to_review_ready(client, candidate_id)
    approved = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=_approve_review_payload(),
        headers=_review_headers("postgres-conversion-lifecycle-review"),
    )
    assert approved.status_code == 200
    intent_id = "postgres-concurrent-conversion-intent"
    intent_response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json={**_conversion_intent_payload(), "conversionIntentId": intent_id},
        headers=_conversion_intent_headers("postgres-conversion-lifecycle-intent"),
    )
    assert intent_response.status_code == 200
    reset_idea_repository_for_tests()

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        intent = repository.conversion_intent_by_id(intent_id)
    assert intent is not None
    accepted_command = ConversionOutcomeCommand(
        conversion_outcome_id="postgres-concurrent-outcome-v1",
        status=ConversionOutcomeStatus.ACCEPTED,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=1,
        downstream_reference="postgres-report-reference",
        recorded_at_utc=datetime(2026, 6, 21, 10, 20, tzinfo=UTC),
        actor_subject="lotus-report-worker",
    )
    accepted_result = record_conversion_outcome(intent, accepted_command)
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

    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        repository = PostgresIdeaRepository(cast(Any, connection))
        history = repository.conversion_outcomes_for_intent(intent_id)
    first_completion = record_conversion_outcome(
        intent,
        ConversionOutcomeCommand(
            conversion_outcome_id="postgres-concurrent-completion-a",
            status=ConversionOutcomeStatus.COMPLETED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=2,
            downstream_reference="postgres-report-reference",
            recorded_at_utc=datetime(2026, 6, 21, 10, 21, tzinfo=UTC),
            actor_subject="lotus-report-worker",
        ),
        existing_outcomes=history,
    )
    second_completion = record_conversion_outcome(
        intent,
        ConversionOutcomeCommand(
            conversion_outcome_id="postgres-concurrent-completion-b",
            status=ConversionOutcomeStatus.COMPLETED,
            source_system=SourceSystem.LOTUS_REPORT,
            source_event_version=2,
            downstream_reference="postgres-report-reference",
            recorded_at_utc=datetime(2026, 6, 21, 10, 21, tzinfo=UTC),
            actor_subject="lotus-report-worker",
        ),
        existing_outcomes=history,
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


def test_postgres_runtime_provider_persists_ai_explanation_lineage(
    postgres_database_url: str,
) -> None:
    client = TestClient(app)
    persisted = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=high_cash_payload(),
        headers=persistence_headers("postgres-runtime-proof-ai-lineage-seed-001"),
    )
    assert persisted.status_code == 200
    candidate_id = str(persisted.json()["persistence"]["candidateId"])

    request_payload = _ai_explanation_payload(request_id="postgres-runtime-proof-ai-lineage-001")
    reset_idea_repository_for_tests(reload_from_environment=True)
    accepted = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=request_payload,
        headers=_ai_explanation_headers("postgres-runtime-proof-ai-lineage-write-001"),
    )

    assert accepted.status_code == 200
    accepted_payload = accepted.json()
    assert accepted_payload["durableStorageBacked"] is True
    assert accepted_payload["aiLineageRecorded"] is True
    assert accepted_payload["aiLineagePersistenceDecision"] == "accepted"
    assert accepted_payload["outputIntegrityVersion"] == "lotus-idea.ai-output-integrity.v1"
    assert accepted_payload["outputContentDigest"].startswith("sha256:")
    assert accepted_payload["executionProvenancePosture"] == "not_applicable_fallback"
    assert accepted_payload["lotusAiRuntimeExecuted"] is False
    assert accepted_payload["supportedFeaturePromoted"] is False
    assert _table_count(postgres_database_url, "idea_ai_explanation_lineage") == 1

    reset_idea_repository_for_tests(reload_from_environment=True)
    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=request_payload,
        headers=_ai_explanation_headers("postgres-runtime-proof-ai-lineage-write-001"),
    )

    assert replayed.status_code == 200
    replayed_payload = replayed.json()
    assert replayed_payload["durableStorageBacked"] is True
    assert replayed_payload["aiLineageRecorded"] is True
    assert replayed_payload["aiLineagePersistenceDecision"] == "replayed"
    assert _table_count(postgres_database_url, "idea_ai_explanation_lineage") == 1

    changed_payload = dict(request_payload)
    changed_payload["fallbackReason"] = "workflow_not_approved"
    reset_idea_repository_for_tests(reload_from_environment=True)
    conflict = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=changed_payload,
        headers=_ai_explanation_headers("postgres-runtime-proof-ai-lineage-write-002"),
    )

    assert conflict.status_code == 409
    assert conflict.json()["code"] == "ai_explanation_lineage_conflict"
    assert "workflow_not_approved" not in conflict.text
    assert _table_count(postgres_database_url, "idea_ai_explanation_lineage") == 1

    lineage_row = _ai_lineage_row(postgres_database_url)
    assert lineage_row["ai_explanation_request_id"] == "postgres-runtime-proof-ai-lineage-001"
    assert lineage_row["candidate_id"] == candidate_id
    lineage_json = lineage_row["lineage_json"]
    assert lineage_json["request_id"] == "postgres-runtime-proof-ai-lineage-001"
    assert lineage_json["candidate_id"] == candidate_id
    assert lineage_json["fallback_used"] is True
    assert lineage_json["fallback_reason"] == "ai_unavailable"
    assert lineage_row["output_integrity_version"] == accepted_payload["outputIntegrityVersion"]
    assert lineage_row["output_content_digest"] == accepted_payload["outputContentDigest"]
    assert lineage_json["output_integrity_version"] == lineage_row["output_integrity_version"]
    assert lineage_json["output_content_digest"] == lineage_row["output_content_digest"]
    assert (
        lineage_row["execution_provenance_posture"]
        == (accepted_payload["executionProvenancePosture"])
    )
    assert (
        lineage_json["execution_provenance_posture"]
        == (lineage_row["execution_provenance_posture"])
    )
    assert lineage_json["grants_downstream_authority"] is False
    assert "portfolio_id" not in lineage_json
    assert "client_id" not in lineage_json
    assert "prompt" not in lineage_json
    assert "provider_payload" not in lineage_json


def _table_count(database_url: str, table_name: str) -> int:
    if table_name not in POSTGRES_SCHEMA_TABLES:
        raise ValueError(f"Unsupported test table: {table_name}")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row = cursor.fetchone()
    if row is None:
        raise AssertionError(f"No count returned for {table_name}")
    return int(row[0])


def _ai_lineage_row(database_url: str) -> dict[str, Any]:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT ai_explanation_request_id, candidate_id,
                       output_integrity_version, output_content_digest,
                       execution_provenance_posture, lineage_json
                FROM idea_ai_explanation_lineage
                """
            )
            row = cursor.fetchone()
    if row is None:
        raise AssertionError("No AI explanation lineage row returned")
    return {
        "ai_explanation_request_id": str(row[0]),
        "candidate_id": str(row[1]),
        "output_integrity_version": str(row[2]),
        "output_content_digest": str(row[3]),
        "execution_provenance_posture": str(row[4]),
        "lineage_json": row[5],
    }


def _schema_tables_exist(database_url: str) -> bool:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                """,
                (list(POSTGRES_SCHEMA_TABLES),),
            )
            existing_tables = {str(row[0]) for row in cursor.fetchall()}
    return existing_tables == set(POSTGRES_SCHEMA_TABLES)


@dataclass
class RecordingCoreSource(CoreOpportunitySourcePort):
    evidence: CoreHighCashEvidence
    seen_request: CoreHighCashEvidenceRequest | None = None

    def fetch_high_cash_evidence(
        self, request: CoreHighCashEvidenceRequest
    ) -> CoreHighCashEvidence:
        self.seen_request = request
        return self.evidence


def _source_ingestion_command() -> IngestHighCashSourceSignalCommand:
    return IngestHighCashSourceSignalCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        tenant_id="tenant-a",
        as_of_date=date(2026, 6, 21),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        idempotency_key="signal-ingestion:high-cash:lotus-core:postgres-recovery-001",
        correlation_id="corr-postgres-source-ingestion-proof",
        trace_id="trace-postgres-source-ingestion-proof",
    )


def _core_high_cash_evidence(
    *,
    holdings_hash: str = "sha256:lotus-core:HoldingsAsOf:v1",
) -> CoreHighCashEvidence:
    return CoreHighCashEvidence(
        source_reported_cash_weight=Decimal("0.18"),
        portfolio_state_ref=_core_source_ref("lotus-core:PortfolioStateSnapshot:v1"),
        holdings_ref=_core_source_ref("lotus-core:HoldingsAsOf:v1", content_hash=holdings_hash),
        cash_movement_ref=_core_source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
        cashflow_projection_ref=_core_source_ref("lotus-core:PortfolioCashflowProjection:v1"),
    )


def _core_source_ref(product_id: str, *, content_hash: str | None = None) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=f"/source/{product_id}",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        content_hash=content_hash or f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def _review_queue_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.queue.read",
        "X-Correlation-Id": "corr-postgres-runtime-proof-queue",
    }


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


def _feedback_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.feedback.record",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
        "X-Correlation-Id": "corr-postgres-runtime-proof-feedback",
        "X-Trace-Id": "trace-postgres-runtime-proof-feedback",
        "Idempotency-Key": idempotency_key,
    }


def _conversion_intent_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.conversion.intent.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-conversion-intent",
        "X-Trace-Id": "trace-postgres-runtime-proof-conversion-intent",
        "Idempotency-Key": idempotency_key,
    }


def _conversion_outcome_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "lotus-report-worker",
        "X-Caller-Capabilities": "idea.conversion.outcome.record",
        "X-Correlation-Id": "corr-postgres-runtime-proof-conversion-outcome",
        "X-Trace-Id": "trace-postgres-runtime-proof-conversion-outcome",
        "Idempotency-Key": idempotency_key,
    }


def _report_evidence_pack_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Capabilities": "idea.report-evidence-pack.request",
        "X-Correlation-Id": "corr-postgres-runtime-proof-report-pack",
        "X-Trace-Id": "trace-postgres-runtime-proof-report-pack",
        "Idempotency-Key": idempotency_key,
    }


def _ai_explanation_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.ai-explanation.evaluate",
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Correlation-Id": "corr-postgres-runtime-proof-ai-lineage",
        "Idempotency-Key": idempotency_key,
    }


def _ai_explanation_payload(*, request_id: str) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "workflowPack": {
            "workflowPackId": "lotus-ai:idea-explanation:v1",
            "workflowPackVersion": "v1",
            "purpose": "missing_evidence_check",
            "evaluationRef": "lotus-ai:governed-verifier:v1",
        },
        "approvedMetadata": {"channel": "advisor-workbench"},
        "requestedAtUtc": "2026-06-21T10:12:00Z",
        "fallbackReason": "ai_unavailable",
    }


def _access_scope() -> dict[str, str]:
    return {
        "tenantId": "tenant-private-bank-sg",
        "bookId": "book-advisor-001",
        "portfolioId": "PB_SG_GLOBAL_BAL_001",
        "clientId": "client-001",
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


def _feedback_payload() -> dict[str, Any]:
    return {
        "feedbackId": "feedback-useful-001",
        "outcome": "useful",
        "reasonCodes": ["review_required"],
        "recordedAtUtc": "2026-06-21T10:06:00Z",
    }


def _conversion_intent_payload() -> dict[str, Any]:
    return {
        "conversionIntentId": "conversion-report-001",
        "target": "report_evidence",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:15:00Z",
    }


def _conversion_outcome_payload() -> dict[str, Any]:
    return {
        "conversionOutcomeId": "conversion-report-outcome-001",
        "sourceEventVersion": 1,
        "status": "accepted",
        "sourceSystem": "lotus-report",
        "downstreamReference": "report-evidence-pack-001",
        "recordedAtUtc": "2026-06-21T10:20:00Z",
    }


def _report_evidence_pack_payload() -> dict[str, Any]:
    return {
        "reportEvidencePackId": "report-evidence-pack-001",
        "purpose": "client_review_report_section",
        "reasonCodes": ["review_approved_for_conversion"],
        "requestedAtUtc": "2026-06-21T10:25:00Z",
        "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
        "clientReadyPublicationRequested": False,
    }


def _transition_candidate_to_review_ready(client: TestClient, candidate_id: str) -> None:
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
