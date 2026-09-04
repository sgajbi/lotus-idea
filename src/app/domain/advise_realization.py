from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class AdviseProposalRealizationStatus(StrEnum):
    ACCEPTED_FOR_REVIEW = "ACCEPTED_FOR_REVIEW"
    REJECTED_BEFORE_WORK = "REJECTED_BEFORE_WORK"
    PROPOSAL_LINKED = "PROPOSAL_LINKED"
    ADVISORY_REJECTED = "ADVISORY_REJECTED"
    ADVISORY_CANCELLED = "ADVISORY_CANCELLED"
    ADVISORY_EXPIRED = "ADVISORY_EXPIRED"
    ADVISORY_COMPLETED = "ADVISORY_COMPLETED"


class AdviseProposalReviewWorkStatus(StrEnum):
    PENDING_ADVISER_REVIEW = "PENDING_ADVISER_REVIEW"
    PROPOSAL_LINKED = "PROPOSAL_LINKED"
    CLOSED = "CLOSED"


class AdviseRealizationHistoryMutationDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


TERMINAL_ADVISE_REALIZATION_STATUSES = frozenset(
    {
        AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK,
        AdviseProposalRealizationStatus.ADVISORY_REJECTED,
        AdviseProposalRealizationStatus.ADVISORY_CANCELLED,
        AdviseProposalRealizationStatus.ADVISORY_EXPIRED,
        AdviseProposalRealizationStatus.ADVISORY_COMPLETED,
    }
)

_ALLOWED_ADVISE_REALIZATION_TRANSITIONS = {
    AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW: frozenset(
        {AdviseProposalRealizationStatus.PROPOSAL_LINKED}
    ),
    AdviseProposalRealizationStatus.PROPOSAL_LINKED: frozenset(
        {
            AdviseProposalRealizationStatus.ADVISORY_REJECTED,
            AdviseProposalRealizationStatus.ADVISORY_CANCELLED,
            AdviseProposalRealizationStatus.ADVISORY_EXPIRED,
            AdviseProposalRealizationStatus.ADVISORY_COMPLETED,
        }
    ),
    AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK: frozenset(),
    AdviseProposalRealizationStatus.ADVISORY_REJECTED: frozenset(),
    AdviseProposalRealizationStatus.ADVISORY_CANCELLED: frozenset(),
    AdviseProposalRealizationStatus.ADVISORY_EXPIRED: frozenset(),
    AdviseProposalRealizationStatus.ADVISORY_COMPLETED: frozenset(),
}


@dataclass(frozen=True)
class AdviseProposalRealizationOutcome:
    outcome_id: str
    source_event_version: int
    status: AdviseProposalRealizationStatus
    reason_code: str
    occurred_at_utc: datetime
    review_work_id: str | None
    proposal_id: str | None
    terminal: bool

    def __post_init__(self) -> None:
        _require_text(self.outcome_id, "outcome_id")
        _require_text(self.reason_code, "reason_code")
        if self.source_event_version <= 0:
            raise ValueError("source_event_version must be positive")
        _require_aware_utc(self.occurred_at_utc, "occurred_at_utc")
        if self.review_work_id is not None:
            _require_text(self.review_work_id, "review_work_id")
        if self.proposal_id is not None:
            _require_text(self.proposal_id, "proposal_id")
        if self.terminal != (self.status in TERMINAL_ADVISE_REALIZATION_STATUSES):
            raise ValueError("terminal must match Advise realization status")


@dataclass(frozen=True)
class AdviseProposalRealizationHistory:
    realization_id: str
    intake_id: str
    review_work_id: str | None
    review_work_status: AdviseProposalReviewWorkStatus | None
    source_authority: str
    realization_authority: str
    tenant_id: str
    legal_entity_code: str
    portfolio_id: str
    idea_candidate_id: str
    conversion_intent_id: str
    source_evidence_fingerprint: str
    current_status: AdviseProposalRealizationStatus
    current_source_event_version: int
    proposal_id: str | None
    proposal_record_created: bool
    suitability_authority_granted: bool
    order_created: bool
    client_publication_authorized: bool
    created_at_utc: datetime
    updated_at_utc: datetime
    outcomes: tuple[AdviseProposalRealizationOutcome, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("realization_id", self.realization_id),
            ("intake_id", self.intake_id),
            ("tenant_id", self.tenant_id),
            ("legal_entity_code", self.legal_entity_code),
            ("portfolio_id", self.portfolio_id),
            ("idea_candidate_id", self.idea_candidate_id),
            ("conversion_intent_id", self.conversion_intent_id),
            ("source_evidence_fingerprint", self.source_evidence_fingerprint),
        ):
            _require_text(value, field_name)
        if self.source_authority != "lotus-idea":
            raise ValueError("source_authority must be lotus-idea")
        if self.realization_authority != "lotus-advise":
            raise ValueError("realization_authority must be lotus-advise")
        if not self.source_evidence_fingerprint.startswith("sha256:"):
            raise ValueError("source_evidence_fingerprint must use sha256")
        if self.review_work_id is not None:
            _require_text(self.review_work_id, "review_work_id")
        if self.proposal_id is not None:
            _require_text(self.proposal_id, "proposal_id")
        if self.current_source_event_version <= 0:
            raise ValueError("current_source_event_version must be positive")
        _require_aware_utc(self.created_at_utc, "created_at_utc")
        _require_aware_utc(self.updated_at_utc, "updated_at_utc")
        if self.updated_at_utc < self.created_at_utc:
            raise ValueError("updated_at_utc must not precede created_at_utc")
        if any(
            (
                self.suitability_authority_granted,
                self.order_created,
                self.client_publication_authorized,
            )
        ):
            raise ValueError("Advise realization response asserted unsupported authority")
        object.__setattr__(self, "outcomes", tuple(self.outcomes))
        _validate_history(self)


