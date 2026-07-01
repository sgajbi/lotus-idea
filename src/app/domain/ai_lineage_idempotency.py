from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from typing import Any, Protocol

from app.domain.ai_governance import AIExplanationResult
from app.domain.ai_lineage_persistence import (
    AIExplanationLineageRecord,
    AIExplanationLineagePersistenceDecision,
    AIExplanationLineagePersistenceResult,
)
from app.domain.idempotency import IdempotencyDecision, IdempotencyRecord, evaluate_idempotency


class AIExplanationLineageCarrier(Protocol):
    @property
    def ai_explanation_lineage_records(self) -> tuple[AIExplanationLineageRecord, ...]: ...


def record_ai_explanation_lineage_request_with_idempotency(
    result: AIExplanationResult,
    *,
    idempotency_key: str,
    payload: Mapping[str, Any],
    idempotency_records: MutableMapping[str, IdempotencyRecord],
    idempotency_candidates: MutableMapping[str, str],
    record_for_idempotency_key: Callable[[str], Any],
    record_lineage: Callable[[AIExplanationResult], AIExplanationLineagePersistenceResult],
) -> AIExplanationLineagePersistenceResult:
    if not idempotency_key.strip():
        raise ValueError("idempotency_key is required")
    idempotency_decision, idempotency_record = evaluate_idempotency(
        key=idempotency_key,
        payload=dict(payload),
        existing=idempotency_records.get(idempotency_key),
    )
    if idempotency_decision is IdempotencyDecision.CONFLICT:
        return AIExplanationLineagePersistenceResult(
            decision=AIExplanationLineagePersistenceDecision.CONFLICT,
            record=record_for_idempotency_key(idempotency_key),
            lineage_record=None,
            audit_event=None,
        )
    lineage_result = record_lineage(result)
    if idempotency_decision is IdempotencyDecision.ACCEPTED and (
        lineage_result.decision is AIExplanationLineagePersistenceDecision.ACCEPTED
    ):
        idempotency_records[idempotency_key] = idempotency_record
        idempotency_candidates[idempotency_key] = (
            lineage_result.lineage_record.candidate_id
            if lineage_result.lineage_record is not None
            else result.request.redacted_evidence.candidate_id
        )
    return lineage_result


def ai_explanation_lineage_by_request_id(
    record: AIExplanationLineageCarrier,
    request_id: str,
) -> AIExplanationLineageRecord | None:
    for lineage_record in record.ai_explanation_lineage_records:
        if lineage_record.request_id == request_id:
            return lineage_record
    return None
