from __future__ import annotations

from collections import deque

import pytest

from app.infrastructure.postgres_capacity_stress import PostgresCapacityStressAdapter


class StubCursor:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows
        self.queries: list[str] = []

    def execute(self, query: str, params: object = None) -> None:
        self.queries.append(query)

    def fetchall(self) -> list[object]:
        return self.rows

    def __enter__(self) -> "StubCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class StubConnection:
    def __init__(self, cursors: list[StubCursor]) -> None:
        self.cursors = deque(cursors)
        self.closed = False

    def cursor(self) -> StubCursor:
        return self.cursors.popleft()

    def close(self) -> None:
        self.closed = True

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class ConnectionFactory:
    def __init__(self, connections: list[StubConnection]) -> None:
        self.connections = deque(connections)
        self.application_names: list[str] = []

    def __call__(self, database_url: str, **kwargs: object) -> StubConnection:
        self.application_names.append(str(kwargs["application_name"]))
        return self.connections.popleft()


def _adapter(
    observer: StubConnection,
    *load_connections: StubConnection,
    **overrides: object,
) -> PostgresCapacityStressAdapter:
    values = {
        "database_url": "postgresql://redacted",
        "expected_database_name": "idea_capacity_proof",
        "maximum_target_connections": 20,
        "connection_factory": ConnectionFactory([observer, *load_connections]),
    }
    values.update(overrides)
    return PostgresCapacityStressAdapter(**values)  # type: ignore[arg-type]


def test_verifies_target_reads_fresh_posture_and_releases_load() -> None:
    preflight = StubCursor([("idea_capacity_proof", 20)])
    refresh_and_posture = StubCursor([(0.9,)])
    observer = StubConnection([preflight, refresh_and_posture])
    load = StubConnection([])
    adapter = _adapter(observer, load)

    adapter.acquire_load_connection()
    posture = adapter.read_posture()
    adapter.close()

    assert posture.posture == "shed"
    assert "current_database" in preflight.queries[0]
    assert "pg_stat_clear_snapshot" in refresh_and_posture.queries[0]
    assert load.closed is True
    assert observer.closed is True


@pytest.mark.parametrize(
    ("rows", "overrides", "message"),
    [
        ([], {}, "invalid shape"),
        ([("wrong", 20)], {}, "identity mismatch"),
        ([("idea_capacity_proof", 101)], {}, "exceeds"),
        ([{"database_name": "idea_capacity_proof", "max_connections": True}], {}, "invalid shape"),
    ],
)
def test_preflight_fails_closed_and_closes_observer(
    rows: list[object], overrides: dict[str, object], message: str
) -> None:
    observer = StubConnection([StubCursor(rows)])

    with pytest.raises(ValueError, match=message):
        _adapter(observer, **overrides)

    assert observer.closed is True


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"database_url": " "}, "database_url"),
        ({"expected_database_name": " "}, "expected_database_name"),
        ({"maximum_target_connections": 0}, "between 1 and 100"),
        ({"maximum_target_connections": 101}, "between 1 and 100"),
        ({"connect_timeout_seconds": 0}, "positive"),
    ],
)
def test_rejects_unsafe_configuration(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _adapter(StubConnection([]), **overrides)
