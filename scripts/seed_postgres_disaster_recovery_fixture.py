from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
from typing import Any, cast

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.domain import (  # noqa: E402
    AIFallbackReason,
    AIExplanationCommand,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReviewPosture,
    SourceSystem,
    apply_review_action,
    build_ai_explanation_request,
    create_downstream_submission_claim,
    deterministic_ai_fallback,
    outbox_dead_letter_support_reference,
    outbox_recovery_request_payload,
    record_conversion_outcome,
    record_feedback,
    request_conversion_intent,
    request_report_evidence_pack,
)
from app.infrastructure.postgres_protocols import PostgresConnection  # noqa: E402
from app.infrastructure.postgres_repository import PostgresIdeaRepository  # noqa: E402
from scripts.postgres_disaster_recovery_fixture_data import (  # noqa: E402
    FIXTURE_CANDIDATE_PREFIX,
    FIXTURE_TIME,
    conversion_command,
    conversion_outcome_command,
    feedback_command,
    high_cash_candidate,
    report_pack_command,
    review_command,
)

DATABASE_URL_ENV = "LOTUS_IDEA_DR_SOURCE_DATABASE_URL"


def seed_disaster_recovery_fixture(
    database_url: str,
    *,
    confirm_disposable_database: bool,
) -> dict[str, int]:
    if not confirm_disposable_database:
        raise ValueError("explicit disposable-database confirmation is required")
    if not database_url.strip():
        raise ValueError("database_url is required")
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        typed_connection = cast(PostgresConnection, connection)
        _assert_empty_migrated_database(typed_connection)
        repository = PostgresIdeaRepository(typed_connection)
        review_ready, approved = _seed_workflow_records(repository)
        _seed_ai_lineage(repository, review_ready)
        _seed_downstream_submissions(repository)
        recovery_event_id = _seed_outbox_delivery_states(typed_connection)
        _seed_outbox_recovery(repository, recovery_event_id)
        _validate_runtime_rehydration(repository)
        return _table_counts(typed_connection)


def _assert_empty_migrated_database(connection: PostgresConnection) -> None:
    with connection.cursor() as cursor:
        database_cursor = cast(Any, cursor)
        database_cursor.execute(
            """SELECT COUNT(*) AS table_count FROM pg_catalog.pg_tables
               WHERE schemaname = 'public' AND tablename LIKE 'idea\\_%' ESCAPE '\\'"""
        )
        if int(database_cursor.fetchone()["table_count"]) != 15:
            raise ValueError("all current Lotus Idea migrations must be applied before seeding")
        database_cursor.execute(
            """SELECT
                   (SELECT COUNT(*) FROM idea_candidate_record)
                 + (SELECT COUNT(*) FROM idea_outbox_event)
                 + (SELECT COUNT(*) FROM idea_downstream_submission) AS existing_count"""
        )
        if int(database_cursor.fetchone()["existing_count"]):
            raise ValueError("disaster recovery fixture requires an empty disposable database")


