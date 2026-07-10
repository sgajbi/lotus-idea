from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.ideas import ConversionOutcomeStatus, ConversionTarget, SourceSystem


CONVERSION_OUTCOME_POLICY_VERSION = "idea-conversion-outcome-v1"


class ConversionOutcomePolicyReason(StrEnum):
    DUPLICATE_IDENTITY = "duplicate_identity"
    IDENTITY_CONFLICT = "identity_conflict"
    VERSION_CONFLICT = "version_conflict"
    OUT_OF_ORDER_EVENT = "out_of_order_event"
    INVALID_TRANSITION = "invalid_transition"
    INVALID_CORRECTION = "invalid_correction"


class ConversionOutcomePolicyViolation(ValueError):
    def __init__(self, reason: ConversionOutcomePolicyReason) -> None:
        super().__init__(reason.value)
        self.reason = reason
        self.policy_version = CONVERSION_OUTCOME_POLICY_VERSION


@dataclass(frozen=True)
class ConversionOutcomeIdentity:
    conversion_outcome_id: str
    conversion_intent_id: str
    target: ConversionTarget
    source_system: SourceSystem
    source_event_version: int
    status: ConversionOutcomeStatus
    downstream_reference: str | None
    recorded_at_utc: datetime
    actor_subject: str
    supersedes_conversion_outcome_id: str | None = None
    correction_reason: str | None = None


TERMINAL_CONVERSION_OUTCOME_STATUSES = frozenset(
    {
        ConversionOutcomeStatus.REJECTED,
        ConversionOutcomeStatus.FAILED,
        ConversionOutcomeStatus.COMPLETED,
    }
)

_INITIAL_STATUSES = frozenset(
    {
        ConversionOutcomeStatus.REQUESTED,
        ConversionOutcomeStatus.ACCEPTED,
        ConversionOutcomeStatus.REJECTED,
        ConversionOutcomeStatus.FAILED,
    }
)

_ALLOWED_NEXT_STATUSES = {
    ConversionOutcomeStatus.REQUESTED: frozenset(
        {
            ConversionOutcomeStatus.ACCEPTED,
            ConversionOutcomeStatus.REJECTED,
            ConversionOutcomeStatus.FAILED,
        }
    ),
    ConversionOutcomeStatus.ACCEPTED: frozenset({ConversionOutcomeStatus.COMPLETED}),
    ConversionOutcomeStatus.REJECTED: frozenset(),
    ConversionOutcomeStatus.FAILED: frozenset(),
    ConversionOutcomeStatus.COMPLETED: frozenset(),
}


def validate_conversion_outcome_progression(
    existing: tuple[ConversionOutcomeIdentity, ...],
    proposed: ConversionOutcomeIdentity,
) -> None:
    matching_identity = next(
        (
            outcome
            for outcome in existing
            if outcome.conversion_outcome_id == proposed.conversion_outcome_id
        ),
        None,
    )
    if matching_identity is not None:
        reason = (
            ConversionOutcomePolicyReason.DUPLICATE_IDENTITY
            if matching_identity == proposed
            else ConversionOutcomePolicyReason.IDENTITY_CONFLICT
        )
        raise ConversionOutcomePolicyViolation(reason)

    current = current_conversion_outcome_identity(existing)
    if current is None:
        _validate_initial_outcome(proposed)
        return

    _require_same_stream(current, proposed)
    if proposed.source_event_version != current.source_event_version + 1:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.VERSION_CONFLICT)
    if proposed.recorded_at_utc <= current.recorded_at_utc:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.OUT_OF_ORDER_EVENT)

    if proposed.supersedes_conversion_outcome_id is not None:
        _validate_correction(current, proposed)
        return
    if proposed.correction_reason is not None:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_CORRECTION)
    if proposed.status not in _ALLOWED_NEXT_STATUSES[current.status]:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_TRANSITION)


def current_conversion_outcome_identity(
    outcomes: tuple[ConversionOutcomeIdentity, ...],
) -> ConversionOutcomeIdentity | None:
    if not outcomes:
        return None
    return max(
        outcomes,
        key=lambda outcome: (
            outcome.source_event_version,
            outcome.recorded_at_utc,
            outcome.conversion_outcome_id,
        ),
    )


def _validate_initial_outcome(proposed: ConversionOutcomeIdentity) -> None:
    if proposed.source_event_version != 1:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.VERSION_CONFLICT)
    if (
        proposed.supersedes_conversion_outcome_id is not None
        or proposed.correction_reason is not None
    ):
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_CORRECTION)
    if proposed.status not in _INITIAL_STATUSES:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_TRANSITION)


def _require_same_stream(
    current: ConversionOutcomeIdentity,
    proposed: ConversionOutcomeIdentity,
) -> None:
    if (
        proposed.conversion_intent_id != current.conversion_intent_id
        or proposed.target is not current.target
        or proposed.source_system is not current.source_system
    ):
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.IDENTITY_CONFLICT)


def _validate_correction(
    current: ConversionOutcomeIdentity,
    proposed: ConversionOutcomeIdentity,
) -> None:
    if proposed.supersedes_conversion_outcome_id != current.conversion_outcome_id:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_CORRECTION)
    if proposed.correction_reason is None or not proposed.correction_reason.strip():
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_CORRECTION)
    if proposed.status is ConversionOutcomeStatus.REQUESTED:
        raise ConversionOutcomePolicyViolation(ConversionOutcomePolicyReason.INVALID_CORRECTION)
