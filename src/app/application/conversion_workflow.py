from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain import (
    ConversionIntentCommand,
    ConversionIntentResult,
    ConversionOutcomeCommand,
    ConversionOutcomeResult,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    record_conversion_outcome,
    request_conversion_intent,
)
from app.ports.idea_repository import ConversionWorkflowRepository


@dataclass(frozen=True)
class RequestConversionIntentToRepositoryCommand:
    candidate_id: str
    conversion: ConversionIntentCommand
    idempotency_key: str

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class RecordConversionOutcomeToRepositoryCommand:
    conversion_intent_id: str
    outcome: ConversionOutcomeCommand
    idempotency_key: str

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.idempotency_key, "idempotency_key")


@dataclass(frozen=True)
class ConversionIntentWorkflowResult:
    conversion_result: ConversionIntentResult | None
    persistence: ConversionPersistenceResult


@dataclass(frozen=True)
class ConversionOutcomeWorkflowResult:
    outcome_result: ConversionOutcomeResult | None
    persistence: ConversionPersistenceResult


def request_conversion_intent_to_repository(
    command: RequestConversionIntentToRepositoryCommand,
    *,
    repository: ConversionWorkflowRepository,
) -> ConversionIntentWorkflowResult:
    snapshot = repository.snapshot()
    record = snapshot.candidate_records.get(command.candidate_id)
    if record is None:
        return ConversionIntentWorkflowResult(
            conversion_result=None,
            persistence=ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )

    payload = _conversion_intent_payload(command)
    prechecked = repository.precheck_conversion_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    if prechecked is not None:
        return ConversionIntentWorkflowResult(conversion_result=None, persistence=prechecked)

    conversion_result = request_conversion_intent(record.candidate, command.conversion)
    persistence = repository.record_conversion_intent(
        conversion_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    return ConversionIntentWorkflowResult(
        conversion_result=conversion_result,
        persistence=persistence,
    )


def record_conversion_outcome_to_repository(
    command: RecordConversionOutcomeToRepositoryCommand,
    *,
    repository: ConversionWorkflowRepository,
) -> ConversionOutcomeWorkflowResult:
    payload = _conversion_outcome_payload(command)
    prechecked = repository.precheck_conversion_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    if prechecked is not None:
        return ConversionOutcomeWorkflowResult(outcome_result=None, persistence=prechecked)

    conversion_intent = repository.conversion_intent_by_id(command.conversion_intent_id)
    if conversion_intent is None:
        return ConversionOutcomeWorkflowResult(
            outcome_result=None,
            persistence=ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )

    outcome_result = record_conversion_outcome(conversion_intent, command.outcome)
    persistence = repository.record_conversion_outcome(
        outcome_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    return ConversionOutcomeWorkflowResult(
        outcome_result=outcome_result,
        persistence=persistence,
    )


def _conversion_intent_payload(
    command: RequestConversionIntentToRepositoryCommand,
) -> dict[str, Any]:
    conversion = command.conversion
    return {
        "candidate_id": command.candidate_id,
        "conversion_intent_id": conversion.conversion_intent_id,
        "reason_codes": [reason.value for reason in conversion.reason_codes],
        "requested_at_utc": conversion.requested_at_utc.isoformat(),
        "target": conversion.target.value,
    }


def _conversion_outcome_payload(
    command: RecordConversionOutcomeToRepositoryCommand,
) -> dict[str, Any]:
    outcome = command.outcome
    return {
        "conversion_intent_id": command.conversion_intent_id,
        "conversion_outcome_id": outcome.conversion_outcome_id,
        "downstream_reference": outcome.downstream_reference,
        "recorded_at_utc": outcome.recorded_at_utc.isoformat(),
        "source_system": outcome.source_system.value,
        "status": outcome.status.value,
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
