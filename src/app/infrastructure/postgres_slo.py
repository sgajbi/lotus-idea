from __future__ import annotations

from collections.abc import Callable
import time
from typing import TypeVar

from app.observability.service_slo_metrics import observe_postgres_operation


_T = TypeVar("_T")


def execute_observed_postgres_call(operation: str, call: Callable[[], _T]) -> _T:
    started_at = time.perf_counter()
    try:
        result = call()
    except Exception:
        observe_postgres_operation(
            operation=operation,
            outcome="failed",
            duration_seconds=time.perf_counter() - started_at,
        )
        raise
    observe_postgres_operation(
        operation=operation,
        outcome="accepted",
        duration_seconds=time.perf_counter() - started_at,
    )
    return result
