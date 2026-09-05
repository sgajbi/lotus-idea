from dataclasses import replace
from datetime import datetime

from app.domain import IdeaCandidate, SignalEvaluationResult


def accept_candidate_evaluation(
    evaluation: SignalEvaluationResult,
    *,
    accepted_at_utc: datetime,
) -> SignalEvaluationResult:
    """Bind a durable candidate mutation to Idea's trusted admission instant.

    The signal's evaluated/detected time remains the producer-observed business
    instant. Candidate and evidence creation are Idea control-plane events and
    therefore use the server acceptance time.
    """
    _require_utc(accepted_at_utc)
    candidate = evaluation.candidate
    if candidate is None:
        return evaluation
    return replace(
        evaluation,
        candidate=_candidate_at_acceptance(candidate, accepted_at_utc),
    )


def _candidate_at_acceptance(candidate: IdeaCandidate, accepted_at_utc: datetime) -> IdeaCandidate:
    return replace(
        candidate,
        evidence_packet=replace(
            candidate.evidence_packet,
            created_at_utc=accepted_at_utc,
        ),
        created_at_utc=accepted_at_utc,
        updated_at_utc=accepted_at_utc,
    )


def _require_utc(value: datetime) -> None:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None:
        raise ValueError("accepted_at_utc must be timezone-aware")
    if offset.total_seconds() != 0:
        raise ValueError("accepted_at_utc must use UTC offset +00:00")


__all__ = ["accept_candidate_evaluation"]
