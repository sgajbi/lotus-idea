from __future__ import annotations

from typing import Any, Callable, TypeVar

from app.domain.persistence import InMemoryIdeaRepository
from app.infrastructure.postgres_candidate_writes import ConcurrentIdempotencyMutationError
from app.infrastructure.postgres_repository_delta import apply_postgres_snapshot_delta

_T = TypeVar("_T")


def execute_postgres_mutation(
    writer: Any,
    connection: Any,
    snapshot_loader: Callable[[], Any],
    fresh_snapshot_loader: Callable[[], Any],
    operation: Callable[[InMemoryIdeaRepository], _T],
) -> _T:
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
            return result
        except ConcurrentIdempotencyMutationError:
            connection.rollback()
            if attempt_index == 0:
                use_fresh_snapshot = True
                continue
            raise
        except Exception:
            connection.rollback()
            raise
    raise RuntimeError("postgres mutation retry exhausted")
