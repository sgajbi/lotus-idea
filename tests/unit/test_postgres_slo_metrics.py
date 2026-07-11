from __future__ import annotations

import pytest

import app.infrastructure.postgres_slo as postgres_slo_module
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection


def test_postgres_snapshot_records_bounded_read_sli(monkeypatch: pytest.MonkeyPatch) -> None:
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(
        postgres_slo_module,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )

    snapshot = PostgresIdeaRepository(FakePostgresConnection()).snapshot()

    assert snapshot.candidate_records == {}
    assert len(observations) == 1
    assert observations[0]["operation"] == "snapshot_read"
    assert observations[0]["outcome"] == "accepted"
    assert observations[0]["duration_seconds"] >= 0  # type: ignore[operator]


def test_postgres_snapshot_records_failure_without_query_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(
        postgres_slo_module,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        PostgresIdeaRepository(FailingConnection()).snapshot()

    assert len(observations) == 1
    assert observations[0]["operation"] == "snapshot_read"
    assert observations[0]["outcome"] == "failed"
    assert set(observations[0]) == {"operation", "outcome", "duration_seconds"}


class FailingConnection:
    def cursor(self) -> object:
        raise RuntimeError("database unavailable")
