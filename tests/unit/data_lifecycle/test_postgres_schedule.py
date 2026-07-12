from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.domain.data_lifecycle import DataLifecycleState
from app.infrastructure.data_lifecycle import postgres_schedule as module
from app.infrastructure.data_lifecycle.postgres_schedule import (
    PostgresScheduledDataLifecycleRepository,
)


NOW = datetime(2026, 7, 12, 2, 0, tzinfo=UTC)


class Cursor:
    def __init__(self, rows: list[dict[str, Any]], *, fail: bool = False) -> None:
        self.rows = rows
        self.fail = fail
        self.query = ""
        self.params: tuple[object, ...] = ()

    def __enter__(self) -> Cursor:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...]) -> None:
        if self.fail:
            raise RuntimeError("database unavailable")
        self.query = " ".join(query.split())
        self.params = params

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class Connection:
    def __init__(self, cursor: Cursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> Cursor:
        return self.cursor_instance


def test_postgres_scheduled_lifecycle_scan_is_bounded_ordered_and_source_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = Cursor(
        [
            {
                "candidate_id": "candidate-expired-001",
                "tenant_id": "tenant-private-bank-sg",
                "policy_ref": "lotus-idea:regulated-advisory-evidence:seven-year:v1",
                "state": "held",
                "held_from_state": "erased",
                "retention_expires_at_utc": NOW,
                "version": 4,
                "active_outbox_count": 1,
                "active_downstream_count": 2,
            }
        ]
    )
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )

    snapshots = PostgresScheduledDataLifecycleRepository(
        Connection(cursor)
    ).scan_data_lifecycle_controls(
        evaluated_at_utc=NOW,
        limit=11,
    )

    assert cursor.params == (NOW, 11)
    assert "control.retention_expires_at_utc <= %s" in cursor.query
    assert "control.state <> 'purged'" in cursor.query
    assert "ORDER BY control.retention_expires_at_utc, control.candidate_id" in cursor.query
    assert "LIMIT %s" in cursor.query
    assert snapshots[0].state is DataLifecycleState.HELD
    assert snapshots[0].held_from_state is DataLifecycleState.ERASED
    assert snapshots[0].active_outbox_count == 1
    assert snapshots[0].active_downstream_count == 2
    assert observations[0]["outcome"] == "accepted"


def test_postgres_scheduled_lifecycle_scan_uses_governed_metric_vocabulary() -> None:
    repository = PostgresScheduledDataLifecycleRepository(Connection(Cursor([])))

    assert (
        repository.scan_data_lifecycle_controls(
            evaluated_at_utc=NOW,
            limit=10,
        )
        == ()
    )


def test_postgres_scheduled_lifecycle_scan_observes_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(
        module,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )
    repository = PostgresScheduledDataLifecycleRepository(Connection(Cursor([], fail=True)))

    with pytest.raises(RuntimeError, match="database unavailable"):
        repository.scan_data_lifecycle_controls(evaluated_at_utc=NOW, limit=10)

    assert observations[0]["outcome"] == "failed"
