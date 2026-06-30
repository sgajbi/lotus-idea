from __future__ import annotations

from datetime import UTC, datetime

from app.domain.events import OutboxEventRecord
from app.infrastructure.postgres_outbox_delivery import (
    load_outbox_delivery_readiness_summary,
    load_outbox_events_for_delivery,
)
from app.infrastructure.postgres_protocols import PostgresConnection
from app.ports.idea_repository import OutboxDeliveryReadinessRepositorySummary


class PostgresOutboxRepositoryMixin:
    _connection: PostgresConnection

    def outbox_events_for_delivery(
        self,
        *,
        limit: int = 100,
        max_retry_count: int = 3,
        evaluated_at_utc: datetime | None = None,
    ) -> tuple[OutboxEventRecord, ...]:
        return load_outbox_events_for_delivery(
            self._connection,
            limit=limit,
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at_utc or datetime.now(UTC),
        )

    def outbox_delivery_readiness_summary(
        self,
        *,
        max_retry_count: int,
        evaluated_at_utc: datetime,
    ) -> OutboxDeliveryReadinessRepositorySummary:
        return load_outbox_delivery_readiness_summary(
            self._connection,
            max_retry_count=max_retry_count,
            evaluated_at_utc=evaluated_at_utc,
        )
