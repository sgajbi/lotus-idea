from __future__ import annotations

from collections.abc import Callable
import time
from typing import TypeVar

import psycopg

from app.observability.service_slo_metrics import observe_postgres_operation


_T = TypeVar("_T")


class PostgresOperationUnavailableError(RuntimeError):
    """A PostgreSQL driver failure that callers can handle without leaking details."""


def execute_observed_postgres_call(operation: str, call: Callable[[], _T]) -> _T:
    started_at = time.perf_counter()
    try:
        result = call()
    except Exception as exc:
        observe_postgres_operation(
            operation=operation,
            outcome="failed",
            duration_seconds=time.perf_counter() - started_at,
        )
        if isinstance(exc, psycopg.Error):
            raise PostgresOperationUnavailableError("PostgreSQL operation unavailable") from exc
        raise
    observe_postgres_operation(
        operation=operation,
        outcome="accepted",
        duration_seconds=time.perf_counter() - started_at,
    )
    return result
