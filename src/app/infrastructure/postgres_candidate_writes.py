from __future__ import annotations

from typing import Any, Protocol, Sequence

from psycopg.types.json import Jsonb

from app.domain import CandidatePersistenceRecord
from app.infrastructure.postgres_codecs import idea_candidate_to_json


class PostgresWriteCursor(Protocol):
    def execute(self, query: str, params: Sequence[Any] | None = None) -> Any: ...

    def fetchall(self) -> Sequence[Any]: ...


class StaleCandidateMutationError(RuntimeError):
    """Raised when a candidate mutation was based on a stale repository snapshot."""

    def __init__(self, candidate_id: str) -> None:
        super().__init__(f"stale candidate mutation rejected for {candidate_id}")
        self.candidate_id = candidate_id


def update_postgres_candidate_record(
    cursor: PostgresWriteCursor,
    *,
    before: CandidatePersistenceRecord,
    record: CandidatePersistenceRecord,
) -> None:
    candidate = record.candidate
    expected_updated_at_utc = before.candidate.updated_at_utc
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
          AND updated_at_utc = %s
        RETURNING candidate_id
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
            expected_updated_at_utc,
        ),
    )
    if not cursor.fetchall():
        raise StaleCandidateMutationError(candidate.candidate_id)