@dataclass(frozen=True)
class AdviseRealizationHistoryMutationResult:
    decision: AdviseRealizationHistoryMutationDecision
    history: AdviseProposalRealizationHistory | None
    blocker: str | None = None
    appended_outcome_count: int = 0

    def __post_init__(self) -> None:
        if self.appended_outcome_count < 0:
            raise ValueError("appended_outcome_count must not be negative")
        if (
            self.decision is not AdviseRealizationHistoryMutationDecision.ACCEPTED
            and self.appended_outcome_count != 0
        ):
            raise ValueError("only an accepted history mutation may append outcomes")


def evaluate_advise_realization_history_mutation(
    existing: AdviseProposalRealizationHistory | None,
    proposed: AdviseProposalRealizationHistory,
) -> AdviseRealizationHistoryMutationDecision:
    if existing is None:
        return AdviseRealizationHistoryMutationDecision.ACCEPTED
    if existing == proposed:
        return AdviseRealizationHistoryMutationDecision.REPLAYED
    if _history_identity(existing) != _history_identity(proposed):
        return AdviseRealizationHistoryMutationDecision.CONFLICT
    if proposed.current_source_event_version <= existing.current_source_event_version:
        return AdviseRealizationHistoryMutationDecision.CONFLICT
    if proposed.outcomes[: len(existing.outcomes)] != existing.outcomes:
        return AdviseRealizationHistoryMutationDecision.CONFLICT
    return AdviseRealizationHistoryMutationDecision.ACCEPTED


def _history_identity(history: AdviseProposalRealizationHistory) -> tuple[str, ...]:
    return (
        history.realization_id,
        history.intake_id,
        history.source_authority,
        history.realization_authority,
        history.tenant_id,
        history.legal_entity_code,
        history.portfolio_id,
        history.idea_candidate_id,
        history.conversion_intent_id,
        history.source_evidence_fingerprint,
    )


def _validate_history(history: AdviseProposalRealizationHistory) -> None:
    if not history.outcomes:
        raise ValueError("Advise realization outcomes are required")
    if len({outcome.outcome_id for outcome in history.outcomes}) != len(history.outcomes):
        raise ValueError("Advise realization outcome identities must be unique")
    expected_versions = tuple(range(1, len(history.outcomes) + 1))
    versions = tuple(outcome.source_event_version for outcome in history.outcomes)
    if versions != expected_versions:
        raise ValueError("Advise realization event versions must be contiguous from one")
    first = history.outcomes[0]
    if first.status not in {
        AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW,
        AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK,
    }:
        raise ValueError("Advise realization history has an invalid initial status")
    for previous, current in zip(history.outcomes, history.outcomes[1:], strict=False):
        if current.status not in _ALLOWED_ADVISE_REALIZATION_TRANSITIONS[previous.status]:
            raise ValueError("Advise realization history has an invalid status transition")
        if current.occurred_at_utc < previous.occurred_at_utc:
            raise ValueError("Advise realization outcomes must be chronological")
    last = history.outcomes[-1]
    if history.current_source_event_version != last.source_event_version:
        raise ValueError("current_source_event_version must match the final outcome")
    if history.current_status is not last.status:
        raise ValueError("current_status must match the final outcome")
    if history.updated_at_utc != last.occurred_at_utc:
        raise ValueError("updated_at_utc must match the final outcome")
    if history.created_at_utc != first.occurred_at_utc:
        raise ValueError("created_at_utc must match the initial outcome")
    if history.review_work_id != last.review_work_id:
        raise ValueError("review_work_id must match the final outcome")
    _validate_work_and_proposal(history)


def _validate_work_and_proposal(history: AdviseProposalRealizationHistory) -> None:
    first = history.outcomes[0]
    last = history.outcomes[-1]
    if first.status is AdviseProposalRealizationStatus.REJECTED_BEFORE_WORK:
        if len(history.outcomes) != 1:
            raise ValueError("rejected-before-work realization cannot progress")
        if history.review_work_id is not None or history.review_work_status is not None:
            raise ValueError("rejected-before-work realization forbids review work")
    else:
        if history.review_work_id is None or history.review_work_status is None:
            raise ValueError("accepted Advise realization requires review work")
        if any(outcome.review_work_id != history.review_work_id for outcome in history.outcomes):
            raise ValueError("Advise realization review work identity changed")
    proposal_ids = {outcome.proposal_id for outcome in history.outcomes if outcome.proposal_id}
    if len(proposal_ids) > 1:
        raise ValueError("Advise realization proposal identity changed")
    linked_proposal_id = next(iter(proposal_ids), None)
    if history.proposal_id != linked_proposal_id or last.proposal_id != linked_proposal_id:
        raise ValueError("proposal_id must match the final owner outcome")
    if history.proposal_record_created != (linked_proposal_id is not None):
        raise ValueError("proposal_record_created must match proposal_id")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
