from __future__ import annotations

from typing import Any, Mapping

from app.domain.idempotency import IdempotencyDecision, evaluate_idempotency
from app.domain.persistence import (
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
)
from app.domain.review_governance import ReviewMutationIdentity
from app.infrastructure.postgres_candidate_detail import load_candidate_record_by_id
from app.infrastructure.postgres_idempotency_lookup import load_idempotency_record_by_key
from app.infrastructure.postgres_idempotency_reservation import reserve_replayed_idempotency
from app.infrastructure.postgres_protocols import PostgresConnection
from app.infrastructure.postgres_review_identity import (
    load_postgres_review_identity,
)


def precheck_postgres_review_mutation(
    connection: PostgresConnection,
    *,
    idempotency_key: str,
    payload: Mapping[str, Any],
    identity: ReviewMutationIdentity,
) -> ReviewPersistenceResult | None:
    idempotency_row = load_idempotency_record_by_key(connection, idempotency_key)
    if idempotency_row is not None:
        existing_idempotency, candidate_id = idempotency_row
        idempotency_decision, _ = evaluate_idempotency(
            key=idempotency_key,
            payload=dict(payload),
            existing=existing_idempotency,
        )
        record = (
            load_candidate_record_by_id(connection, candidate_id)
            if candidate_id is not None
            else None
        )
        if idempotency_decision is IdempotencyDecision.CONFLICT:
            return ReviewPersistenceResult(
                decision=ReviewPersistenceDecision.CONFLICT,
                record=record,
            )
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.REPLAYED,
            record=record,
        )

    existing_identity = load_postgres_review_identity(connection, identity)
    if existing_identity is None:
        return None
    record = load_candidate_record_by_id(connection, existing_identity.candidate_id)
    if existing_identity != identity:
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.IDENTITY_CONFLICT,
            record=record,
        )
    _, idempotency_record = evaluate_idempotency(
        key=idempotency_key,
        payload=dict(payload),
        existing=None,
    )
    reservation = reserve_replayed_idempotency(
        connection,
        record=idempotency_record,
        candidate_id=identity.candidate_id,
        occurred_at_utc=identity.occurred_at_utc,
    )
    if reservation is IdempotencyDecision.CONFLICT:
        return ReviewPersistenceResult(
            decision=ReviewPersistenceDecision.CONFLICT,
            record=record,
        )
    return ReviewPersistenceResult(
        decision=ReviewPersistenceDecision.REPLAYED,
        record=record,
    )


def precheck_postgres_conversion_mutation(
    connection: PostgresConnection,
    *,
    idempotency_key: str,
    payload: Mapping[str, Any],
) -> ConversionPersistenceResult | None:
    idempotency_row = load_idempotency_record_by_key(connection, idempotency_key)
    if idempotency_row is None:
        return None
    existing_idempotency, candidate_id = idempotency_row
    idempotency_decision, _ = evaluate_idempotency(
        key=idempotency_key,
        payload=dict(payload),
        existing=existing_idempotency,
    )
    record = (
        load_candidate_record_by_id(connection, candidate_id) if candidate_id is not None else None
    )
    if idempotency_decision is IdempotencyDecision.CONFLICT:
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.CONFLICT,
            record=record,
        )
    return ConversionPersistenceResult(
        decision=ConversionPersistenceDecision.REPLAYED,
        record=record,
    )
