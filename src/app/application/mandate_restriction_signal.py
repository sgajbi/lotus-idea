from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    MandateRestrictionSignalInput,
    MandateRestrictionSignalPolicy,
    SignalEvaluationResult,
    SourceRef,
    evaluate_mandate_restriction_signal,
)
from app.domain.access_scope import ReviewAccessScope


@dataclass(frozen=True)
class EvaluateMandateRestrictionSignalCommand:
    as_of_date: date
    restriction_ref: SourceRef | None
    restriction_status: str | None
    changed_since_last_review: bool | None
    actionability_blocked: bool | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


DEFAULT_MANDATE_RESTRICTION_POLICY = MandateRestrictionSignalPolicy(
    policy_version="mandate-restriction-review-v1",
    candidate_score=Decimal("66"),
)


def evaluate_mandate_restriction_signal_command(
    command: EvaluateMandateRestrictionSignalCommand,
    *,
    policy: MandateRestrictionSignalPolicy = DEFAULT_MANDATE_RESTRICTION_POLICY,
) -> SignalEvaluationResult:
    source_input = MandateRestrictionSignalInput(
        as_of_date=command.as_of_date,
        restriction_ref=command.restriction_ref,
        restriction_status=command.restriction_status,
        changed_since_last_review=command.changed_since_last_review,
        actionability_blocked=command.actionability_blocked,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_mandate_restriction_signal(source_input, policy)
