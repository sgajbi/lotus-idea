from __future__ import annotations

from datetime import datetime

from app.domain.idempotency import IdempotencyDecision, IdempotencyRecord
from app.infrastructure.postgres_idempotency_lookup import load_idempotency_record_by_key
from app.infrastructure.postgres_protocols import PostgresConnection


def reserve_replayed_idempotency(
    connection: PostgresConnection,
    *,
    record: IdempotencyRecord,
    tenant_id: str,
    candidate_id: str,
    occurred_at_utc: datetime,
) -> IdempotencyDecision:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO idea_idempotency_record (
                tenant_id, idempotency_key, operation_name, payload_hash, candidate_id,
                created_at_utc
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id, idempotency_key) WHERE tenant_id IS NOT NULL DO NOTHING
            RETURNING idempotency_key
            """,
            (
                tenant_id,
                record.key,
                record.key.split(":", 1)[0],
                record.payload_hash,
                candidate_id,
                occurred_at_utc,
            ),
        )
        inserted = bool(cursor.fetchall())
    if inserted:
        connection.commit()
        return IdempotencyDecision.ACCEPTED
    connection.rollback()
    existing = load_idempotency_record_by_key(
        connection,
        record.key,
        tenant_id=tenant_id,
    )
    if existing is None:
        raise RuntimeError("idempotency reservation collision has no durable winner")
    existing_record, existing_candidate_id = existing
    if existing_record.payload_hash != record.payload_hash or existing_candidate_id != candidate_id:
        return IdempotencyDecision.CONFLICT
    return IdempotencyDecision.REPLAYED
