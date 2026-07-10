from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

from app.domain.disaster_recovery import (
    DisasterRecoveryPolicy,
    RestoreDrillEvidence,
    RestoreDrillRequest,
    evaluate_restored_database,
)
from app.ports.disaster_recovery import RestoredDatabaseInspector


class ValidateRestoredDatabase:
    def __init__(
        self,
        inspector: RestoredDatabaseInspector,
        policy: DisasterRecoveryPolicy,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._inspector = inspector
        self._policy = policy
        self._now = now or (lambda: datetime.now(UTC))

    def execute(self, request: RestoreDrillRequest) -> RestoreDrillEvidence:
        snapshot = self._inspector.inspect(expected_tables=self._policy.owned_tables)
        return evaluate_restored_database(
            request,
            snapshot,
            self._policy,
            generated_at_utc=self._now(),
        )
