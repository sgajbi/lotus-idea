from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, cast

import psycopg

from app.domain.capacity_posture import PostgresCapacityPosture
from app.infrastructure.postgres_capacity_posture import load_postgres_capacity_posture
from app.infrastructure.postgres_protocols import PostgresConnection


TARGET_PREFLIGHT_QUERY = """
SELECT current_database() AS database_name,
       current_setting('max_connections')::integer AS max_connections
"""


class CloseablePostgresConnection(PostgresConnection, Protocol):
    def close(self) -> None: ...


class PostgresCapacityStressAdapter:
    def __init__(
        self,
        *,
        database_url: str,
        expected_database_name: str,
        maximum_target_connections: int,
        connect_timeout_seconds: int = 5,
        connection_factory: Callable[..., CloseablePostgresConnection] | None = None,
    ) -> None:
        if not database_url.strip():
            raise ValueError("database_url must not be blank")
        if not expected_database_name.strip():
            raise ValueError("expected_database_name must not be blank")
        if not 1 <= maximum_target_connections <= 100:
            raise ValueError("maximum_target_connections must be between 1 and 100")
        if connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive")
        self._database_url = database_url
        self._expected_database_name = expected_database_name
        self._maximum_target_connections = maximum_target_connections
        self._connect_timeout_seconds = connect_timeout_seconds
        self._connection_factory = connection_factory
        self._observer = self._connect("lotus-idea-capacity-threshold-observer")
        self._load_connections: list[CloseablePostgresConnection] = []
        try:
            self._verify_target()
        except Exception:
            self._observer.close()
            raise

    def read_posture(self) -> PostgresCapacityPosture:
        return load_postgres_capacity_posture(self._observer)

    def acquire_load_connection(self) -> None:
        self._load_connections.append(self._connect("lotus-idea-capacity-threshold-load"))

    def release_load_connections(self) -> None:
        while self._load_connections:
            self._load_connections.pop().close()

    def close(self) -> None:
        self.release_load_connections()
        self._observer.close()

    def _verify_target(self) -> None:
        with self._observer.cursor() as cursor:
            cursor.execute(TARGET_PREFLIGHT_QUERY)
            rows = cursor.fetchall()
        target = _target_row(rows[0] if len(rows) == 1 else None)
        if target is None:
            raise ValueError("PostgreSQL capacity target preflight returned an invalid shape")
        database_name, max_connections = target
        if database_name != self._expected_database_name:
            raise ValueError("PostgreSQL capacity target database identity mismatch")
        if max_connections > self._maximum_target_connections:
            raise ValueError("PostgreSQL capacity target exceeds the configured connection cap")

    def _connect(self, application_name: str) -> CloseablePostgresConnection:
        factory = self._connection_factory or psycopg.connect
        return cast(
            CloseablePostgresConnection,
            factory(
                self._database_url,
                connect_timeout=self._connect_timeout_seconds,
                application_name=application_name,
            ),
        )


def _target_row(row: Any) -> tuple[str, int] | None:
    values: tuple[object, object]
    if isinstance(row, Mapping):
        values = (row.get("database_name"), row.get("max_connections"))
    elif isinstance(row, Sequence) and not isinstance(row, (str, bytes)) and len(row) == 2:
        values = (row[0], row[1])
    else:
        return None
    database_name, max_connections = values
    if (
        not isinstance(database_name, str)
        or not database_name
        or isinstance(max_connections, bool)
        or not isinstance(max_connections, int)
        or max_connections <= 0
    ):
        return None
    return database_name, max_connections
