from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.domain import OpportunityFamily, SignalEvaluationResult
from app.ports.evidence_payloads import source_ref_payload


def build_candidate_idempotency_payload(
    *,
    portfolio_id: str,
    as_of_date: date,
    period_name: str,
    evaluated_at_utc: datetime,
    family: OpportunityFamily,
    policy_version: str,
    evaluation: SignalEvaluationResult,
) -> dict[str, Any]:
    candidate = evaluation.candidate
    source_refs = candidate.evidence_packet.source_refs if candidate is not None else ()
    return {
        "as_of_date": as_of_date.isoformat(),
        "candidate_id": candidate.candidate_id if candidate is not None else None,
        "evaluated_at_utc": evaluated_at_utc.isoformat(),
        "family": family.value,
        "period_name": period_name,
        "portfolio_id": portfolio_id,
        "policy_version": policy_version,
        "source_signal_ids": list(candidate.source_signal_ids) if candidate is not None else [],
        "source_refs": [source_ref_payload(source_ref) for source_ref in source_refs],
    }
