from __future__ import annotations

from typing import Protocol

from app.domain.capacity_posture import PostgresCapacityPosture


class PostgresCapacityStressPort(Protocol):
    def read_posture(self) -> PostgresCapacityPosture: ...

    def acquire_load_connection(self) -> None: ...

    def release_load_connections(self) -> None: ...

    def close(self) -> None: ...
