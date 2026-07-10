from __future__ import annotations

from app.infrastructure.postgres_disaster_recovery import (
    REFERENTIAL_CHECKS,
    SEMANTIC_CHECKS,
)


def test_restore_inspector_covers_linked_workflow_and_resume_safety() -> None:
    assert {
        "ai_lineage_candidate",
        "conversion_outcome_intent",
        "outbox_candidate_aggregate",
        "outbox_recovery_event",
        "report_conversion_intent",
        "submission_conversion_intent",
        "submission_report_pack",
    }.issubset(REFERENTIAL_CHECKS)
    assert {
        "duplicate_outbox_fingerprint",
        "outbox_failure_state",
        "outbox_lease_state",
        "outbox_publication_state",
        "submission_lease_state",
    }.issubset(SEMANTIC_CHECKS)


def test_restore_inspector_queries_are_read_only() -> None:
    forbidden = ("insert ", "update ", "delete ", "alter ", "drop ", "truncate ")

    for _, query in (*REFERENTIAL_CHECKS.values(), *SEMANTIC_CHECKS.values()):
        normalized = " ".join(query.lower().split())
        assert normalized.startswith("select count(*)")
        assert not any(keyword in normalized for keyword in forbidden)


def test_restore_inspector_enforces_complete_outbox_failure_timing() -> None:
    query = SEMANTIC_CHECKS["outbox_failure_state"][1]

    assert "first_failed_at_utc IS NULL" in query
    assert "last_failed_at_utc IS NULL" in query
    assert "next_attempt_at_utc IS NOT NULL" in query


def test_restore_inspector_preserves_complete_downstream_fencing_history() -> None:
    query = SEMANTIC_CHECKS["submission_lease_state"][1]

    assert "NOT IN (0, 3)" in query
    assert "status <> 'in_flight'" not in query
