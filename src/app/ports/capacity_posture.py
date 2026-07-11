from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.capacity_posture import PostgresCapacityPosture


@runtime_checkable
class PostgresCapacityPostureRepository(Protocol):
    def postgres_capacity_posture(self) -> PostgresCapacityPosture: ...
