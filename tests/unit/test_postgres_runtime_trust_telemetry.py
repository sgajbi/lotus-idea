from __future__ import annotations

from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    high_cash_candidate,
)


def test_postgres_repository_uses_bounded_runtime_trust_telemetry_projection() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidate = high_cash_candidate()
    repository.persist_candidate(
        candidate,
        idempotency_key="runtime-trust-telemetry:test",
        payload={"candidateId": candidate.candidate_id},
        actor_subject="platform-operator",
        occurred_at_utc=EVALUATED_AT,
    )
    candidate_json = connection.rows["idea_candidate_record"][0]["candidate_json"]
    candidate_json["evidence_packet"]["source_refs"][0]["freshness"] = "stale"
    candidate_json["evidence_packet"]["source_refs"][0]["data_quality_status"] = "stale"
    connection.rows["idea_review_decision"] = [{}]
    connection.rows["idea_feedback_event"] = [{}]
    connection.rows["idea_conversion_intent"] = [{}, {}]
    connection.rows["idea_conversion_outcome"] = [{}]
    connection.rows["idea_report_evidence_pack_request"] = [{}, {}, {}]
    connection.executed_sql.clear()

    summary = repository.runtime_trust_telemetry_summary()

    executed_sql = " ".join(connection.executed_sql)
    assert summary.candidate_snapshot_count == 1
    assert summary.current_source_ref_count == 3
    assert summary.stale_or_unavailable_source_ref_count == 1
    assert summary.source_authority_counts == {"lotus-core": 4}
    assert summary.freshness_counts == {"current": 3, "stale": 1}
    assert summary.supportability_counts == {"ready": 1}
    assert summary.lifecycle_counts == {"generated": 1}
    assert summary.review_decision_count == 1
    assert summary.feedback_event_count == 1
    assert summary.conversion_intent_count == 2
    assert summary.conversion_outcome_count == 1
    assert summary.report_evidence_pack_count == 3
    assert summary.lineage_materialized is True
    assert summary.source_batch_evidence_available is True
    assert summary.data_quality_status == "quality_warning"
    assert summary.latest_source_generated_at_utc == EVALUATED_AT
    assert summary.source_as_of_dates == ("2026-06-21",)
    assert "/* lotus-idea runtime-trust-telemetry-summary */" in executed_sql
    assert "from idea_candidate_record" in executed_sql
    assert "from idea_review_decision" in executed_sql
    assert "from idea_feedback_event" in executed_sql
    assert "from idea_conversion_intent" in executed_sql
    assert "from idea_conversion_outcome" in executed_sql
    assert "from idea_report_evidence_pack_request" in executed_sql
    for unrelated_table in (
        "idea_audit_event",
        "idea_outbox_event",
        "idea_downstream_submission",
        "idea_ai_explanation_lineage",
        "idea_lifecycle_history",
        "idea_idempotency_record",
    ):
        assert unrelated_table not in executed_sql
