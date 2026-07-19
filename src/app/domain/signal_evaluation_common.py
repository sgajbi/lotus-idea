from __future__ import annotations

from datetime import date, datetime

from app.domain.ideas import OpportunityFamily, ReasonCode, SourceRef, UnsupportedEvidenceReason
from app.domain.signal_evaluation_models import SignalEvaluationOutcome, SignalEvaluationResult
from app.domain.source_temporal import source_temporal_violation


def blocked_signal_result(
    *,
    family: OpportunityFamily,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.BLOCKED,
        family=family,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def temporal_blocked_signal_result(
    *,
    family: OpportunityFamily,
    as_of_date: date,
    evaluated_at_utc: datetime,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    violation = source_temporal_violation(
        family=family,
        requested_as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        source_refs=source_refs,
    )
    if violation is None:
        return None
    reason_code, unsupported_reason = violation
    return blocked_signal_result(
        family=family,
        reason_codes=(reason_code,),
        unsupported_reasons=(unsupported_reason,),
    )


__all__ = [
    "blocked_signal_result",
    "temporal_blocked_signal_result",
]
