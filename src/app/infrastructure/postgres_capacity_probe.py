from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any, Protocol, cast

import psycopg

from app.ports.capacity_probe import PostgresCapacityProbeResult


class _Cursor(Protocol):
    def execute(self, query: str) -> Any: ...

    def fetchone(self) -> tuple[object, ...] | None: ...

    def __enter__(self) -> "_Cursor": ...

    def __exit__(self, *args: object) -> None: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...

    def close(self) -> None: ...


class PostgresCapacityProbe:
    def __init__(
        self,
        *,
        database_url: str,
        connect_timeout_seconds: int = 5,
        connection_factory: Callable[..., _Connection] | None = None,
        monotonic: Callable[[], float] = time.perf_counter,
    ) -> None:
        if not database_url.strip():
            raise ValueError("database_url must not be blank")
        if connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive")
        self._database_url = database_url
        self._connect_timeout_seconds = connect_timeout_seconds
        self._connection_factory = connection_factory
        self._monotonic = monotonic

    def execute(self) -> PostgresCapacityProbeResult:
        connection: _Connection | None = None
        started_at = self._monotonic()
        try:
            connection = self._connect()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                if row != (1,):
                    return self._result(started_at, "failed", None)
                cursor.execute(
                    "SELECT COUNT(*)::double precision / "
                    "current_setting('max_connections')::double precision "
                    "FROM pg_stat_activity"
                )
                utilization_row = cursor.fetchone()
            return self._result(
                started_at,
                "accepted",
                _utilization_fraction(utilization_row),
            )
        except (psycopg.Error, OSError):
            return self._result(started_at, "failed", None)
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> _Connection:
        if self._connection_factory is not None:
            return self._connection_factory(
                self._database_url,
                connect_timeout=self._connect_timeout_seconds,
                application_name="lotus-idea-capacity-probe",
            )
        return cast(
            _Connection,
            psycopg.connect(
                self._database_url,
                connect_timeout=self._connect_timeout_seconds,
                application_name="lotus-idea-capacity-probe",
            ),
        )

    def _result(
        self,
        started_at: float,
        outcome: str,
        utilization_fraction: float | None,
    ) -> PostgresCapacityProbeResult:
        return PostgresCapacityProbeResult(
            duration_seconds=max(0.0, self._monotonic() - started_at),
            outcome=outcome,
            connection_utilization_fraction=utilization_fraction,
        )


def _utilization_fraction(row: tuple[object, ...] | None) -> float | None:
    if row is None or len(row) != 1:
        return None
    measurement = row[0]
    if isinstance(measurement, bool) or not isinstance(measurement, (int, float)):
        return None
    fraction = float(measurement)
    return fraction if 0 <= fraction <= 1 else None
