from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable, Generic, TypeVar

from app.domain.data_lifecycle import (
    DataLifecycleCommand,
    DataLifecycleOperationResult,
    evaluate_data_lifecycle,
)
from app.domain.data_lifecycle_schedule import (
    ScheduledLifecycleReview,
    evaluate_scheduled_lifecycle_control,
    validate_scheduled_lifecycle_review_limit,
)
from app.ports.data_lifecycle import DataLifecycleRepository, ScheduledDataLifecycleRepository


_RepositoryT = TypeVar("_RepositoryT")


class _TimedRepositoryUseCase(Generic[_RepositoryT]):
    def __init__(
        self,
        repository: _RepositoryT,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))


class ExecuteDataLifecycle(_TimedRepositoryUseCase[DataLifecycleRepository]):
    def execute(self, command: DataLifecycleCommand) -> DataLifecycleOperationResult:
        return self._repository.execute_data_lifecycle(
            command,
            evaluated_at_utc=self._now(),
            evaluator=evaluate_data_lifecycle,
        )


class ReviewScheduledDataLifecycle(_TimedRepositoryUseCase[ScheduledDataLifecycleRepository]):
    def execute(self, *, limit: int) -> ScheduledLifecycleReview:
        validate_scheduled_lifecycle_review_limit(limit)
        evaluated_at_utc = self._now()
        snapshots = self._repository.scan_data_lifecycle_controls(
            evaluated_at_utc=evaluated_at_utc,
            limit=limit + 1,
        )
        return ScheduledLifecycleReview(
            evaluated_at_utc=evaluated_at_utc,
            requested_limit=limit,
            truncated=len(snapshots) > limit,
            items=tuple(
                evaluate_scheduled_lifecycle_control(
                    snapshot,
                    evaluated_at_utc=evaluated_at_utc,
                )
                for snapshot in snapshots[:limit]
            ),
        )
