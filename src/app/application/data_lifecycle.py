from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

from app.domain.data_lifecycle import (
    DataLifecycleCommand,
    DataLifecycleOperationResult,
    evaluate_data_lifecycle,
)
from app.ports.data_lifecycle import DataLifecycleRepository


class ExecuteDataLifecycle:
    def __init__(
        self,
        repository: DataLifecycleRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    def execute(self, command: DataLifecycleCommand) -> DataLifecycleOperationResult:
        return self._repository.execute_data_lifecycle(
            command,
            evaluated_at_utc=self._now(),
            evaluator=evaluate_data_lifecycle,
        )
