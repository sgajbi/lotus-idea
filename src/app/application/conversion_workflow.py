from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.candidate_lookup import candidate_record_by_id
from app.application.persisted_action_evidence import (
    PersistedActionEvidenceUnavailable,
    require_single_persisted_action,
)
from app.domain import (
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeIdentity,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    EventLineageContext,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    conversion_outcome_identity_from_command,
    record_conversion_outcome,
    request_conversion_intent,
)
from app.domain.access_scope import QueueAccessScopeFilter
from app.ports.idea_repository import (
    ConversionIntentWorkflowRepository,
    ConversionOutcomeWorkflowRepository,
)


@dataclass(frozen=True)
class RequestConversionIntentToRepositoryCommand:
    candidate_id: str
    conversion: ConversionIntentCommand
    idempotency_key: str
    accepted_at_utc: datetime
    access_scope_filter: QueueAccessScopeFilter | None = None
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.idempotency_key, "idempotency_key")
        if self.conversion.idempotency_key != self.idempotency_key:
            raise ValueError("conversion idempotency key must match repository idempotency key")
        _require_aware_utc(self.accepted_at_utc, "accepted_at_utc")


@dataclass(frozen=True)
class RecordConversionOutcomeToRepositoryCommand:
    conversion_intent_id: str
    outcome: ConversionOutcomeCommand
    idempotency_key: str
    accepted_at_utc: datetime
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.idempotency_key, "idempotency_key")
        _require_aware_utc(self.accepted_at_utc, "accepted_at_utc")


@dataclass(frozen=True)
class ConversionIntentWorkflowResult:
    conversion_intent: GovernedConversionIntent | None
    persistence: ConversionPersistenceResult

    def require_conversion_intent(self) -> GovernedConversionIntent:
        if self.conversion_intent is None:
            raise PersistedActionEvidenceUnavailable(
                "Successful conversion mutation has no persisted conversion intent"
            )
        return self.conversion_intent


@dataclass(frozen=True)
class ConversionOutcomeWorkflowResult:
    conversion_outcome: GovernedConversionOutcome | None
    persistence: ConversionPersistenceResult

    def require_conversion_outcome(self) -> GovernedConversionOutcome:
        if self.conversion_outcome is None:
            raise PersistedActionEvidenceUnavailable(
                "Successful conversion mutation has no persisted conversion outcome"
            )
        return self.conversion_outcome


class ConversionAccessScopeDenied(Exception):
    """Raised when caller entitlements do not cover the target candidate scope."""


def request_conversion_intent_to_repository(
    command: RequestConversionIntentToRepositoryCommand,
    *,
    repository: ConversionIntentWorkflowRepository,
) -> ConversionIntentWorkflowResult:
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return ConversionIntentWorkflowResult(
            conversion_intent=None,
            persistence=ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )
    if command.access_scope_filter is None or not command.access_scope_filter.matches(
        record.candidate.access_scope
    ):
        raise ConversionAccessScopeDenied

    payload = _conversion_intent_payload(command)
    prechecked = repository.precheck_conversion_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
    )
    if prechecked is not None:
        return ConversionIntentWorkflowResult(
            conversion_intent=_persisted_conversion_intent(command, prechecked),
            persistence=prechecked,
        )

    conversion_result = request_conversion_intent(
        record.candidate,
        command.conversion,
        accepted_at_utc=command.accepted_at_utc,
    )
    persistence = repository.record_conversion_intent(
        conversion_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return ConversionIntentWorkflowResult(
        conversion_intent=_persisted_conversion_intent(command, persistence),
        persistence=persistence,
    )


def _persisted_conversion_intent(
    command: RequestConversionIntentToRepositoryCommand,
    persistence: ConversionPersistenceResult,
) -> GovernedConversionIntent | None:
    if persistence.decision not in {
        ConversionPersistenceDecision.ACCEPTED,
        ConversionPersistenceDecision.REPLAYED,
    }:
        return None
    record = persistence.record
    if record is None or record.candidate.candidate_id != command.candidate_id:
        raise PersistedActionEvidenceUnavailable(
            "Successful conversion mutation has no matching candidate record"
        )
    requested = command.conversion
    return require_single_persisted_action(
        intent
        for intent in record.conversion_intents
        if (
            intent.intent.conversion_intent_id == requested.conversion_intent_id
            and intent.intent.candidate_id == command.candidate_id
            and intent.intent.target is requested.target
            and intent.intent.requested_at_utc == requested.requested_at_utc
            and intent.actor_subject == requested.actor_subject
            and intent.idempotency_key == command.idempotency_key
            and intent.reason_codes == requested.reason_codes
        )
    )


def record_conversion_outcome_to_repository(
    command: RecordConversionOutcomeToRepositoryCommand,
    *,
    repository: ConversionOutcomeWorkflowRepository,
) -> ConversionOutcomeWorkflowResult:
    conversion_intent = repository.conversion_intent_by_id(command.conversion_intent_id)
    if conversion_intent is None:
        return ConversionOutcomeWorkflowResult(
            conversion_outcome=None,
            persistence=ConversionPersistenceResult(
                decision=ConversionPersistenceDecision.NOT_FOUND,
                record=None,
            ),
        )

    payload = _conversion_outcome_payload(command)
    identity = conversion_outcome_identity_from_command(conversion_intent, command.outcome)
    prechecked = repository.precheck_conversion_outcome_mutation(
        idempotency_key=command.idempotency_key,
        payload=payload,
        identity=identity,
    )
    if prechecked is not None:
        return ConversionOutcomeWorkflowResult(
            conversion_outcome=_persisted_conversion_outcome(command, prechecked, identity),
            persistence=prechecked,
        )

    existing_outcomes = repository.conversion_outcomes_for_intent(command.conversion_intent_id)
    outcome_result = record_conversion_outcome(
        conversion_intent,
        command.outcome,
        accepted_at_utc=command.accepted_at_utc,
        existing_outcomes=existing_outcomes,
    )
    persistence = repository.record_conversion_outcome(
        outcome_result,
        idempotency_key=command.idempotency_key,
        payload=payload,
        event_lineage=command.event_lineage,
    )
    return ConversionOutcomeWorkflowResult(
        conversion_outcome=_persisted_conversion_outcome(command, persistence, identity),
        persistence=persistence,
    )


def _persisted_conversion_outcome(
    command: RecordConversionOutcomeToRepositoryCommand,
    persistence: ConversionPersistenceResult,
    identity: ConversionOutcomeIdentity,
) -> GovernedConversionOutcome | None:
    if persistence.decision not in {
        ConversionPersistenceDecision.ACCEPTED,
        ConversionPersistenceDecision.REPLAYED,
    }:
        return None
    record = persistence.record
    if record is None:
        raise PersistedActionEvidenceUnavailable(
            "Successful conversion outcome mutation has no candidate record"
        )
    return require_single_persisted_action(
        outcome
        for outcome in record.conversion_outcomes
        if (
            outcome.conversion_intent_id == command.conversion_intent_id
            and outcome.identity == identity
        )
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
        "actor_subject": outcome.actor_subject,
        "downstream_reference": outcome.downstream_reference,
        "recorded_at_utc": outcome.recorded_at_utc.isoformat(),
        "source_system": outcome.source_system.value,
        "source_event_version": outcome.source_event_version,
        "status": outcome.status.value,
        "supersedes_conversion_outcome_id": outcome.supersedes_conversion_outcome_id,
        "correction_reason": outcome.correction_reason,
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
