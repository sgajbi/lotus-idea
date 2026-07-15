from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from app.application.source_runtime_evidence.receipts import (
    is_sha256,
    persistence_receipt_is_valid,
    source_evidence_hash,
    source_receipt_is_valid,
)
from app.domain import OpportunityFamily, SourceSystem
from app.domain.proof_evidence import parse_timezone_aware_datetime


def runtime_execution_receipts_are_valid(
    execution: Mapping[str, Any],
    *,
    generated_at_utc: datetime,
    product_id: str,
    source_system: SourceSystem,
    family: OpportunityFamily,
    period_name_required: bool,
) -> bool:
    if execution.get("status") != "completed" or execution.get("durableStorageBacked") is not True:
        return False
    if tuple(execution.get("qualificationBlockers") or ()):
        return False
    evaluated_at_utc = parse_timezone_aware_datetime(execution.get("evaluatedAtUtc"))
    if evaluated_at_utc is None or evaluated_at_utc > generated_at_utc:
        return False
    try:
        as_of_date = date.fromisoformat(str(execution.get("asOfDate")))
    except ValueError:
        return False
    period_name = execution.get("periodName")
    if period_name_required and (not isinstance(period_name, str) or not period_name.strip()):
        return False
    if not is_sha256(execution.get("requestFingerprint")):
        return False
    source = execution.get("sourceReceipt")
    persistence = execution.get("persistenceReceipt")
    if not source_receipt_is_valid(
        source,
        product_id=product_id,
        source_system=source_system,
        as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
    ):
        return False
    if not persistence_receipt_is_valid(
        persistence,
        family=family,
        generated_at_utc=generated_at_utc,
    ):
        return False
    assert isinstance(source, Mapping) and isinstance(persistence, Mapping)
    return persistence.get("sourceEvidenceHash") == source_evidence_hash(source)
