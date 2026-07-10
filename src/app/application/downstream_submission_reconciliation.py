from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    SourceSystem,
)
from app.ports.idea_repository import DownstreamSubmissionRepository


class DownstreamSubmissionReconciliationStatus(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    NOT_ELIGIBLE = "not_eligible"


@dataclass(frozen=True)
class DownstreamSubmissionReconciliationSummary:
    support_reference: str
    resource_type: DownstreamSubmissionResourceType
    target: ConversionTarget
    source_authority: SourceSystem
    submission_posture: DownstreamSubmissionPosture
    attempt_count: int
    submitted_at_utc: datetime
    updated_at_utc: datetime
    lease_expires_at_utc: datetime | None
    downstream_failure_reason: str | None
    audit_entry_count: int
    reconciliation_eligible: bool
    owner: str = "lotus-idea-operations"


@dataclass(frozen=True)
class DownstreamSubmissionReconciliationResult:
    status: DownstreamSubmissionReconciliationStatus
    summary: DownstreamSubmissionReconciliationSummary | None
    blocker: str | None = None


def list_downstream_submissions_requiring_reconciliation(
    repository: DownstreamSubmissionRepository,
    *,
    limit: int = 100,
) -> tuple[DownstreamSubmissionReconciliationSummary, ...]:
    return tuple(
        _summary(record)
        for record in repository.downstream_submissions_requiring_reconciliation(limit=limit)
    )


def reconcile_uncertain_downstream_submission(
    repository: DownstreamSubmissionRepository,
    *,
    support_reference: str,
    resolution: DownstreamSubmissionResolution,
    actor_subject: str,
    reason: str,
    change_reference: str,
    reconciled_at_utc: datetime | None = None,
) -> DownstreamSubmissionReconciliationResult:
    result = repository.reconcile_downstream_submission(
        support_reference=support_reference,
        resolution=resolution,
        actor_subject=actor_subject,
        reason=reason,
        change_reference=change_reference,
        reconciled_at_utc=reconciled_at_utc or datetime.now(UTC),
    )
    status_by_decision = {
        DownstreamSubmissionMutationDecision.ACCEPTED: (
            DownstreamSubmissionReconciliationStatus.ACCEPTED
        ),
        DownstreamSubmissionMutationDecision.REPLAYED: (
            DownstreamSubmissionReconciliationStatus.REPLAYED
        ),
        DownstreamSubmissionMutationDecision.NOT_FOUND: (
            DownstreamSubmissionReconciliationStatus.NOT_FOUND
        ),
        DownstreamSubmissionMutationDecision.LEASE_CONFLICT: (
            DownstreamSubmissionReconciliationStatus.CONFLICT
        ),
        DownstreamSubmissionMutationDecision.INVALID_STATE: (
            DownstreamSubmissionReconciliationStatus.NOT_ELIGIBLE
        ),
    }
    return DownstreamSubmissionReconciliationResult(
        status=status_by_decision[result.decision],
        summary=_summary(result.record) if result.record is not None else None,
        blocker=result.blocker,
    )


def _summary(record: DownstreamSubmissionRecord) -> DownstreamSubmissionReconciliationSummary:
    return DownstreamSubmissionReconciliationSummary(
        support_reference=record.support_reference,
        resource_type=record.resource_type,
        target=record.target,
        source_authority=record.source_authority,
        submission_posture=record.status,
        attempt_count=record.attempt_count,
        submitted_at_utc=record.submitted_at_utc,
        updated_at_utc=record.updated_at_utc,
        lease_expires_at_utc=record.lease_expires_at_utc,
        downstream_failure_reason=record.downstream_failure_reason,
        audit_entry_count=len(record.audit_history),
        reconciliation_eligible=record.status
        in {
            DownstreamSubmissionPosture.IN_FLIGHT,
            DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        },
    )
