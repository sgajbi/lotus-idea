from __future__ import annotations

from datetime import date, datetime

from app.domain.ideas import ReasonCode, SourceRef, UnsupportedEvidenceReason


def source_temporal_violation(
    *,
    requested_as_of_date: date,
    evaluated_at_utc: datetime,
    source_refs: tuple[SourceRef, ...],
) -> tuple[ReasonCode, UnsupportedEvidenceReason] | None:
    """Return the first deterministic source-time contract violation.

    Signal evaluation is a consumer of source-owned evidence. Exact business
    date alignment and a generated-at timestamp no later than evaluation are
    the current foundation contract; source-specific effective windows belong
    in a future versioned source contract rather than being inferred here.
    """
    for source_ref in source_refs:
        if source_ref.as_of_date != requested_as_of_date:
            return (
                ReasonCode.SOURCE_DATE_MISMATCH,
                UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
            )
        if source_ref.generated_at_utc > evaluated_at_utc:
            return (
                ReasonCode.SOURCE_GENERATED_AFTER_EVALUATION,
                UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
            )
    return None
