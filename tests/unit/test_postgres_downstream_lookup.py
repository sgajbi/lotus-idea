from __future__ import annotations

from dataclasses import replace

from app.domain import (
    DownstreamSubmissionPosture,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReviewPosture,
    request_conversion_intent as _request_conversion_intent,
    request_report_evidence_pack,
)

from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    access_scope,
    conversion_command,
    high_cash_candidate,
    review_command,
    report_pack_command,
)
from tests.support.postgres_review_authority import persist_candidate_with_review_authority

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
    candidate, grant = persist_candidate_with_review_authority(
        repository,
        candidate,
        idempotency_key="signal-ingestion:downstream-lookup",
        accepted_at_utc=EVALUATED_AT,
        review_command=lambda value: review_command(candidate=value),
    )
    conversion_result = _request_conversion_intent(
        candidate,
        conversion_command(),
        accepted_at_utc=EVALUATED_AT,
        review_authority_grant=grant,
    )
    repository.record_conversion_intent(
        conversion_result,
        idempotency_key=conversion_result.conversion_intent.idempotency_key,
        payload={"conversionIntentId": "conversion-report-001"},
    )
    connection.executed_sql.clear()

    loaded = repository.conversion_intent_by_id("conversion-report-001")

    assert loaded == conversion_result.conversion_intent
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea downstream-lookup-conversion-intent */" in executed_sql
    assert "intent.conversion_intent_id = %s" in executed_sql
    assert "join idea_data_lifecycle_control" in executed_sql
    assert "idea_conversion_intent" in executed_sql
    assert "idea_candidate_record" not in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql


def test_postgres_report_pack_lookup_uses_direct_table_query() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = approved_candidate()
    candidate, grant = persist_candidate_with_review_authority(
        repository,
        candidate,
        idempotency_key="signal-ingestion:report-pack-lookup",
        accepted_at_utc=EVALUATED_AT,
        review_command=lambda value: review_command(candidate=value),
    )
    conversion_result = _request_conversion_intent(
        candidate,
        conversion_command(),
        accepted_at_utc=EVALUATED_AT,
        review_authority_grant=grant,
    )
    conversion_persistence = repository.record_conversion_intent(
        conversion_result,
        idempotency_key=conversion_result.conversion_intent.idempotency_key,
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
        idempotency_key=pack_result.evidence_pack.idempotency_key,
        payload={"reportEvidencePackId": "report-evidence-pack-001"},
    )
    connection.executed_sql.clear()

    loaded = repository.report_evidence_pack_by_id("report-evidence-pack-001")

    assert loaded == pack_result.evidence_pack
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea downstream-lookup-report-evidence-pack */" in executed_sql
    assert "report.report_evidence_pack_id = %s" in executed_sql
    assert "join idea_data_lifecycle_control" in executed_sql
    assert "idea_report_evidence_pack_request" in executed_sql
    assert "idea_candidate_record" not in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_downstream_submission" not in executed_sql


def test_postgres_report_pack_candidate_lookup_uses_bounded_record_query() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = approved_candidate()
    candidate, grant = persist_candidate_with_review_authority(
        repository,
        candidate,
        idempotency_key="signal-ingestion:report-pack-candidate-lookup",
        accepted_at_utc=EVALUATED_AT,
        review_command=lambda value: review_command(candidate=value),
    )
    conversion_result = _request_conversion_intent(
        candidate,
        conversion_command(),
        accepted_at_utc=EVALUATED_AT,
        review_authority_grant=grant,
    )
    conversion_persistence = repository.record_conversion_intent(
        conversion_result,
        idempotency_key=conversion_result.conversion_intent.idempotency_key,
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
        idempotency_key=pack_result.evidence_pack.idempotency_key,
        payload={"reportEvidencePackId": "report-evidence-pack-001"},
    )
    connection.executed_sql.clear()

    loaded = repository.candidate_record_for_report_evidence_pack("report-evidence-pack-001")

    assert loaded is not None
    assert loaded.candidate.access_scope == candidate.access_scope
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea downstream-lookup-report-evidence-pack-candidate */" in executed_sql
    assert "report.report_evidence_pack_id = %s" in executed_sql
    assert "join idea_data_lifecycle_control" in executed_sql
    assert "idea_report_evidence_pack_request" in executed_sql


def test_postgres_downstream_submission_idempotency_lookup_uses_direct_table_query() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    claim = build_downstream_submission_claim(
        idempotency_key="downstream-submit:bounded-lookup",
        request_fingerprint="sha256:downstream-submit-bounded",
        resource_id="conversion-bounded-lookup",
        submitted_at_utc=EVALUATED_AT,
        correlation_id="corr-downstream-bounded",
        trace_id="trace-downstream-bounded",
    )
    repository.claim_downstream_submission(claim)
    finalized = repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        finalized_at_utc=EVALUATED_AT,
    )
    assert finalized.record is not None
    record = finalized.record
    connection.executed_sql.clear()

    loaded = repository.downstream_submission_by_idempotency_key("downstream-submit:bounded-lookup")

    assert loaded == record
    executed_sql = " ".join(connection.executed_sql)
    assert "/* lotus-idea downstream-submission-by-idempotency */" in executed_sql
    assert "where idempotency_key = %s" in executed_sql
    assert "idea_downstream_submission" in executed_sql
    assert "idea_candidate_record" not in executed_sql
    assert "idea_outbox_event" not in executed_sql
    assert "idea_conversion_intent" not in executed_sql
    assert "idea_report_evidence_pack_request" not in executed_sql
    assert "idea_ai_explanation_lineage" not in executed_sql


def test_postgres_downstream_lookups_return_none_for_missing_records() -> None:
    repository = PostgresIdeaRepository(FakePostgresConnection())

    assert repository.conversion_intent_by_id("missing-conversion") is None
    assert repository.candidate_record_for_conversion_intent("missing-conversion") is None
    assert repository.report_evidence_pack_by_id("missing-report-pack") is None
    assert repository.candidate_record_for_report_evidence_pack("missing-report-pack") is None
    assert repository.downstream_submission_by_idempotency_key("missing-submission") is None


def test_postgres_downstream_lookups_hide_erased_candidate_resources() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = approved_candidate()
    candidate, grant = persist_candidate_with_review_authority(
        repository,
        candidate,
        idempotency_key="signal-ingestion:hidden-erased-resource",
        accepted_at_utc=EVALUATED_AT,
        review_command=lambda value: review_command(candidate=value),
    )
    conversion_result = _request_conversion_intent(
        candidate,
        conversion_command(),
        accepted_at_utc=EVALUATED_AT,
        review_authority_grant=grant,
    )
    repository.record_conversion_intent(
        conversion_result,
        idempotency_key=conversion_result.conversion_intent.idempotency_key,
        payload={"conversionIntentId": "conversion-report-001"},
    )
    control = connection.rows["idea_data_lifecycle_control"][0]
    control["state"] = "erased"

    assert repository.conversion_intent_by_id("conversion-report-001") is None
    assert repository.candidate_record_for_conversion_intent("conversion-report-001") is None
