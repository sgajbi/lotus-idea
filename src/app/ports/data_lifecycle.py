from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.data_lifecycle import (
    DataLifecycleCandidateContext,
    DataLifecycleCommand,
    DataLifecycleEvaluation,
    DataLifecycleOperationResult,
)


class DataLifecycleEvaluator(Protocol):
    def __call__(
        self,
        command: DataLifecycleCommand,
        context: DataLifecycleCandidateContext,
        *,
        evaluated_at_utc: datetime,
    ) -> DataLifecycleEvaluation: ...


class DataLifecycleRepository(Protocol):
    def execute_data_lifecycle(
        self,
        command: DataLifecycleCommand,
        *,
        evaluated_at_utc: datetime,
        evaluator: DataLifecycleEvaluator,
    ) -> DataLifecycleOperationResult: ...
