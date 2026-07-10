from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.domain.events import EventLineageContext, OutboxEventRecord, build_candidate_outbox_event


class InMemoryOutboxWriteMixin:
    _outbox_events: dict[str, OutboxEventRecord]

    def _append_outbox_event(
        self,
        *,
        event_type: str,
        aggregate_id: str,
        occurred_at_utc: datetime,
        payload: Mapping[str, str],
        idempotency_key: str,
        event_lineage: EventLineageContext | None,
    ) -> None:
        event = build_candidate_outbox_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            occurred_at_utc=occurred_at_utc,
            payload=payload,
            idempotency_key=idempotency_key,
            lineage=event_lineage,
        )
        self._outbox_events[event.event_id] = event
