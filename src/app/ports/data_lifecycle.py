from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.data_lifecycle import (
    DataLifecycleCandidateContext,
    DataLifecycleCommand,
    DataLifecycleEvaluation,
    DataLifecycleOperationResult,
)
from app.domain.data_lifecycle_schedule import ScheduledLifecycleControlSnapshot


class DataLifecycleEvaluator(Protocol):
    def __call__(
        self,
        command: DataLifecycleCommand,
        context: DataLifecycleCandidateContext,
        *,
        evaluated_at_utc: datetime,
    ) -> DataLifecycleEvaluation: ...


@runtime_checkable
class DataLifecycleRepository(Protocol):
    def execute_data_lifecycle(
        self,
        command: DataLifecycleCommand,
        *,
        evaluated_at_utc: datetime,
        evaluator: DataLifecycleEvaluator,
    ) -> DataLifecycleOperationResult: ...


@runtime_checkable
class ScheduledDataLifecycleRepository(Protocol):
    def scan_data_lifecycle_controls(
        self,
        *,
        evaluated_at_utc: datetime,
        limit: int,
    ) -> tuple[ScheduledLifecycleControlSnapshot, ...]: ...
