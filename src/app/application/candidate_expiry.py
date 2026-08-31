from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.application.candidate_lookup import candidate_record_by_id
from app.domain import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    IdeaLifecycleStatus,
    LifecyclePersistenceResult,
    ReasonCode,
)
from app.ports.idea_repository import CandidateExpiryRepository


class CandidateExpiryDecision(StrEnum):
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    ALREADY_EXPIRED = "already_expired"
    TERMINAL_STATE_PRESERVED = "terminal_state_preserved"


@dataclass(frozen=True)
class ExpireCandidateCommand:
    candidate_id: str
    idempotency_key: str
    actor_subject: str
    evaluated_at_utc: datetime
    reason_codes: tuple[ReasonCode, ...]

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.candidate_id, "candidate_id"),
            (self.idempotency_key, "idempotency_key"),
            (self.actor_subject, "actor_subject"),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class CandidateExpiryResult:
    decision: CandidateExpiryDecision
    persistence: LifecyclePersistenceResult | None = None


def expire_candidate(
    command: ExpireCandidateCommand,
    *,
    repository: CandidateExpiryRepository,
) -> CandidateExpiryResult:
    """Retire one known opportunity without inventing source or material facts."""
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.NOT_FOUND)
    status = record.candidate.lifecycle_status
    if status is IdeaLifecycleStatus.EXPIRED:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.ALREADY_EXPIRED)
    if IdeaLifecycleStatus.EXPIRED not in ALLOWED_LIFECYCLE_TRANSITIONS[status]:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.TERMINAL_STATE_PRESERVED)

    reason_values = tuple(reason.value for reason in command.reason_codes)
    persistence = repository.record_lifecycle_transition(
        command.candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        idempotency_key=command.idempotency_key,
        payload={
            "candidate_id": command.candidate_id,
            "evaluated_at_utc": command.evaluated_at_utc.isoformat(),
            "reason_codes": list(reason_values),
            "target_status": IdeaLifecycleStatus.EXPIRED.value,
        },
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluated_at_utc,
        reason_codes=reason_values,
    )
    return CandidateExpiryResult(
        decision=CandidateExpiryDecision.EXPIRED,
        persistence=persistence,
    )


__all__ = [
    "CandidateExpiryDecision",
    "CandidateExpiryResult",
    "ExpireCandidateCommand",
    "expire_candidate",
]
