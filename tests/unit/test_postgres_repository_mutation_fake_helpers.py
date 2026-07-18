from __future__ import annotations

import pytest

from tests.unit.postgres_repository_mutation_fake_helpers import row_for_insert


class _JsonbValue:
    def __init__(self, obj: dict[str, str]) -> None:
        self.obj = obj


def test_row_for_insert_builds_candidate_record_row_with_unwrapped_jsonb() -> None:
    row = row_for_insert(
        "idea_candidate_record",
        (
            "candidate-1",
            "private-banking-family",
            "under_review",
            "advisor_review",
            "evidence-packet-1",
            "hash-1",
            _JsonbValue({"portfolio_id": "PB_SG_GLOBAL_BAL_001"}),
            "2026-07-18T01:00:00Z",
            "2026-07-18T01:01:00Z",
        ),
    )

    assert row == {
        "candidate_id": "candidate-1",
        "family": "private-banking-family",
        "lifecycle_status": "under_review",
        "review_posture": "advisor_review",
        "evidence_packet_id": "evidence-packet-1",
        "evidence_hash": "hash-1",
        "candidate_json": {"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        "persisted_at_utc": "2026-07-18T01:00:00Z",
        "updated_at_utc": "2026-07-18T01:01:00Z",
    }


def test_row_for_insert_builds_downstream_submission_operability_row() -> None:
    row = row_for_insert(
        "idea_downstream_submission",
        (
            "idem-1",
            "fingerprint-1",
            "conversion_intent",
            "intent-1",
            "lotus-manage",
            "lotus-idea",
            "submitted",
            None,
            "corr-1",
            "trace-1",
            "2026-07-18T02:00:00Z",
            "support-1",
            1,
            "2026-07-18T02:01:00Z",
            None,
            None,
            None,
            _JsonbValue({"operator": "advisor-desk"}),
        ),
    )

    assert row["idempotency_key"] == "idem-1"
    assert row["target"] == "lotus-manage"
    assert row["source_authority"] == "lotus-idea"
    assert row["audit_json"] == {"operator": "advisor-desk"}


def test_row_for_insert_rejects_unknown_table_explicitly() -> None:
    with pytest.raises(KeyError):
        row_for_insert("unknown_idea_table", ())


def test_row_for_insert_rejects_column_value_mismatch() -> None:
    with pytest.raises(ValueError, match="zip"):
        row_for_insert("idea_feedback_event", ("feedback-1",))
