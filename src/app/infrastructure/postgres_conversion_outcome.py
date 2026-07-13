from __future__ import annotations

from typing import Any, Mapping

from psycopg.types.json import Jsonb

from app.domain.conversion_governance import GovernedConversionOutcome
from app.domain.conversion_outcome_policy import ConversionOutcomeIdentity
from app.domain.idempotency import IdempotencyDecision, evaluate_idempotency
from app.domain.persistence import (
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
)
from app.infrastructure.postgres_codecs import (
    conversion_outcome_from_json,
    conversion_outcome_to_json,
    read_json_object,
)
from app.infrastructure.postgres_downstream_lookup import (
    load_candidate_record_for_conversion_intent,
)
from app.infrastructure.postgres_idempotency_lookup import load_idempotency_record_by_key
from app.infrastructure.postgres_idempotency_reservation import reserve_replayed_idempotency
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor


class ConcurrentConversionOutcomeMutationError(RuntimeError):
    def __init__(self, identity: ConversionOutcomeIdentity) -> None:
        super().__init__(
            f"concurrent conversion outcome identity: {identity.conversion_outcome_id}"
        )
        self.identity = identity


def insert_postgres_conversion_outcome(
    cursor: PostgresCursor,
    outcome: GovernedConversionOutcome,
) -> None:
    cursor.execute(
        """
        INSERT INTO idea_conversion_outcome (
            conversion_outcome_id, conversion_intent_id, source_system,
            status, source_event_version, supersedes_conversion_outcome_id,
            correction_reason, actor_subject, outcome_json, recorded_at_utc
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING conversion_outcome_id
        """,
        (
            outcome.outcome.conversion_outcome_id,
            outcome.conversion_intent_id,
            outcome.source_system.value,
            outcome.outcome.status.value,
            outcome.source_event_version,
            outcome.supersedes_conversion_outcome_id,
            outcome.correction_reason,
            outcome.actor_subject,
            Jsonb(conversion_outcome_to_json(outcome)),
            outcome.outcome.recorded_at_utc,
        ),
    )
    if not cursor.fetchall():
        raise ConcurrentConversionOutcomeMutationError(outcome.identity)


def load_postgres_conversion_outcomes_for_intent(
    connection: PostgresConnection,
    conversion_intent_id: str,
) -> tuple[GovernedConversionOutcome, ...]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea conversion-outcome-history */
            SELECT outcome_json
            FROM idea_conversion_outcome
            WHERE conversion_intent_id = %s
            ORDER BY source_event_version, recorded_at_utc, conversion_outcome_id
            """,
            (conversion_intent_id,),
        )
        rows = cursor.fetchall()
    return tuple(
        conversion_outcome_from_json(read_json_object(row, "outcome_json")) for row in rows
    )


def precheck_postgres_conversion_outcome_mutation(
    connection: PostgresConnection,
    *,
    idempotency_key: str,
    payload: Mapping[str, Any],
    identity: ConversionOutcomeIdentity,
) -> ConversionPersistenceResult | None:
    idempotency_row = load_idempotency_record_by_key(connection, idempotency_key)
    if idempotency_row is not None:
        existing_idempotency, candidate_id = idempotency_row
        decision, _ = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        record = (
            load_candidate_record_for_conversion_intent(connection, identity.conversion_intent_id)
            if candidate_id is not None
            else None
        )
        return ConversionPersistenceResult(
            decision=(
                ConversionPersistenceDecision.CONFLICT
                if decision is IdempotencyDecision.CONFLICT
                else ConversionPersistenceDecision.REPLAYED
            ),
            record=record,
        )

    existing_identity = load_postgres_conversion_outcome_identity(
        connection,
        identity.conversion_outcome_id,
    )
    if existing_identity is None:
        return None
    record = load_candidate_record_for_conversion_intent(
        connection,
        existing_identity.conversion_intent_id,
    )
    if existing_identity != identity:
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.OUTCOME_CONFLICT,
            record=record,
        )
    _, idempotency_record = evaluate_idempotency(
        key=idempotency_key,
        payload=dict(payload),
        existing=None,
    )
    if record is not None:
        reservation = reserve_replayed_idempotency(
            connection,
            record=idempotency_record,
            candidate_id=record.candidate.candidate_id,
            occurred_at_utc=identity.recorded_at_utc,
        )
        if reservation is IdempotencyDecision.CONFLICT:
            return ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.CONFLICT,
                record=record,
            )
    return ConversionPersistenceResult(
        decision=ConversionPersistenceDecision.REPLAYED,
        record=record,
    )


def load_postgres_conversion_outcome_identity(
    connection: PostgresConnection,
    conversion_outcome_id: str,
) -> ConversionOutcomeIdentity | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            /* lotus-idea conversion-outcome-identity */
            SELECT outcome_json
            FROM idea_conversion_outcome
            WHERE conversion_outcome_id = %s
            """,
            (conversion_outcome_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return None
    return conversion_outcome_from_json(read_json_object(rows[0], "outcome_json")).identity
