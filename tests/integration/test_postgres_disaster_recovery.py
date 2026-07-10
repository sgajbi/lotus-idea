from __future__ import annotations

from app.infrastructure.postgres_disaster_recovery import (
    PostgresRestoredDatabaseInspector,
)
from scripts.seed_postgres_disaster_recovery_fixture import (
    seed_disaster_recovery_fixture,
)

OWNED_TABLES = frozenset(
    {
        "idea_ai_explanation_lineage",
        "idea_audit_event",
        "idea_candidate_record",
        "idea_candidate_state_quarantine",
        "idea_conversion_intent",
        "idea_conversion_outcome",
        "idea_conversion_outcome_quarantine",
        "idea_downstream_submission",
        "idea_feedback_event",
        "idea_idempotency_record",
        "idea_lifecycle_history",
        "idea_outbox_event",
        "idea_outbox_recovery_audit",
        "idea_report_evidence_pack_request",
        "idea_review_decision",
    }
)


def test_postgres_restore_inspector_certifies_current_migrated_schema(
    postgres_database_url: str,
) -> None:
    inspector = PostgresRestoredDatabaseInspector(postgres_database_url)

    snapshot = inspector.inspect(expected_tables=OWNED_TABLES)

    assert set(snapshot.table_row_counts) == OWNED_TABLES
    assert set(snapshot.table_content_sha256) == OWNED_TABLES
    assert set(snapshot.table_row_counts.values()) == {0}
    assert all(len(digest) == 64 for digest in snapshot.table_content_sha256.values())
    assert snapshot.missing_primary_key_tables == ()
    assert snapshot.unvalidated_constraints == ("ck_idea_candidate_record_state_policy_v1",)
    assert snapshot.invalid_indexes == ()
    assert not any(snapshot.referential_violation_counts.values())
    assert not any(snapshot.semantic_violation_counts.values())
    assert len(snapshot.database_identity_sha256) == 64
    assert "PostgreSQL" in snapshot.postgres_version


def test_postgres_restore_inspector_validates_representative_linked_fixture(
    postgres_database_url: str,
) -> None:
    counts = seed_disaster_recovery_fixture(
        postgres_database_url,
        confirm_disposable_database=True,
    )

    snapshot = PostgresRestoredDatabaseInspector(postgres_database_url).inspect(
        expected_tables=OWNED_TABLES
    )

    assert counts == snapshot.table_row_counts
    assert all(
        count > 0
        for table, count in counts.items()
        if table
        not in {
            "idea_candidate_state_quarantine",
            "idea_conversion_outcome_quarantine",
        }
    )
    assert not any(snapshot.referential_violation_counts.values())
    assert not any(snapshot.semantic_violation_counts.values())
