from __future__ import annotations

from typing import Any, Mapping

from app.domain.conversion_outcome_policy import ConversionOutcomeIdentity
from app.domain.idempotency import (
    IdempotencyDecision,
    IdempotencyRecord,
    evaluate_idempotency,
)
from app.domain.persistence_models import (
    CandidatePersistenceRecord,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
)


def precheck_conversion_outcome_identity_mutation(
    *,
    candidate_records: Mapping[str, CandidatePersistenceRecord],
    idempotency_records: dict[str, IdempotencyRecord],
    idempotency_candidates: dict[str, str],
    idempotency_key: str,
    payload: Mapping[str, Any],
    identity: ConversionOutcomeIdentity,
) -> ConversionPersistenceResult | None:
    existing_idempotency = idempotency_records.get(idempotency_key)
    decision, idempotency_record = evaluate_idempotency(
        key=idempotency_key,
        payload=dict(payload),
        existing=existing_idempotency,
    )
    if decision in {IdempotencyDecision.CONFLICT, IdempotencyDecision.REPLAYED}:
        candidate_id = idempotency_candidates.get(idempotency_key)
        return ConversionPersistenceResult(
            decision=(
                ConversionPersistenceDecision.CONFLICT
                if decision is IdempotencyDecision.CONFLICT
                else ConversionPersistenceDecision.REPLAYED
            ),
            record=candidate_records.get(candidate_id) if candidate_id is not None else None,
        )
    return conversion_outcome_identity_result(
        candidate_records=candidate_records,
        idempotency_records=idempotency_records,
        idempotency_candidates=idempotency_candidates,
        identity=identity,
        idempotency_key=idempotency_key,
        idempotency_record=idempotency_record,
    )


def conversion_outcome_identity_result(
    *,
    candidate_records: Mapping[str, CandidatePersistenceRecord],
    idempotency_records: dict[str, IdempotencyRecord],
    idempotency_candidates: dict[str, str],
    identity: ConversionOutcomeIdentity,
    idempotency_key: str,
    idempotency_record: IdempotencyRecord,
) -> ConversionPersistenceResult | None:
    existing = _conversion_outcome_identity_record(
        candidate_records,
        identity.conversion_outcome_id,
    )
    if existing is None:
        return None
    existing_identity, record = existing
    if existing_identity != identity:
        return ConversionPersistenceResult(
            decision=ConversionPersistenceDecision.OUTCOME_CONFLICT,
            record=record,
        )
    idempotency_records[idempotency_key] = idempotency_record
    idempotency_candidates[idempotency_key] = record.candidate.candidate_id
    return ConversionPersistenceResult(
        decision=ConversionPersistenceDecision.REPLAYED,
        record=record,
    )


def _conversion_outcome_identity_record(
    candidate_records: Mapping[str, CandidatePersistenceRecord],
    conversion_outcome_id: str,
) -> tuple[ConversionOutcomeIdentity, CandidatePersistenceRecord] | None:
    for record in candidate_records.values():
        for outcome in record.conversion_outcomes:
            if outcome.outcome.conversion_outcome_id == conversion_outcome_id:
                return outcome.identity, record
    return None
