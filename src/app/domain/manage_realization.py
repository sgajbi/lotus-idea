"""Manage-owned action realization history, held to the owner's exact machine.

lotus-manage owns the management-review state it creates for an accepted Idea
conversion intent (manage#660). This module models that owner truth verbatim -
the `lotus-manage.idea-action-outcome-history.v1` contract - so Idea can
reconcile the exact owner history without inferring business success from
transport. Two facts shape the model and must not be blurred:

- Review status is NOT absorbing: the owner permits APPROVED -> PENDING_REVIEW
  and REJECTED -> PENDING_REVIEW via REQUEST_CHANGES. Monotonicity therefore
  lives in the append-only event versions, never in a terminal-status flag.
- An APPROVED review outcome proves management-review posture only. The owner
  states rebalance execution, order creation, and client publication are NOT
  proven; a history claiming otherwise is refused at construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

MANAGE_ACTION_OUTCOME_HISTORY_CONTRACT_VERSION = "lotus-manage.idea-action-outcome-history.v1"


class ManageActionRealizationStatus(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ManageActionRealizationEventType(StrEnum):
    INTAKE_ACCEPTED = "INTAKE_ACCEPTED"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class ManageRealizationHistoryMutationDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


#: The owner's VALID_WORKFLOW_TRANSITIONS verbatim (lotus-manage
#: src/core/rebalance_runs/workflow.py). REQUEST_CHANGES reopens both
#: APPROVED and REJECTED - no review status is terminal.
VALID_MANAGE_REVIEW_TRANSITIONS: dict[
    tuple[ManageActionRealizationStatus, ManageActionRealizationEventType],
    ManageActionRealizationStatus,
] = {
    (
        ManageActionRealizationStatus.PENDING_REVIEW,
        ManageActionRealizationEventType.APPROVE,
    ): ManageActionRealizationStatus.APPROVED,
    (
        ManageActionRealizationStatus.PENDING_REVIEW,
        ManageActionRealizationEventType.REJECT,
    ): ManageActionRealizationStatus.REJECTED,
    (
        ManageActionRealizationStatus.PENDING_REVIEW,
        ManageActionRealizationEventType.REQUEST_CHANGES,
    ): ManageActionRealizationStatus.PENDING_REVIEW,
    (
        ManageActionRealizationStatus.APPROVED,
        ManageActionRealizationEventType.REQUEST_CHANGES,
    ): ManageActionRealizationStatus.PENDING_REVIEW,
    (
        ManageActionRealizationStatus.APPROVED,
        ManageActionRealizationEventType.REJECT,
    ): ManageActionRealizationStatus.REJECTED,
    (
        ManageActionRealizationStatus.REJECTED,
        ManageActionRealizationEventType.REQUEST_CHANGES,
    ): ManageActionRealizationStatus.PENDING_REVIEW,
}


@dataclass(frozen=True)
class ManageActionRealizationEvent:
    event_id: str
    action_id: str
    source_event_version: int
    event_type: ManageActionRealizationEventType
    previous_status: ManageActionRealizationStatus | None
    status: ManageActionRealizationStatus
    occurred_at_utc: datetime
    actor_id: str
    actor_role: str
    reason_code: str
    correlation_id: str
    causation_id: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("event_id", self.event_id),
            ("action_id", self.action_id),
            ("actor_id", self.actor_id),
            ("actor_role", self.actor_role),
            ("reason_code", self.reason_code),
            ("correlation_id", self.correlation_id),
            ("causation_id", self.causation_id),
        ):
            _require_text(value, field_name)
        if self.source_event_version <= 0:
            raise ValueError("source_event_version must be positive")
        _require_aware_utc(self.occurred_at_utc, "occurred_at_utc")


@dataclass(frozen=True)
class ManageActionRealizationHistory:
    contract_version: str
    intake_id: str
    management_action_id: str
    source_authority: str
    portfolio_id: str
    idea_candidate_id: str
    conversion_intent_id: str
    status: ManageActionRealizationStatus
    source_event_version: int
    rebalance_execution_proven: bool
    order_execution_proven: bool
    client_publication_proven: bool
    events: tuple[ManageActionRealizationEvent, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("intake_id", self.intake_id),
            ("management_action_id", self.management_action_id),
            ("portfolio_id", self.portfolio_id),
            ("idea_candidate_id", self.idea_candidate_id),
            ("conversion_intent_id", self.conversion_intent_id),
        ):
            _require_text(value, field_name)
        if self.contract_version != MANAGE_ACTION_OUTCOME_HISTORY_CONTRACT_VERSION:
            raise ValueError("contract_version is not the certified owner contract")
        if self.source_authority != "lotus-manage":
            raise ValueError("source_authority must be lotus-manage")
        if self.source_event_version <= 0:
            raise ValueError("source_event_version must be positive")
        if any(
            (
                self.rebalance_execution_proven,
                self.order_execution_proven,
                self.client_publication_proven,
            )
        ):
            raise ValueError("Manage realization response asserted unsupported authority")
        object.__setattr__(self, "events", tuple(self.events))
        _validate_history(self)


@dataclass(frozen=True)
class ManageRealizationHistoryMutationResult:
    decision: ManageRealizationHistoryMutationDecision
    history: ManageActionRealizationHistory | None
    blocker: str | None = None
    appended_event_count: int = 0

    def __post_init__(self) -> None:
        if self.appended_event_count < 0:
            raise ValueError("appended_event_count must not be negative")
        if (
            self.decision is not ManageRealizationHistoryMutationDecision.ACCEPTED
            and self.appended_event_count != 0
        ):
            raise ValueError("only an accepted history mutation may append events")


def evaluate_manage_realization_history_mutation(
    existing: ManageActionRealizationHistory | None,
    proposed: ManageActionRealizationHistory,
) -> ManageRealizationHistoryMutationDecision:
    if existing is None:
        return ManageRealizationHistoryMutationDecision.ACCEPTED
    if existing == proposed:
        return ManageRealizationHistoryMutationDecision.REPLAYED
    if _history_identity(existing) != _history_identity(proposed):
        return ManageRealizationHistoryMutationDecision.CONFLICT
    if proposed.source_event_version <= existing.source_event_version:
        return ManageRealizationHistoryMutationDecision.CONFLICT
    if proposed.events[: len(existing.events)] != existing.events:
        return ManageRealizationHistoryMutationDecision.CONFLICT
    return ManageRealizationHistoryMutationDecision.ACCEPTED


def _history_identity(history: ManageActionRealizationHistory) -> tuple[str, ...]:
    return (
        history.contract_version,
        history.intake_id,
        history.management_action_id,
        history.source_authority,
        history.portfolio_id,
        history.idea_candidate_id,
        history.conversion_intent_id,
    )


def _validate_history(history: ManageActionRealizationHistory) -> None:
    if not history.events:
        raise ValueError("Manage realization events are required")
    if len({event.event_id for event in history.events}) != len(history.events):
        raise ValueError("Manage realization event identities must be unique")
    versions = tuple(event.source_event_version for event in history.events)
    if versions != tuple(range(1, len(history.events) + 1)):
        raise ValueError("Manage realization event versions must be contiguous from one")
    first = history.events[0]
    if (
        first.event_type is not ManageActionRealizationEventType.INTAKE_ACCEPTED
        or first.previous_status is not None
        or first.status is not ManageActionRealizationStatus.PENDING_REVIEW
    ):
        raise ValueError("Manage realization history has an invalid intake event")
    for previous, current in zip(history.events, history.events[1:], strict=False):
        if current.event_type is ManageActionRealizationEventType.INTAKE_ACCEPTED:
            raise ValueError("Manage realization intake event must be first")
        if current.previous_status is not previous.status:
            raise ValueError("Manage realization event chain is not contiguous")
        expected = VALID_MANAGE_REVIEW_TRANSITIONS.get(
            (current.previous_status, current.event_type)
        )
        if expected is None or current.status is not expected:
            raise ValueError("Manage realization history has an invalid status transition")
        if current.occurred_at_utc < previous.occurred_at_utc:
            raise ValueError("Manage realization events must be chronological")
    if any(event.action_id != history.management_action_id for event in history.events):
        raise ValueError("Manage realization action identity changed")
    last = history.events[-1]
    if history.source_event_version != last.source_event_version:
        raise ValueError("source_event_version must match the final event")
    if history.status is not last.status:
        raise ValueError("status must match the final event")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
