from __future__ import annotations

from psycopg.types.json import Jsonb

from app.domain.events import OutboxEventRecord
from app.infrastructure.postgres_protocols import PostgresCursor


def insert_outbox_event(cursor: PostgresCursor, event: OutboxEventRecord) -> None:
    cursor.execute(
        """
        INSERT INTO idea_outbox_event (
            outbox_event_id, event_type, aggregate_type, aggregate_id,
            schema_version, payload_json, status, occurred_at_utc,
            idempotency_fingerprint, correlation_id, causation_id,
            published_at_utc, failure_reason, retry_count, lease_owner,
            lease_attempt_id, lease_expires_at_utc
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            event.event_id,
            event.event_type,
            event.aggregate_type,
            event.aggregate_id,
            event.schema_version,
            Jsonb(dict(event.payload)),
            event.status.value,
            event.occurred_at_utc,
            event.idempotency_fingerprint,
            event.correlation_id,
            event.causation_id,
            event.published_at_utc,
            event.failure_reason,
            event.retry_count,
            event.lease_owner,
            event.lease_attempt_id,
            event.lease_expires_at_utc,
        ),
    )
