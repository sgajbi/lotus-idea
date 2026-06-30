from __future__ import annotations

from dataclasses import replace

from app.domain import (
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReviewPosture,
    request_conversion_intent,
    request_report_evidence_pack,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    FakePostgresConnection,
    access_scope,
    conversion_command,
    high_cash_candidate,
    report_pack_command,
)


def approved_candidate() -> IdeaCandidate:
    return replace(
        high_cash_candidate(candidate_scope=access_scope()),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )


def test_postgres_conversion_intent_lookup_uses_direct_table_query() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = approved_candidate()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:downstream-lookup",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    conversion_result = request_conversion_intent(candidate, conversion_command())
    repository.record_conversion_intent(
        conversion_result,
        idempotency_key="conversion:downstream-lookup",
        payload={"conversionIntentId": "conversion-report-001"},
    )
    connection.executed_sql.clear()

    loaded = repository.conversion_intent_by_id("conversion-report-001")

    assert loaded == conversion_result.conversion_intent
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea downstream-lookup-conversion-intent */" in executed_sql
    assert "where conversion_intent_id = %s" in executed_sql
    assert "idea_conversion_intent" in executed_sql
    assert "idea_candidate_record" not in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql


def test_postgres_report_pack_lookup_uses_direct_table_query() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = approved_candidate()
    repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:report-pack-lookup",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    conversion_result = request_conversion_intent(candidate, conversion_command())
    conversion_persistence = repository.record_conversion_intent(
        conversion_result,
        idempotency_key="conversion:report-pack-lookup",
        payload={"conversionIntentId": "conversion-report-001"},
    )
    assert conversion_persistence.record is not None
    pack_result = request_report_evidence_pack(
        conversion_persistence.record.candidate,
        conversion_result.conversion_intent,
        report_pack_command(),
    )
    repository.record_report_evidence_pack(
        pack_result,
        idempotency_key="report-pack:downstream-lookup",
        payload={"reportEvidencePackId": "report-evidence-pack-001"},
    )
    connection.executed_sql.clear()

    loaded = repository.report_evidence_pack_by_id("report-evidence-pack-001")

    assert loaded == pack_result.evidence_pack
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea downstream-lookup-report-evidence-pack */" in executed_sql
    assert "where report_evidence_pack_id = %s" in executed_sql
    assert "idea_report_evidence_pack_request" in executed_sql
    assert "idea_candidate_record" not in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql
