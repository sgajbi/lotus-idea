from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.ideas import ConversionTarget, SourceSystem


class DownstreamSubmissionResourceType(StrEnum):
    CONVERSION_INTENT = "conversion_intent"
    REPORT_EVIDENCE_PACK = "report_evidence_pack"


class DownstreamSubmissionPosture(StrEnum):
    ACCEPTED_BY_DOWNSTREAM = "accepted_by_downstream"
    REJECTED_BY_DOWNSTREAM = "rejected_by_downstream"
    NOT_CONFIGURED = "not_configured"


@dataclass(frozen=True)
class DownstreamSubmissionRecord:
    idempotency_key: str
    request_fingerprint: str
    resource_type: DownstreamSubmissionResourceType
    resource_id: str
    target: ConversionTarget
    source_authority: SourceSystem
    status: DownstreamSubmissionPosture
    submitted_at_utc: datetime
    downstream_failure_reason: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.idempotency_key, "idempotency_key")
        _require_text(self.request_fingerprint, "request_fingerprint")
        _require_text(self.resource_id, "resource_id")
        _require_aware_utc(self.submitted_at_utc, "submitted_at_utc")
        if self.downstream_failure_reason is not None:
            _require_text(self.downstream_failure_reason, "downstream_failure_reason")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
