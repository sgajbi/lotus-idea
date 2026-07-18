from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.infrastructure.postgres_runtime_trust_telemetry import (
    load_runtime_trust_telemetry_summary,
)
from app.infrastructure.postgres_protocols import PostgresCursor


def test_postgres_runtime_trust_telemetry_loader_defaults_empty_projection() -> None:
    connection = _TelemetryLoaderConnection(
        rows_by_comment={
            "runtime-trust-telemetry-summary": [],
            "runtime-trust-telemetry-source-authority-counts": [],
            "runtime-trust-telemetry-freshness-counts": [],
            "runtime-trust-telemetry-supportability-counts": [],
            "runtime-trust-telemetry-lifecycle-counts": [],
            "runtime-trust-telemetry-data-lifecycle-counts": [],
        }
    )

    summary = load_runtime_trust_telemetry_summary(connection)

    assert summary.candidate_snapshot_count == 0
    assert summary.current_source_ref_count == 0
    assert summary.stale_or_unavailable_source_ref_count == 0
    assert summary.source_authority_counts == {}
    assert summary.freshness_counts == {}
    assert summary.supportability_counts == {}
    assert summary.lifecycle_counts == {}
    assert summary.review_decision_count == 0
    assert summary.feedback_event_count == 0
    assert summary.conversion_intent_count == 0
    assert summary.conversion_outcome_count == 0
    assert summary.report_evidence_pack_count == 0
    assert summary.lineage_materialized is False
    assert summary.source_batch_evidence_available is False
    assert summary.data_quality_status == "quality_unknown"
    assert summary.latest_source_generated_at_utc is None
    assert summary.source_as_of_dates == ()
    assert summary.data_lifecycle_state_counts == {}
    assert summary.retention_expired_count == 0
    assert summary.lifecycle_control_missing_count == 0
    assert connection.executed_comments == (
        "runtime-trust-telemetry-summary",
        "runtime-trust-telemetry-source-authority-counts",
        "runtime-trust-telemetry-freshness-counts",
        "runtime-trust-telemetry-supportability-counts",
        "runtime-trust-telemetry-lifecycle-counts",
        "runtime-trust-telemetry-data-lifecycle-counts",
    )


def test_postgres_runtime_trust_telemetry_loader_decodes_summary_and_counts() -> None:
    generated_at = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    connection = _TelemetryLoaderConnection(
        rows_by_comment={
            "runtime-trust-telemetry-summary": [
                {
                    "candidate_snapshot_count": 2,
                    "current_source_ref_count": 3,
                    "stale_or_unavailable_source_ref_count": 1,
                    "review_decision_count": 1,
                    "feedback_event_count": 2,
                    "conversion_intent_count": 3,
                    "conversion_outcome_count": 4,
                    "report_evidence_pack_count": 5,
                    "lineage_materialized": True,
                    "source_batch_evidence_available": True,
                    "data_quality_status": "quality_warning",
                    "latest_source_generated_at_utc": generated_at.isoformat(),
                    "source_as_of_dates": ("2026-06-20", "2026-06-21"),
                    "retention_expired_count": 6,
                    "lifecycle_control_missing_count": 7,
                }
            ],
            "runtime-trust-telemetry-source-authority-counts": [
                {"label": "lotus-core", "count": "3"},
                {"label": "lotus-risk", "count": 1},
            ],
            "runtime-trust-telemetry-freshness-counts": [
                {"label": "current", "count": 3},
                {"label": "stale", "count": 1},
            ],
            "runtime-trust-telemetry-supportability-counts": [
                {"label": "ready", "count": 2},
                {"label": None, "count": 99},
            ],
            "runtime-trust-telemetry-lifecycle-counts": [{"label": "generated", "count": 2}],
            "runtime-trust-telemetry-data-lifecycle-counts": [
                {"label": "active", "count": 1},
                {"label": "held", "count": 1},
            ],
        }
    )

    summary = load_runtime_trust_telemetry_summary(connection)

    assert summary.candidate_snapshot_count == 2
    assert summary.current_source_ref_count == 3
    assert summary.stale_or_unavailable_source_ref_count == 1
    assert summary.source_authority_counts == {"lotus-core": 3, "lotus-risk": 1}
    assert summary.freshness_counts == {"current": 3, "stale": 1}
    assert summary.supportability_counts == {"ready": 2}
    assert summary.lifecycle_counts == {"generated": 2}
    assert summary.review_decision_count == 1
    assert summary.feedback_event_count == 2
    assert summary.conversion_intent_count == 3
    assert summary.conversion_outcome_count == 4
    assert summary.report_evidence_pack_count == 5
    assert summary.lineage_materialized is True
    assert summary.source_batch_evidence_available is True
    assert summary.data_quality_status == "quality_warning"
    assert summary.latest_source_generated_at_utc == generated_at
    assert summary.source_as_of_dates == ("2026-06-20", "2026-06-21")
    assert summary.data_lifecycle_state_counts == {"active": 1, "held": 1}
    assert summary.retention_expired_count == 6
    assert summary.lifecycle_control_missing_count == 7


class _TelemetryLoaderConnection:
    def __init__(self, *, rows_by_comment: dict[str, list[dict[str, Any]]]) -> None:
        self.rows_by_comment = rows_by_comment
        self.executed_comments: tuple[str, ...] = ()

    def cursor(self) -> PostgresCursor:
        return _TelemetryLoaderCursor(self)

    def commit(self) -> None:
        raise AssertionError("runtime trust telemetry loader must not commit")

    def rollback(self) -> None:
        raise AssertionError("runtime trust telemetry loader must not roll back")


class _TelemetryLoaderCursor:
    def __init__(self, connection: _TelemetryLoaderConnection) -> None:
        self.connection = connection
        self._rows: list[dict[str, Any]] = []

    def execute(self, query: str, params: object = None) -> None:
        assert params is None
        comment = _runtime_trust_telemetry_comment(query)
        self.connection.executed_comments = (*self.connection.executed_comments, comment)
        self._rows = self.connection.rows_by_comment[comment]

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows

    def __enter__(self) -> PostgresCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _runtime_trust_telemetry_comment(query: str) -> str:
    normalized = " ".join(query.split())
    marker = "/* lotus-idea "
    start = normalized.index(marker) + len(marker)
    end = normalized.index(" */", start)
    return normalized[start:end]