def _seed_workflow_records(
    repository: PostgresIdeaRepository,
) -> tuple[IdeaCandidate, IdeaCandidate]:
    base = high_cash_candidate()
    review_ready = replace(
        base,
        candidate_id=f"{FIXTURE_CANDIDATE_PREFIX}_review",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    approved = replace(
        base,
        candidate_id=f"{FIXTURE_CANDIDATE_PREFIX}_conversion",
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    _persist_candidate(repository, review_ready, "dr-fixture-review")
    _persist_candidate(repository, approved, "dr-fixture-conversion")

    lifecycle = repository.record_lifecycle_transition(
        review_ready.candidate_id,
        IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
        idempotency_key="dr-fixture-lifecycle",
        payload={"candidateId": review_ready.candidate_id, "target": "reviewed_by_advisor"},
        actor_subject="dr-fixture-advisor",
        occurred_at_utc=FIXTURE_TIME + timedelta(minutes=1),
        transition_id="dr-fixture-transition-001",
        reason_codes=("review_required",),
    )
    if lifecycle.record is None:
        raise RuntimeError("fixture lifecycle transition was not persisted")
    review_result = apply_review_action(lifecycle.record.candidate, review_command())
    review = repository.record_review_action(
        review_result,
        idempotency_key="dr-fixture-review-action",
        payload={"reviewId": review_result.decision.review_id},
    )
    if review.record is None:
        raise RuntimeError("fixture review decision was not persisted")
    feedback_result = record_feedback(review.record.candidate, feedback_command())
    repository.record_feedback_event(
        feedback_result,
        idempotency_key="dr-fixture-feedback",
        payload={"feedbackId": feedback_result.feedback_event.feedback.feedback_id},
    )

    conversion_result = request_conversion_intent(approved, conversion_command())
    conversion = repository.record_conversion_intent(
        conversion_result,
        idempotency_key="dr-fixture-conversion-intent",
        payload={
            "conversionIntentId": conversion_result.conversion_intent.intent.conversion_intent_id
        },
    )
    if conversion.record is None:
        raise RuntimeError("fixture conversion intent was not persisted")
    outcome_result = record_conversion_outcome(
        conversion_result.conversion_intent,
        conversion_outcome_command(),
    )
    repository.record_conversion_outcome(
        outcome_result,
        idempotency_key="dr-fixture-conversion-outcome",
        payload={
            "conversionOutcomeId": outcome_result.conversion_outcome.outcome.conversion_outcome_id
        },
    )
    pack_result = request_report_evidence_pack(
        conversion.record.candidate,
        conversion_result.conversion_intent,
        report_pack_command(),
    )
    repository.record_report_evidence_pack(
        pack_result,
        idempotency_key="dr-fixture-report-pack",
        payload={"reportEvidencePackId": pack_result.evidence_pack.report_evidence_pack_id},
    )
    return review_ready, approved


def _persist_candidate(
    repository: PostgresIdeaRepository, candidate: IdeaCandidate, idempotency_key: str
) -> None:
    result = repository.persist_candidate(
        candidate,
        idempotency_key=idempotency_key,
        payload={"candidateId": candidate.candidate_id},
        actor_subject="dr-fixture-ingestion-worker",
        occurred_at_utc=FIXTURE_TIME,
    )
    if result.record is None:
        raise RuntimeError("fixture candidate was not persisted")


def _seed_ai_lineage(repository: PostgresIdeaRepository, candidate: IdeaCandidate) -> None:
    request = build_ai_explanation_request(
        candidate,
        AIExplanationCommand(
            request_id="dr-fixture-ai-request-001",
            actor_subject="dr-fixture-advisor",
            workflow_pack=AIWorkflowPackRef(
                workflow_pack_id="lotus-ai:idea-explanation:v1",
                workflow_pack_version="v1",
                purpose=AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
                evaluation_ref="lotus-ai:governed-verifier:v1",
            ),
            approved_metadata={"audience": "internal_advisor_review"},
            requested_at_utc=FIXTURE_TIME + timedelta(minutes=10),
        ),
    )
    result = deterministic_ai_fallback(
        request,
        fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        occurred_at_utc=FIXTURE_TIME + timedelta(minutes=10),
    )
    repository.record_ai_explanation_lineage(result)


def _seed_downstream_submissions(repository: PostgresIdeaRepository) -> None:
    conversion_claim = create_downstream_submission_claim(
        idempotency_key="dr-fixture-downstream-conversion",
        request_fingerprint="sha256:dr-fixture-downstream-conversion",
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id="dr-fixture-conversion-intent-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        actor_subject="dr-fixture-realization-worker",
        claimed_at_utc=FIXTURE_TIME + timedelta(minutes=12),
        lease_owner="dr-fixture-realization-worker",
        lease_attempt_id="dr-fixture-downstream-attempt-001",
        lease_expires_at_utc=FIXTURE_TIME + timedelta(minutes=17),
        correlation_id="corr-dr-fixture-downstream-001",
        trace_id="trace-dr-fixture-downstream-001",
    )
    repository.claim_downstream_submission(conversion_claim)

    report_claim = create_downstream_submission_claim(
        idempotency_key="dr-fixture-downstream-report",
        request_fingerprint="sha256:dr-fixture-downstream-report",
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id="dr-fixture-report-pack-001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=SourceSystem.LOTUS_REPORT,
        actor_subject="dr-fixture-realization-worker",
        claimed_at_utc=FIXTURE_TIME + timedelta(minutes=13),
        lease_owner="dr-fixture-realization-worker",
        lease_attempt_id="dr-fixture-downstream-attempt-002",
        lease_expires_at_utc=FIXTURE_TIME + timedelta(minutes=18),
        correlation_id="corr-dr-fixture-downstream-002",
        trace_id="trace-dr-fixture-downstream-002",
    )
    repository.claim_downstream_submission(report_claim)
    repository.finalize_downstream_submission(
        idempotency_key=report_claim.idempotency_key,
        lease_owner=report_claim.lease_owner or "",
        lease_attempt_id=report_claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=FIXTURE_TIME + timedelta(minutes=14),
        failure_reason="dr_fixture_commit_outcome_unknown",
    )


def _seed_outbox_delivery_states(connection: PostgresConnection) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT outbox_event_id FROM idea_outbox_event ORDER BY occurred_at_utc, outbox_event_id"
        )
        event_ids = [str(row["outbox_event_id"]) for row in cursor.fetchall()]
        if len(event_ids) < 6:
            raise RuntimeError("fixture requires at least six generated outbox events")
        published, failed, dead_letter, leased, recovery, _pending = event_ids[:6]
        cursor.execute(
            """UPDATE idea_outbox_event
               SET status = 'published', published_at_utc = %s
               WHERE outbox_event_id = %s""",
            (FIXTURE_TIME + timedelta(minutes=20), published),
        )
        cursor.execute(
            """UPDATE idea_outbox_event
               SET status = 'failed', failure_reason = 'dr_fixture_retryable_failure',
                   retry_count = 1, first_failed_at_utc = %s, last_failed_at_utc = %s,
                   next_attempt_at_utc = %s
               WHERE outbox_event_id = %s""",
            (
                FIXTURE_TIME + timedelta(minutes=20),
                FIXTURE_TIME + timedelta(minutes=21),
                FIXTURE_TIME + timedelta(minutes=25),
                failed,
            ),
        )
        for event_id in (dead_letter, recovery):
            cursor.execute(
                """UPDATE idea_outbox_event
                   SET status = 'dead_letter', failure_reason = 'dr_fixture_terminal_failure',
                       retry_count = 3, first_failed_at_utc = %s, last_failed_at_utc = %s
                   WHERE outbox_event_id = %s""",
                (
                    FIXTURE_TIME + timedelta(minutes=20),
                    FIXTURE_TIME + timedelta(minutes=22),
                    event_id,
                ),
            )
        cursor.execute(
            """UPDATE idea_outbox_event
               SET status = 'leased', lease_owner = 'dr-fixture-outbox-worker',
                   lease_attempt_id = 'dr-fixture-outbox-attempt-001',
                   lease_expires_at_utc = %s
               WHERE outbox_event_id = %s""",
            (FIXTURE_TIME + timedelta(minutes=30), leased),
        )
    connection.commit()
    return recovery


def _seed_outbox_recovery(repository: PostgresIdeaRepository, event_id: str) -> None:
    support_reference = outbox_dead_letter_support_reference(event_id)
    request_payload = outbox_recovery_request_payload(
        support_reference=support_reference,
        reason="provider incident replay authorization",
        change_reference="CHG-DR-FIXTURE-001",
        actor_subject="dr-fixture-operator",
    )
    claim = repository.claim_dead_letter_for_recovery(
        support_reference=support_reference,
        idempotency_key="dr-fixture-outbox-recovery-001",
        request_payload=request_payload,
        actor_subject="dr-fixture-operator",
        reason="provider incident replay authorization",
        change_reference="CHG-DR-FIXTURE-001",
        requested_at_utc=FIXTURE_TIME + timedelta(minutes=23),
        lease_owner="dr-fixture-recovery-worker",
        lease_attempt_id="dr-fixture-recovery-attempt-001",
        lease_expires_at_utc=FIXTURE_TIME + timedelta(minutes=28),
    )
    if claim.audit_record is None:
        raise RuntimeError("fixture outbox recovery audit was not persisted")


def _validate_runtime_rehydration(repository: PostgresIdeaRepository) -> None:
    snapshot = repository.snapshot()
    if len(snapshot.candidate_records) != 2:
        raise RuntimeError("fixture candidate rehydration failed")
    if len(snapshot.outbox_events) < 8:
        raise RuntimeError("fixture outbox rehydration failed")
    if len(repository.outbox_recovery_audit_records()) != 1:
        raise RuntimeError("fixture recovery audit rehydration failed")


def _table_counts(connection: PostgresConnection) -> dict[str, int]:
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        database_cursor = cast(Any, cursor)
        database_cursor.execute(
            """SELECT tablename FROM pg_catalog.pg_tables
               WHERE schemaname = 'public' AND tablename LIKE 'idea\\_%' ESCAPE '\\'
               ORDER BY tablename"""
        )
        for row in database_cursor.fetchall():
            table = str(row["tablename"])
            database_cursor.execute(
                sql.SQL("SELECT COUNT(*) AS row_count FROM {}").format(sql.Identifier(table))
            )
            counts[table] = int(database_cursor.fetchone()["row_count"])
    return counts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a disposable PostgreSQL database for Lotus Idea restore proof"
    )
    parser.add_argument("--confirm-disposable-database", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    database_url = os.getenv(DATABASE_URL_ENV, "").strip()
    if not database_url:
        print(f"{DATABASE_URL_ENV} is required")
        return 2
    try:
        counts = seed_disaster_recovery_fixture(
            database_url,
            confirm_disposable_database=args.confirm_disposable_database,
        )
    except (OSError, RuntimeError, TypeError, ValueError, psycopg.Error) as exc:
        print(f"PostgreSQL disaster recovery fixture failed: {type(exc).__name__}")
        return 1
    print(json.dumps({"status": "seeded", "table_row_counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
