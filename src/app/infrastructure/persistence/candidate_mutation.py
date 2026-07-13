from __future__ import annotations

from app.domain.persistence import IdeaRepositorySnapshot
from app.infrastructure.postgres_candidate_detail import load_candidate_record_for_mutation
from app.infrastructure.postgres_idempotency_lookup import load_idempotency_record_by_key
from app.infrastructure.postgres_protocols import PostgresConnection


def load_candidate_persistence_snapshot(
    connection: PostgresConnection,
    *,
    candidate_id: str,
    idempotency_key: str,
) -> IdeaRepositorySnapshot:
    """Load only state that can affect one candidate-persistence decision."""
    _acquire_candidate_persistence_locks(
        connection,
        candidate_id=candidate_id,
        idempotency_key=idempotency_key,
    )
    idempotency_row = load_idempotency_record_by_key(connection, idempotency_key)
    candidate_ids = {candidate_id}
    if idempotency_row is not None and idempotency_row[1] is not None:
        candidate_ids.add(idempotency_row[1])

    candidate_records = {}
    for current_candidate_id in sorted(candidate_ids):
        record = load_candidate_record_for_mutation(connection, current_candidate_id)
        if record is not None:
            candidate_records[current_candidate_id] = record

    if idempotency_row is None:
        return IdeaRepositorySnapshot(
            candidate_records=candidate_records,
            idempotency_records={},
            idempotency_candidates={},
        )

    idempotency_record, linked_candidate_id = idempotency_row
    return IdeaRepositorySnapshot(
        candidate_records=candidate_records,
        idempotency_records={idempotency_key: idempotency_record},
        idempotency_candidates=(
            {idempotency_key: linked_candidate_id} if linked_candidate_id is not None else {}
        ),
    )


def _acquire_candidate_persistence_locks(
    connection: PostgresConnection,
    *,
    candidate_id: str,
    idempotency_key: str,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea candidate-persistence-candidate-lock */
            SELECT pg_advisory_xact_lock(hashtextextended(%s, 1201))
            """,
            (candidate_id,),
        )
        cursor.execute(
            """
            /* lotus-idea candidate-persistence-idempotency-lock */
            SELECT pg_advisory_xact_lock(hashtextextended(%s, 1202))
            """,
            (idempotency_key,),
        )
