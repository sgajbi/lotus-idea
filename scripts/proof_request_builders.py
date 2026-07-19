# ruff: noqa: E402
from __future__ import annotations

from datetime import date, datetime

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.ports.advise_sources import AdvisePolicyEvaluationEvidenceRequest


def build_advise_policy_evaluation_evidence_request(
    *,
    evaluation_id: str,
    as_of_date: date,
    evaluated_at_utc: datetime,
    correlation_id: str | None,
    trace_id: str | None,
) -> AdvisePolicyEvaluationEvidenceRequest:
    return AdvisePolicyEvaluationEvidenceRequest(
        evaluation_id=evaluation_id,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
