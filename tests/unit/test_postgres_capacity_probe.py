from __future__ import annotations

from collections import deque
from typing import Any

import psycopg
import pytest

from app.infrastructure.postgres_capacity_probe import PostgresCapacityProbe


class StubCursor:
    def __init__(self, rows: list[tuple[object, ...] | None]) -> None:
        self.rows = deque(rows)
        self.queries: list[str] = []

    def execute(self, query: str) -> None:
        self.queries.append(query)

    def fetchone(self) -> tuple[object, ...] | None:
        return self.rows.popleft()

    def __enter__(self) -> "StubCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class StubConnection:
    def __init__(self, cursor: StubCursor) -> None:
        self._cursor = cursor
        self.closed = False

    def cursor(self) -> StubCursor:
        return self._cursor

    def close(self) -> None:
        self.closed = True


def test_probe_measures_read_only_query_and_connection_utilization() -> None:
    cursor = StubCursor([(1,), (0.25,)])
    connection = StubConnection(cursor)
    connection_args: dict[str, Any] = {}

    def connect(database_url: str, **kwargs: object) -> StubConnection:
        connection_args.update(database_url=database_url, **kwargs)
        return connection

    clock = iter((10.0, 10.2))
    probe = PostgresCapacityProbe(
        database_url="postgresql://sensitive",
        connection_factory=connect,
        monotonic=lambda: next(clock),
    )

    result = probe.execute()

    assert result.duration_seconds == pytest.approx(0.2)
    assert result.outcome == "accepted"
    assert result.connection_utilization_fraction == 0.25
    assert cursor.queries == [
        "SELECT 1",
        "SELECT COUNT(*)::double precision / current_setting('max_connections')::double precision FROM pg_stat_activity",
    ]
    assert connection_args["application_name"] == "lotus-idea-capacity-probe"
    assert connection.closed is True


def test_probe_fails_closed_on_unexpected_result_without_connection_detail() -> None:
    connection = StubConnection(StubCursor([(2,)]))
    probe = PostgresCapacityProbe(
        database_url="postgresql://sensitive",
        connection_factory=lambda *args, **kwargs: connection,
    )

    result = probe.execute()

    assert result.outcome == "failed"
    assert result.connection_utilization_fraction is None
    assert connection.closed is True


def test_probe_fails_closed_on_database_error() -> None:
    def connect(*args: object, **kwargs: object) -> StubConnection:
        raise psycopg.OperationalError("sensitive host detail")

    probe = PostgresCapacityProbe(
        database_url="postgresql://sensitive",
        connection_factory=connect,
    )

    result = probe.execute()

    assert result.outcome == "failed"
    assert result.connection_utilization_fraction is None


def test_probe_does_not_claim_invalid_utilization() -> None:
    for value in (-0.1, 1.1, "unknown", True):
        connection = StubConnection(StubCursor([(1,), (value,)]))
        probe = PostgresCapacityProbe(
            database_url="postgresql://sensitive",
            connection_factory=lambda *args, connection=connection, **kwargs: connection,
        )

        result = probe.execute()

        assert result.outcome == "accepted"
        assert result.connection_utilization_fraction is None


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"database_url": " "}, "database_url must not be blank"),
        ({"database_url": "postgresql://example", "connect_timeout_seconds": 0}, "positive"),
    ],
)
def test_probe_rejects_invalid_connection_configuration(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PostgresCapacityProbe(**kwargs)  # type: ignore[arg-type]


def test_probe_uses_default_psycopg_connection_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = StubConnection(StubCursor([(1,), None]))
    monkeypatch.setattr(
        "app.infrastructure.postgres_capacity_probe.psycopg.connect",
        lambda *args, **kwargs: connection,
    )
    probe = PostgresCapacityProbe(database_url="postgresql://example")

    result = probe.execute()

    assert result.outcome == "accepted"
    assert result.connection_utilization_fraction is None
    assert connection.closed is True
