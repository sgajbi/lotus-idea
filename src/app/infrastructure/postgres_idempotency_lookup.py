from __future__ import annotations

from app.domain.idempotency import IdempotencyRecord
from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection


def load_idempotency_record_by_key(
    connection: PostgresConnection,
    idempotency_key: str,
) -> tuple[IdempotencyRecord, str | None] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea idempotency-lookup */
            SELECT idempotency_key, payload_hash, candidate_id
            FROM idea_idempotency_record
            WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    row = rows[0]
    return (
        IdempotencyRecord(
            key=read_row_value(row, "idempotency_key"),
            payload_hash=read_row_value(row, "payload_hash"),
        ),
        read_row_value(row, "candidate_id"),
    )
