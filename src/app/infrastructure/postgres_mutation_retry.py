from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

from app.domain.persistence import InMemoryIdeaRepository
from app.infrastructure.postgres_candidate_writes import ConcurrentIdempotencyMutationError
from app.infrastructure.postgres_conversion_outcome import (
    ConcurrentConversionOutcomeMutationError,
)
from app.infrastructure.postgres_repository_delta import apply_postgres_snapshot_delta
from app.infrastructure.postgres_review_identity import ConcurrentReviewIdentityMutationError
from app.observability.service_slo_metrics import observe_postgres_operation

_T = TypeVar("_T")


def execute_postgres_mutation(
    writer: Any,
    connection: Any,
    snapshot_loader: Callable[[], Any],
    fresh_snapshot_loader: Callable[[], Any],
    operation: Callable[[InMemoryIdeaRepository], _T],
) -> _T:
    started_at = time.perf_counter()
    use_fresh_snapshot = False
    for attempt_index in range(2):
        try:
            before = fresh_snapshot_loader() if use_fresh_snapshot else snapshot_loader()
            repository = InMemoryIdeaRepository(before)
            result = operation(repository)
            with connection.cursor() as cursor:
                apply_postgres_snapshot_delta(
                    writer,
                    cursor,
                    before=before,
                    after=repository.snapshot(),
                )
            connection.commit()
            observe_postgres_operation(
                operation="mutation",
                outcome="accepted",
                duration_seconds=time.perf_counter() - started_at,
            )
            return result
        except (
            ConcurrentIdempotencyMutationError,
            ConcurrentReviewIdentityMutationError,
            ConcurrentConversionOutcomeMutationError,
        ):
            connection.rollback()
            if attempt_index == 0:
                use_fresh_snapshot = True
                continue
            observe_postgres_operation(
                operation="mutation",
                outcome="conflict",
                duration_seconds=time.perf_counter() - started_at,
            )
            raise
        except Exception:
            connection.rollback()
            observe_postgres_operation(
                operation="mutation",
                outcome="failed",
                duration_seconds=time.perf_counter() - started_at,
            )
            raise
    raise RuntimeError("postgres mutation retry exhausted")  # pragma: no cover - defensive guard
