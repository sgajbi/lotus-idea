from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.application.candidate_lookup import candidate_record_by_id
from app.domain import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    CandidatePersistenceRecord,
    EventLineageContext,
    IdeaLifecycleStatus,
    InvalidLifecycleTransition,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    ReasonCode,
)
from app.ports.idea_repository import CandidateExpiryRepository


class CandidateExpiryDecision(StrEnum):
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    ALREADY_EXPIRED = "already_expired"
    NOT_DUE = "not_due"
    TERMINAL_STATE_PRESERVED = "terminal_state_preserved"


@dataclass(frozen=True)
class ExpireCandidateCommand:
    candidate_id: str
    actor_subject: str
    evaluated_at_utc: datetime
    reason_codes: tuple[ReasonCode, ...]
    event_lineage: EventLineageContext | None = None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.candidate_id, "candidate_id"),
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
    return _expire_candidate_record(command, record=record, repository=repository)


def expire_candidate_if_due(
    command: ExpireCandidateCommand,
    *,
    repository: CandidateExpiryRepository,
) -> CandidateExpiryResult:
    """Apply a persisted applicability boundary through the governed lifecycle fence."""
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.NOT_FOUND)
    if not record.is_expired_at(command.evaluated_at_utc):
        return CandidateExpiryResult(decision=CandidateExpiryDecision.NOT_DUE)
    return _expire_candidate_record(command, record=record, repository=repository)


def _expire_candidate_record(
    command: ExpireCandidateCommand,
    *,
    record: CandidatePersistenceRecord,
    repository: CandidateExpiryRepository,
) -> CandidateExpiryResult:
    status = record.candidate.lifecycle_status
    if status is IdeaLifecycleStatus.EXPIRED:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.ALREADY_EXPIRED)
    if IdeaLifecycleStatus.EXPIRED not in ALLOWED_LIFECYCLE_TRANSITIONS[status]:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.TERMINAL_STATE_PRESERVED)

    reason_values = tuple(reason.value for reason in command.reason_codes)
    material_version = record.candidate.identity.material_version
    expiry_key = f"candidate-expiry:{command.candidate_id}:material-version:{material_version}"
    try:
        persistence = repository.record_lifecycle_transition(
            command.candidate_id,
            IdeaLifecycleStatus.EXPIRED,
            idempotency_key=expiry_key,
            payload={
                "candidate_id": command.candidate_id,
                "material_version": material_version,
                "reason_codes": list(reason_values),
                "target_status": IdeaLifecycleStatus.EXPIRED.value,
            },
            actor_subject=command.actor_subject,
            occurred_at_utc=command.evaluated_at_utc,
            reason_codes=reason_values,
            event_lineage=command.event_lineage,
        )
    except InvalidLifecycleTransition:
        return _classify_concurrent_state(repository, command.candidate_id)
    if persistence.decision is LifecyclePersistenceDecision.REPLAYED:
        return CandidateExpiryResult(
            decision=CandidateExpiryDecision.ALREADY_EXPIRED,
            persistence=persistence,
        )
    if persistence.decision is LifecyclePersistenceDecision.CONFLICT:
        concurrent = _classify_concurrent_state(repository, command.candidate_id)
        if concurrent.decision is not CandidateExpiryDecision.EXPIRED:
            return concurrent
        raise RuntimeError("candidate expiry idempotency conflict")
    return CandidateExpiryResult(
        decision=CandidateExpiryDecision.EXPIRED,
        persistence=persistence,
    )


def _classify_concurrent_state(
    repository: CandidateExpiryRepository,
    candidate_id: str,
) -> CandidateExpiryResult:
    current = candidate_record_by_id(repository, candidate_id)
    if current is None:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.NOT_FOUND)
    status = current.candidate.lifecycle_status
    if status is IdeaLifecycleStatus.EXPIRED:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.ALREADY_EXPIRED)
    if IdeaLifecycleStatus.EXPIRED not in ALLOWED_LIFECYCLE_TRANSITIONS[status]:
        return CandidateExpiryResult(decision=CandidateExpiryDecision.TERMINAL_STATE_PRESERVED)
    return CandidateExpiryResult(decision=CandidateExpiryDecision.EXPIRED)


__all__ = [
    "CandidateExpiryDecision",
    "CandidateExpiryResult",
    "ExpireCandidateCommand",
    "expire_candidate",
    "expire_candidate_if_due",
]
