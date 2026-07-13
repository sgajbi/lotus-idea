from __future__ import annotations

from collections.abc import Callable, Iterable

from app.domain.persistence import IdeaRepositorySnapshot
from app.infrastructure.postgres_candidate_detail import load_candidate_record_for_mutation
from app.infrastructure.postgres_idempotency_lookup import load_idempotency_record_by_key
from app.infrastructure.postgres_protocols import PostgresConnection


RelatedCandidateIdsLoader = Callable[[], Iterable[str]]


def load_candidate_mutation_snapshot(
    connection: PostgresConnection,
    *,
    candidate_ids: Iterable[str],
    idempotency_key: str | None = None,
    identity_keys: Iterable[str] = (),
    related_candidate_ids_loader: RelatedCandidateIdsLoader | None = None,
) -> IdeaRepositorySnapshot:
    """Load the bounded aggregate state reachable from one mutation command."""
    requested_candidate_ids = _normalized_values(candidate_ids)
    mutation_identity_keys = _normalized_values(identity_keys)

    # Resolve once before waiting and once after identity fencing. The second
    # read observes an identity inserted by a writer that held the same lock.
    related_before = _load_related_candidate_ids(related_candidate_ids_loader)
    _acquire_advisory_locks(connection, mutation_identity_keys, seed=1199, label="identity")
    related_after = _load_related_candidate_ids(related_candidate_ids_loader)
    bounded_candidate_ids = tuple(
        sorted(set(requested_candidate_ids) | set(related_before) | set(related_after))
    )
    _acquire_advisory_locks(connection, bounded_candidate_ids, seed=1201, label="candidate")
    if idempotency_key is not None:
        _acquire_advisory_locks(
            connection,
            (idempotency_key,),
            seed=1202,
            label="idempotency",
        )

    idempotency_row = (
        load_idempotency_record_by_key(connection, idempotency_key)
        if idempotency_key is not None
        else None
    )
    candidate_ids_to_load = set(bounded_candidate_ids)
    if idempotency_row is not None and idempotency_row[1] is not None:
        candidate_ids_to_load.add(idempotency_row[1])

    candidate_records = {}
    for candidate_id in sorted(candidate_ids_to_load):
        record = load_candidate_record_for_mutation(connection, candidate_id)
        if record is not None:
            candidate_records[candidate_id] = record

    idempotency_records = {}
    idempotency_candidates = {}
    if idempotency_row is not None and idempotency_key is not None:
        idempotency_record, linked_candidate_id = idempotency_row
        idempotency_records[idempotency_key] = idempotency_record
        if linked_candidate_id is not None:
            idempotency_candidates[idempotency_key] = linked_candidate_id

    return IdeaRepositorySnapshot(
        candidate_records=candidate_records,
        idempotency_records=idempotency_records,
        idempotency_candidates=idempotency_candidates,
        conversion_intent_candidates={
            intent.intent.conversion_intent_id: candidate_id
            for candidate_id, record in candidate_records.items()
            for intent in record.conversion_intents
        },
        report_evidence_pack_candidates={
            evidence_pack.report_evidence_pack_id: candidate_id
            for candidate_id, record in candidate_records.items()
            for evidence_pack in record.report_evidence_packs
        },
        ai_explanation_lineage_candidates={
            lineage.request_id: candidate_id
            for candidate_id, record in candidate_records.items()
            for lineage in record.ai_explanation_lineage_records
        },
    )


def load_idempotency_mutation_snapshot(
    connection: PostgresConnection,
    idempotency_key: str,
) -> IdeaRepositorySnapshot:
    _acquire_advisory_locks(
        connection,
        (idempotency_key,),
        seed=1202,
        label="idempotency",
    )
    idempotency_row = load_idempotency_record_by_key(connection, idempotency_key)
    if idempotency_row is None:
        return IdeaRepositorySnapshot({}, {}, {})
    record, linked_candidate_id = idempotency_row
    return IdeaRepositorySnapshot(
        candidate_records={},
        idempotency_records={idempotency_key: record},
        idempotency_candidates=(
            {idempotency_key: linked_candidate_id} if linked_candidate_id is not None else {}
        ),
    )


def load_idempotency_replay_snapshot(
    connection: PostgresConnection,
    idempotency_key: str,
) -> IdeaRepositorySnapshot:
    idempotency_row = load_idempotency_record_by_key(connection, idempotency_key)
    if idempotency_row is None:
        return IdeaRepositorySnapshot({}, {}, {})
    idempotency_record, candidate_id = idempotency_row
    candidate_record = (
        load_candidate_record_for_mutation(connection, candidate_id)
        if candidate_id is not None
        else None
    )
    return IdeaRepositorySnapshot(
        candidate_records=(
            {candidate_id: candidate_record}
            if candidate_id is not None and candidate_record is not None
            else {}
        ),
        idempotency_records={idempotency_key: idempotency_record},
        idempotency_candidates=(
            {idempotency_key: candidate_id} if candidate_id is not None else {}
        ),
    )


def load_candidate_replay_snapshot(
    connection: PostgresConnection,
    candidate_id: str,
) -> IdeaRepositorySnapshot:
    record = load_candidate_record_for_mutation(connection, candidate_id)
    return IdeaRepositorySnapshot(
        candidate_records={candidate_id: record} if record is not None else {},
        idempotency_records={},
        idempotency_candidates={},
    )


def _load_related_candidate_ids(
    loader: RelatedCandidateIdsLoader | None,
) -> tuple[str, ...]:
    return _normalized_values(loader() if loader is not None else ())


def _normalized_values(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value.strip()}))


def _acquire_advisory_locks(
    connection: PostgresConnection,
    values: Iterable[str],
    *,
    seed: int,
    label: str,
) -> None:
    with connection.cursor() as cursor:
        for value in _normalized_values(values):
            cursor.execute(
                f"""
                /* lotus-idea aggregate-mutation-{label}-lock */
                SELECT pg_advisory_xact_lock(hashtextextended(%s, {seed}))
                """,
                (value,),
            )
