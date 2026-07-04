from __future__ import annotations

from typing import Any, Mapping

from app.domain.idempotency import IdempotencyDecision, evaluate_idempotency
from app.domain.persistence import (
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
)
from app.infrastructure.postgres_candidate_detail import load_candidate_record_by_id
from app.infrastructure.postgres_idempotency_lookup import load_idempotency_record_by_key
from app.infrastructure.postgres_protocols import PostgresConnection


def precheck_postgres_review_mutation(
    connection: PostgresConnection,
    *,
    idempotency_key: str,
    payload: Mapping[str, Any],
) -> ReviewPersistenceResult | None:
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
