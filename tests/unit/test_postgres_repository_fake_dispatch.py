from __future__ import annotations

from datetime import UTC, datetime

from tests.unit.postgres_repository_fake import FakePostgresConnection


def test_fake_cursor_routes_generic_insert_select_and_delete_with_write_tracking() -> None:
    connection = FakePostgresConnection()
    cursor = connection.cursor()
    now = datetime(2026, 7, 18, tzinfo=UTC)

    cursor.execute(
        "insert into idea_candidate_record values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            "candidate-1",
            "high_cash",
            "new",
            "pending_review",
            "evidence-1",
            "hash-1",
            {"candidateId": "candidate-1"},
            now,
            now,
        ),
    )

    assert cursor.rowcount == 1
    assert connection.rows["idea_candidate_record"][0]["candidate_id"] == "candidate-1"

    cursor.execute("select * from idea_candidate_record")
    assert cursor.fetchall() == [
        {
            "candidate_id": "candidate-1",
            "family": "high_cash",
            "lifecycle_status": "new",
            "review_posture": "pending_review",
            "evidence_packet_id": "evidence-1",
            "evidence_hash": "hash-1",
            "candidate_json": {"candidateId": "candidate-1"},
            "persisted_at_utc": now,
            "updated_at_utc": now,
        }
    ]

    cursor.execute("delete from idea_candidate_record")

    assert connection.deletes == 1
    assert connection.rows["idea_candidate_record"] == []


def test_fake_cursor_downstream_readiness_summary_excludes_quarantined_outcomes() -> None:
    connection = FakePostgresConnection()
    connection.rows["idea_conversion_intent"].extend(
        [
            {"conversion_intent_id": "intent-1"},
            {"conversion_intent_id": "intent-2"},
        ]
    )
    connection.rows["idea_conversion_outcome"].extend(
        [
            {"conversion_intent_id": "intent-1"},
            {"conversion_intent_id": "intent-2"},
            {"conversion_intent_id": "intent-2"},
        ]
    )
    connection.rows["idea_conversion_outcome_quarantine"].append(
        {"conversion_intent_id": "intent-1"}
    )
    connection.rows["idea_report_evidence_pack_request"].append(
        {"report_evidence_pack_id": "pack-1"}
    )
    cursor = connection.cursor()

    cursor.execute("/* lotus-idea downstream-realization-readiness-summary */ select 1")

    assert cursor.fetchone() == {
        "conversion_intent_count": 2,
        "conversion_outcome_count": 1,
        "report_evidence_pack_request_count": 1,
    }
