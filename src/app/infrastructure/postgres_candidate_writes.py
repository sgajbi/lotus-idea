from __future__ import annotations

from typing import Any, Protocol, Sequence

from psycopg.types.json import Jsonb

from app.domain import CandidatePersistenceRecord
from app.infrastructure.postgres_codecs import idea_candidate_to_json


class PostgresWriteCursor(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...


def update_postgres_candidate_record(
    cursor: PostgresWriteCursor,
    record: CandidatePersistenceRecord,
) -> None:
    candidate = record.candidate
    cursor.execute(
        """
        UPDATE idea_candidate_record
        SET family = %s,
            lifecycle_status = %s,
            review_posture = %s,
            evidence_packet_id = %s,
            evidence_hash = %s,
            candidate_json = %s,
            updated_at_utc = %s
        WHERE candidate_id = %s
        """,
        (
            candidate.family.value,
            candidate.lifecycle_status.value,
            candidate.review_posture.value,
            candidate.evidence_packet.evidence_packet_id,
            record.evidence_hash,
            Jsonb(idea_candidate_to_json(candidate)),
            candidate.updated_at_utc,
            candidate.candidate_id,
        ),
    )
