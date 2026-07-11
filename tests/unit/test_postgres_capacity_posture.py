from __future__ import annotations

from collections import deque

from app.domain.capacity_posture import CapacityPosture
from app.infrastructure.postgres_capacity_posture import load_postgres_capacity_posture


class StubCursor:
    def __init__(self, row: object = None, *, failure: Exception | None = None) -> None:
        self.row = row
        self.failure = failure
        self.query = ""

    def execute(self, query: str, params: object = None) -> None:
        self.query = query
        if self.failure is not None:
            raise self.failure

    def fetchall(self) -> list[object]:
        return [self.row]

    def __enter__(self) -> "StubCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class StubConnection:
    def __init__(self, cursors: list[StubCursor]) -> None:
        self.cursors = deque(cursors)

    def cursor(self) -> StubCursor:
        return self.cursors.popleft()

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def test_capacity_projection_supports_tuple_and_mapping_rows() -> None:
    tuple_posture = load_postgres_capacity_posture(StubConnection([StubCursor((0.71,))]))
    mapping_posture = load_postgres_capacity_posture(
        StubConnection([StubCursor({"connection_utilization_fraction": 0.91})])
    )

    assert tuple_posture.posture is CapacityPosture.WARNING
    assert mapping_posture.posture is CapacityPosture.SHED


def test_capacity_projection_fails_closed_on_query_or_shape_failure() -> None:
    for cursor in (
        StubCursor(failure=RuntimeError("database detail")),
        StubCursor((0.1, 0.2)),
        StubCursor({"wrong": 0.5}),
        StubCursor((True,)),
        StubCursor((1.1,)),
    ):
        posture = load_postgres_capacity_posture(StubConnection([cursor]))

        assert posture.posture is CapacityPosture.UNAVAILABLE
        assert posture.connection_utilization_fraction is None
