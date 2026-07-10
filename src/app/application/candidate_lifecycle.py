from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain import (
    EventLineageContext,
    IdeaLifecycleStatus,
    LifecyclePersistenceResult,
    validate_caller_settable_lifecycle_status,
)
from app.ports.idea_repository import CandidateLifecycleRepository


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


def apply_candidate_lifecycle_transition_to_repository(
    command: ApplyCandidateLifecycleTransitionCommand,
    *,
    repository: CandidateLifecycleRepository,
) -> LifecyclePersistenceResult:
    return repository.record_lifecycle_transition(
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
