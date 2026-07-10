from __future__ import annotations

from datetime import datetime, timedelta

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
    SourceSystem,
    create_downstream_submission_claim,
    finalize_downstream_submission,
)


def build_downstream_submission_record(
    *,
    idempotency_key: str,
    request_fingerprint: str,
    resource_id: str,
    submitted_at_utc: datetime,
    status: DownstreamSubmissionPosture,
    failure_reason: str | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
) -> DownstreamSubmissionRecord:
    claimed = build_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        resource_id=resource_id,
        submitted_at_utc=submitted_at_utc,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
    finalized = finalize_downstream_submission(
        claimed,
        lease_owner=claimed.lease_owner or "",
        lease_attempt_id=claimed.lease_attempt_id or "",
        posture=status,
        finalized_at_utc=submitted_at_utc,
        failure_reason=failure_reason,
    )
    assert finalized.record is not None
    return finalized.record


def build_downstream_submission_claim(
    *,
    idempotency_key: str,
    request_fingerprint: str,
    resource_id: str,
    submitted_at_utc: datetime,
    correlation_id: str | None = None,
    trace_id: str | None = None,
) -> DownstreamSubmissionRecord:
    lease_owner = "downstream-realization-test"
    lease_attempt_id = f"test-attempt-{idempotency_key}"
    return create_downstream_submission_claim(
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id=resource_id,
        target=ConversionTarget.ADVISE_PROPOSAL,
        source_authority=SourceSystem.LOTUS_ADVISE,
        actor_subject=lease_owner,
        claimed_at_utc=submitted_at_utc,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=submitted_at_utc + timedelta(seconds=1),
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
