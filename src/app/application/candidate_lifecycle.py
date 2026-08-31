from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.application.persisted_action_evidence import (
    PersistedActionEvidenceUnavailable,
    require_single_persisted_action,
)
from app.domain import (
    EventLineageContext,
    IdeaLifecycleStatus,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    validate_caller_settable_lifecycle_status,
)
from app.domain.audit import AuditEvent
from app.ports.idea_repository import CandidateLifecycleRepository


_LIFECYCLE_TRANSITION_AUDIT_EVENT = "idea.lifecycle.transitioned"


@dataclass(frozen=True)
class ApplyCandidateLifecycleTransitionCommand:
    candidate_id: str
    transition_id: str
    target_status: IdeaLifecycleStatus
    changed_at_utc: datetime
    reason_codes: tuple[str, ...]
    actor_subject: str
    idempotency_key: str
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.transition_id, "transition_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_text(self.idempotency_key, "idempotency_key")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        if any(not reason_code.strip() for reason_code in self.reason_codes):
            raise ValueError("reason_codes cannot contain blank values")
        validate_caller_settable_lifecycle_status(self.target_status)
        if self.changed_at_utc.tzinfo is None or self.changed_at_utc.utcoffset() is None:
            raise ValueError("changed_at_utc must be timezone-aware")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class PersistedLifecycleTransition:
    transition_id: str
    candidate_id: str
    lifecycle_status: IdeaLifecycleStatus
    changed_at_utc: datetime
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CandidateLifecycleTransitionWorkflowResult:
    transition: PersistedLifecycleTransition | None
    persistence: LifecyclePersistenceResult

    def require_transition(self) -> PersistedLifecycleTransition:
        if self.transition is None:
            raise PersistedActionEvidenceUnavailable(
                "Successful lifecycle mutation has no persisted transition"
            )
        return self.transition


def apply_candidate_lifecycle_transition_to_repository(
    command: ApplyCandidateLifecycleTransitionCommand,
    *,
    repository: CandidateLifecycleRepository,
) -> CandidateLifecycleTransitionWorkflowResult:
    persistence = repository.record_lifecycle_transition(
        command.candidate_id,
        command.target_status,
        idempotency_key=command.idempotency_key,
        payload=_lifecycle_payload(command),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.changed_at_utc,
        transition_id=command.transition_id,
        reason_codes=command.reason_codes,
        event_lineage=command.event_lineage,
    )
    return CandidateLifecycleTransitionWorkflowResult(
        transition=_persisted_lifecycle_transition(command, persistence),
        persistence=persistence,
    )


def _persisted_lifecycle_transition(
    command: ApplyCandidateLifecycleTransitionCommand,
    persistence: LifecyclePersistenceResult,
) -> PersistedLifecycleTransition | None:
    if persistence.decision not in {
        LifecyclePersistenceDecision.ACCEPTED,
        LifecyclePersistenceDecision.REPLAYED,
    }:
        return None
    record = persistence.record
    if record is None or record.candidate.candidate_id != command.candidate_id:
        raise PersistedActionEvidenceUnavailable(
            "Successful lifecycle mutation has no matching candidate record"
        )
    audit_event = require_single_persisted_action(
        event
        for event in record.audit_events
        if event.event_type == _LIFECYCLE_TRANSITION_AUDIT_EVENT
        and event.attributes.get("transition_id") == command.transition_id
    )
    return _lifecycle_transition_from_audit_event(
        audit_event,
        command=command,
    )


def _lifecycle_transition_from_audit_event(
    audit_event: AuditEvent,
    *,
    command: ApplyCandidateLifecycleTransitionCommand,
) -> PersistedLifecycleTransition:
    try:
        if audit_event.outcome != "accepted":
            raise ValueError("unexpected audit outcome")
        IdeaLifecycleStatus(audit_event.attributes["source_status"])
        target_status = IdeaLifecycleStatus(audit_event.attributes["target_status"])
        reason_codes = tuple(audit_event.attributes["reason_codes"].split(","))
        if not reason_codes or any(not reason_code.strip() for reason_code in reason_codes):
            raise ValueError("invalid persisted reason codes")
        if (
            target_status is not command.target_status
            or audit_event.occurred_at_utc != command.changed_at_utc
            or reason_codes != command.reason_codes
        ):
            raise ValueError("persisted lifecycle transition contradicts the command")
    except (KeyError, ValueError) as exc:
        raise PersistedActionEvidenceUnavailable(
            "Persisted lifecycle transition evidence is malformed"
        ) from exc
    return PersistedLifecycleTransition(
        transition_id=command.transition_id,
        candidate_id=command.candidate_id,
        lifecycle_status=target_status,
        changed_at_utc=audit_event.occurred_at_utc,
        reason_codes=reason_codes,
    )


def _lifecycle_payload(command: ApplyCandidateLifecycleTransitionCommand) -> dict[str, Any]:
    return {
        "candidate_id": command.candidate_id,
        "changed_at_utc": command.changed_at_utc.isoformat(),
        "reason_codes": list(command.reason_codes),
        "target_status": command.target_status.value,
        "transition_id": command.transition_id,
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
