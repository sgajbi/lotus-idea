from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Sequence

import pytest

from app.infrastructure.postgres_opportunity_effectiveness import (
    load_opportunity_effectiveness_summary,
)


def test_postgres_effectiveness_projection_maps_one_privacy_safe_aggregate_row() -> None:
    row = _summary_row()
    connection = _Connection(row)

    summary = load_opportunity_effectiveness_summary(
        connection,
        tenant_id="tenant-a",
        window_start_utc=_time(8),
        window_end_utc=_time(12),
        evaluated_at_utc=_time(14),
        max_opportunities=100,
    )

    assert summary.generated_opportunity_count == 3
    assert summary.family_counts == {"high_cash": 2, "underperformance": 1}
    assert summary.current_downstream_outcome_counts == {"accepted": 1}
    assert summary.detection_to_review_seconds == (Decimal("60.0"), Decimal("120.0"))
    assert connection.cursor_instance.params == (
        "tenant-a",
        _time(8),
        _time(12),
        _time(14),
        101,
    )
    query = connection.cursor_instance.query
    assert "opportunity-effectiveness-summary-v1" in query
    assert "idea_data_lifecycle_control" in query
    assert "LIMIT (SELECT bounded_limit FROM parameters)" in query
    assert "candidate_json" not in summary.__dict__


@pytest.mark.parametrize(
    ("column", "message"),
    (
        ("invalid_temporal_fact_count", "temporally invalid"),
        ("invalid_outcome_history_count", "quarantined conversion outcomes"),
    ),
)
def test_postgres_effectiveness_projection_fails_closed_on_invalid_durable_facts(
    column: str,
    message: str,
) -> None:
    row = _summary_row()
    row[column] = 1

    with pytest.raises(ValueError, match=message):
        load_opportunity_effectiveness_summary(
            _Connection(row),
            tenant_id="tenant-a",
            window_start_utc=_time(8),
            window_end_utc=_time(12),
            evaluated_at_utc=_time(14),
            max_opportunities=100,
        )


def test_postgres_effectiveness_projection_rejects_malformed_driver_values() -> None:
    row = _summary_row()
    row["family_counts"] = {"high_cash": True}

    with pytest.raises(TypeError, match="family_counts values must be integers"):
        load_opportunity_effectiveness_summary(
            _Connection(row),
            tenant_id="tenant-a",
            window_start_utc=_time(8),
            window_end_utc=_time(12),
            evaluated_at_utc=_time(14),
            max_opportunities=100,
        )


class _Cursor:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row
        self.query = ""
        self.params: Sequence[Any] | None = None

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        self.query = query
        self.params = params

    def fetchall(self) -> list[dict[str, Any]]:
        return [self.row]

    def __enter__(self) -> _Cursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _Connection:
    def __init__(self, row: dict[str, Any]) -> None:
        self.cursor_instance = _Cursor(row)

    def cursor(self) -> _Cursor:
        return self.cursor_instance

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def _summary_row() -> dict[str, Any]:
    return {
        "generated_opportunity_count": 3,
        "reviewed_opportunity_count": 2,
        "feedback_opportunity_count": 1,
        "conversion_opportunity_count": 1,
        "conversion_intent_count": 1,
        "stale_evidence_opportunity_count": 0,
        "unavailable_evidence_opportunity_count": 0,
        "unsupported_evidence_opportunity_count": 0,
        "suppressed_opportunity_count": 0,
        "duplicate_suppressed_opportunity_count": 0,
        "recurrent_opportunity_count": 0,
        "recurrent_detection_count": 0,
        "reconciled_submission_count": 0,
        "family_counts": {"high_cash": 2, "underperformance": 1},
        "score_band_counts": {"critical": 2, "high": 1},
        "latest_review_action_counts": {"approve_for_conversion": 1, "reject": 1},
        "feedback_reason_counts": {"relevant": 1},
        "current_downstream_outcome_counts": {"accepted": 1},
        "downstream_submission_posture_counts": {},
        "detection_to_review_seconds": [Decimal("60.0"), Decimal("120.0")],
        "approval_to_conversion_seconds": [Decimal("30.0")],
        "invalid_temporal_fact_count": 0,
        "invalid_outcome_history_count": 0,
    }


def _time(hour: int) -> datetime:
    return datetime(2026, 6, 21, hour, tzinfo=UTC)
