from __future__ import annotations

from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection


def load_ai_lineage_identity_candidate_ids(
    connection: PostgresConnection,
    *,
    request_id: str,
    attestation_replay_nonce: str | None,
    provider_replay_nonce: str | None,
) -> tuple[str, ...]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea ai-lineage-identity-candidates */
            SELECT DISTINCT candidate_id
            FROM idea_ai_explanation_lineage
            WHERE ai_explanation_request_id = %s
               OR (%s IS NOT NULL AND lotus_ai_replay_nonce = %s)
               OR (%s IS NOT NULL AND provider_retention_replay_nonce = %s)
            ORDER BY candidate_id
            """,
            (
                request_id,
                attestation_replay_nonce,
                attestation_replay_nonce,
                provider_replay_nonce,
                provider_replay_nonce,
            ),
        )
        rows = cursor.fetchall()
    return tuple(read_row_value(row, "candidate_id") for row in rows)
