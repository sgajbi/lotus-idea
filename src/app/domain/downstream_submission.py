from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
import hashlib

from app.domain.ideas import ConversionTarget, SourceSystem


DOWNSTREAM_SUBMISSION_SUPPORT_PREFIX = "downstream-submission-"


class DownstreamSubmissionResourceType(StrEnum):
    CONVERSION_INTENT = "conversion_intent"
    REPORT_EVIDENCE_PACK = "report_evidence_pack"


class DownstreamSubmissionPosture(StrEnum):
    IN_FLIGHT = "in_flight"
    ACCEPTED_BY_DOWNSTREAM = "accepted_by_downstream"
    REJECTED_BY_DOWNSTREAM = "rejected_by_downstream"
    NOT_CONFIGURED = "not_configured"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    QUARANTINED = "quarantined"


class DownstreamSubmissionAuditAction(StrEnum):
    CLAIMED = "claimed"
    FINALIZED = "finalized"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    RECONCILED = "reconciled"
    QUARANTINED = "quarantined"


class DownstreamSubmissionClaimDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    CONFLICT = "conflict"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class DownstreamSubmissionMutationDecision(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"
    LEASE_CONFLICT = "lease_conflict"
    INVALID_STATE = "invalid_state"


class DownstreamSubmissionResolution(StrEnum):
    ACCEPTED_BY_DOWNSTREAM = "accepted_by_downstream"
    REJECTED_BY_DOWNSTREAM = "rejected_by_downstream"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class ReportMaterializationReceiptEvidence:
    """Report-owned materialization facts returned with an accepted submission."""

    status: str
    materialization_status: str
    status_url: str
    report_evidence_pack_id: str
    conversion_intent_id: str
    candidate_id: str
    evidence_packet_id: str
    creates_report_job: bool
    creates_rendered_output: bool
    creates_archive_record: bool
    render_job_id: str | None
    archive_document_id: str | None
    supportability_status: str
    remaining_blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("status", self.status),
            ("materialization_status", self.materialization_status),
            ("status_url", self.status_url),
            ("report_evidence_pack_id", self.report_evidence_pack_id),
            ("conversion_intent_id", self.conversion_intent_id),
            ("candidate_id", self.candidate_id),
            ("evidence_packet_id", self.evidence_packet_id),
            ("supportability_status", self.supportability_status),
        ):
            _require_text(value, field_name)
        if not self.creates_report_job:
            raise ValueError("report materialization receipt must create a report job")
        if self.creates_rendered_output != (self.render_job_id is not None):
            raise ValueError("render creation posture must match render_job_id")
        if self.creates_archive_record != (self.archive_document_id is not None):
            raise ValueError("archive creation posture must match archive_document_id")
        if self.creates_archive_record and not self.creates_rendered_output:
            raise ValueError("an archive record requires rendered output")
        if not self.remaining_blockers:
            raise ValueError("remaining_blockers is required")
        for blocker in self.remaining_blockers:
            _require_text(blocker, "remaining_blocker")
        object.__setattr__(self, "remaining_blockers", tuple(self.remaining_blockers))
        if self.status != self.materialization_status:
            raise ValueError("Report materialization status fields must agree")
        if self.supportability_status != "not_certified":
            raise ValueError("Report materialization must remain not_certified")
        if not {
            "client_publication_authority_blocked",
            "supported_feature_promotion_missing",
        }.issubset(self.remaining_blockers):
            raise ValueError("Report materialization omits required supportability blockers")


@dataclass(frozen=True)
class DownstreamSubmissionOwnerReceipt:
    owner_authority: SourceSystem
    owner_request_id: str
    owner_realization_id: str
    owner_work_id: str | None
    source_event_version: int | None
    source_evidence_fingerprint: str
    report_materialization: ReportMaterializationReceiptEvidence | None = None

    def __post_init__(self) -> None:
        _require_text(self.owner_request_id, "owner_request_id")
        _require_text(self.owner_realization_id, "owner_realization_id")
        if self.owner_work_id is not None:
            _require_text(self.owner_work_id, "owner_work_id")
        if self.source_event_version is not None and self.source_event_version <= 0:
            raise ValueError("source_event_version must be positive when present")
        _require_text(self.source_evidence_fingerprint, "source_evidence_fingerprint")
        if not self.source_evidence_fingerprint.startswith("sha256:"):
            raise ValueError("source_evidence_fingerprint must use sha256")
        if self.owner_authority is SourceSystem.LOTUS_REPORT:
            if self.source_event_version is not None:
                raise ValueError("Report materialization receipt has no source event version")
            if self.report_materialization is None:
                raise ValueError("Report owner receipt requires materialization evidence")
            if self.owner_work_id is not None:
                raise ValueError("Report materialization uses owner_realization_id for the job")
            if self.report_materialization.status_url != (
                f"/reports/jobs/{self.owner_realization_id}"
            ):
                raise ValueError(
                    "Report materialization status_url must match owner_realization_id"
                )
        elif self.source_event_version is None:
            raise ValueError("evented owner receipt requires source_event_version")
        elif self.report_materialization is not None:
            raise ValueError("report materialization evidence requires lotus-report authority")


@dataclass(frozen=True)
class DownstreamSubmissionAuditEntry:
    audit_id: str
    action: DownstreamSubmissionAuditAction
    actor_subject: str
    current_posture: DownstreamSubmissionPosture
    occurred_at_utc: datetime
    previous_posture: DownstreamSubmissionPosture | None = None
    reason: str | None = None
    change_reference: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.audit_id, "audit_id")
        _require_text(self.actor_subject, "actor_subject")
        _require_aware_utc(self.occurred_at_utc, "occurred_at_utc")
        if self.reason is not None:
            _require_text(self.reason, "reason")
        if self.change_reference is not None:
            _require_text(self.change_reference, "change_reference")


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
    support_reference: str
    attempt_count: int
    updated_at_utc: datetime
    audit_history: tuple[DownstreamSubmissionAuditEntry, ...]
    downstream_failure_reason: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None
    lease_owner: str | None = None
    lease_attempt_id: str | None = None
    lease_expires_at_utc: datetime | None = None
    owner_receipt: DownstreamSubmissionOwnerReceipt | None = None

    def __post_init__(self) -> None:
        _require_text(self.idempotency_key, "idempotency_key")
        _require_text(self.request_fingerprint, "request_fingerprint")
        _require_text(self.resource_id, "resource_id")
        _require_text(self.support_reference, "support_reference")
        if self.support_reference != downstream_submission_support_reference(self.idempotency_key):
            raise ValueError("support_reference must match idempotency_key")
        _require_aware_utc(self.submitted_at_utc, "submitted_at_utc")
        _require_aware_utc(self.updated_at_utc, "updated_at_utc")
        if self.attempt_count <= 0:
            raise ValueError("attempt_count must be positive")
        if not self.audit_history:
            raise ValueError("audit_history is required")
        if self.downstream_failure_reason is not None:
            _require_text(self.downstream_failure_reason, "downstream_failure_reason")
        _validate_lease(self)
        _validate_posture(self)


@dataclass(frozen=True)
class DownstreamSubmissionClaimResult:
    decision: DownstreamSubmissionClaimDecision
    record: DownstreamSubmissionRecord | None


@dataclass(frozen=True)
class DownstreamSubmissionMutationResult:
    decision: DownstreamSubmissionMutationDecision
    record: DownstreamSubmissionRecord | None
    blocker: str | None = None


def downstream_submission_sort_key(
    record: DownstreamSubmissionRecord,
) -> tuple[datetime, str, str, str, datetime]:
    """Return the provider-neutral ordering for candidate submission posture."""
    return (
        record.submitted_at_utc,
        record.resource_type.value,
        record.resource_id,
        record.target.value,
        record.updated_at_utc,
    )


def downstream_submission_support_reference(idempotency_key: str) -> str:
    _require_text(idempotency_key, "idempotency_key")
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
    return f"{DOWNSTREAM_SUBMISSION_SUPPORT_PREFIX}{digest}"


def create_downstream_submission_claim(
    *,
    idempotency_key: str,
    request_fingerprint: str,
    resource_type: DownstreamSubmissionResourceType,
    resource_id: str,
    target: ConversionTarget,
    source_authority: SourceSystem,
    actor_subject: str,
    claimed_at_utc: datetime,
    lease_owner: str,
    lease_attempt_id: str,
    lease_expires_at_utc: datetime,
    correlation_id: str | None = None,
    trace_id: str | None = None,
) -> DownstreamSubmissionRecord:
    audit = _audit_entry(
        idempotency_key=idempotency_key,
        sequence=1,
        action=DownstreamSubmissionAuditAction.CLAIMED,
        actor_subject=actor_subject,
        current_posture=DownstreamSubmissionPosture.IN_FLIGHT,
        occurred_at_utc=claimed_at_utc,
    )
    return DownstreamSubmissionRecord(
        idempotency_key=idempotency_key,
        request_fingerprint=request_fingerprint,
        resource_type=resource_type,
        resource_id=resource_id,
        target=target,
        source_authority=source_authority,
        status=DownstreamSubmissionPosture.IN_FLIGHT,
        submitted_at_utc=claimed_at_utc,
        support_reference=downstream_submission_support_reference(idempotency_key),
        attempt_count=1,
        updated_at_utc=claimed_at_utc,
        audit_history=(audit,),
        correlation_id=correlation_id,
        trace_id=trace_id,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=lease_expires_at_utc,
    )


def evaluate_downstream_submission_claim(
    existing: DownstreamSubmissionRecord | None,
    *,
    request_fingerprint: str,
) -> DownstreamSubmissionClaimDecision:
    if existing is None:
        return DownstreamSubmissionClaimDecision.ACCEPTED
    if existing.request_fingerprint != request_fingerprint:
        return DownstreamSubmissionClaimDecision.CONFLICT
    if existing.status in {
        DownstreamSubmissionPosture.IN_FLIGHT,
        DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        DownstreamSubmissionPosture.QUARANTINED,
    }:
        return DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED
    return DownstreamSubmissionClaimDecision.REPLAYED


def finalize_downstream_submission(
    record: DownstreamSubmissionRecord,
    *,
    lease_owner: str,
    lease_attempt_id: str,
    posture: DownstreamSubmissionPosture,
    finalized_at_utc: datetime,
    failure_reason: str | None = None,
    owner_receipt: DownstreamSubmissionOwnerReceipt | None = None,
) -> DownstreamSubmissionMutationResult:
    lease_error = _lease_blocker(record, lease_owner, lease_attempt_id)
    if lease_error is not None:
        return DownstreamSubmissionMutationResult(
            decision=DownstreamSubmissionMutationDecision.LEASE_CONFLICT,
            record=record,
            blocker=lease_error,
        )
    if record.status is not DownstreamSubmissionPosture.IN_FLIGHT:
        return DownstreamSubmissionMutationResult(
            decision=DownstreamSubmissionMutationDecision.INVALID_STATE,
            record=record,
            blocker="downstream_submission_not_in_flight",
        )
    if posture not in {
        DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.NOT_CONFIGURED,
        DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
    }:
        raise ValueError("unsupported downstream submission final posture")
    if owner_receipt is not None:
        if posture not in {
            DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        }:
            raise ValueError("owner_receipt requires a terminal downstream posture")
        if owner_receipt.owner_authority is not record.source_authority:
            raise ValueError("owner_receipt authority must match source_authority")
    action = (
        DownstreamSubmissionAuditAction.RECONCILIATION_REQUIRED
        if posture is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED
        else DownstreamSubmissionAuditAction.FINALIZED
    )
    updated = _transition_record(
        record,
        posture=posture,
        action=action,
        actor_subject=lease_owner,
        occurred_at_utc=finalized_at_utc,
        reason=failure_reason,
        record_failure_reason=failure_reason,
        owner_receipt=owner_receipt,
    )
    return DownstreamSubmissionMutationResult(
        decision=DownstreamSubmissionMutationDecision.ACCEPTED,
        record=updated,
    )


def reconcile_downstream_submission(
    record: DownstreamSubmissionRecord,
    *,
    resolution: DownstreamSubmissionResolution,
    actor_subject: str,
    reason: str,
    change_reference: str,
    reconciled_at_utc: datetime,
) -> DownstreamSubmissionMutationResult:
    _require_text(actor_subject, "actor_subject")
    _require_text(reason, "reason")
    _require_text(change_reference, "change_reference")
    _require_aware_utc(reconciled_at_utc, "reconciled_at_utc")
    posture = DownstreamSubmissionPosture(resolution.value)
    last_audit = record.audit_history[-1]
    if last_audit.change_reference == change_reference:
        if (
            last_audit.current_posture is posture
            and last_audit.actor_subject == actor_subject
            and last_audit.reason == reason
        ):
            return DownstreamSubmissionMutationResult(
                decision=DownstreamSubmissionMutationDecision.REPLAYED,
                record=record,
            )
        return DownstreamSubmissionMutationResult(
            decision=DownstreamSubmissionMutationDecision.INVALID_STATE,
            record=record,
            blocker="downstream_submission_change_reference_conflict",
        )
    if record.status not in {
        DownstreamSubmissionPosture.IN_FLIGHT,
        DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
    }:
        return DownstreamSubmissionMutationResult(
            decision=DownstreamSubmissionMutationDecision.INVALID_STATE,
            record=record,
            blocker="downstream_submission_not_reconcilable",
        )
    action = (
        DownstreamSubmissionAuditAction.QUARANTINED
        if resolution is DownstreamSubmissionResolution.QUARANTINED
        else DownstreamSubmissionAuditAction.RECONCILED
    )
    updated = _transition_record(
        record,
        posture=posture,
        action=action,
        actor_subject=actor_subject,
        occurred_at_utc=reconciled_at_utc,
        reason=reason,
        record_failure_reason=(
            None if resolution is DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM else reason
        ),
        change_reference=change_reference,
    )
    return DownstreamSubmissionMutationResult(
        decision=DownstreamSubmissionMutationDecision.ACCEPTED,
        record=updated,
    )


def _transition_record(
    record: DownstreamSubmissionRecord,
    *,
    posture: DownstreamSubmissionPosture,
    action: DownstreamSubmissionAuditAction,
    actor_subject: str,
    occurred_at_utc: datetime,
    reason: str | None,
    record_failure_reason: str | None = None,
    change_reference: str | None = None,
    owner_receipt: DownstreamSubmissionOwnerReceipt | None = None,
) -> DownstreamSubmissionRecord:
    audit = _audit_entry(
        idempotency_key=record.idempotency_key,
        sequence=len(record.audit_history) + 1,
        action=action,
        actor_subject=actor_subject,
        previous_posture=record.status,
        current_posture=posture,
        occurred_at_utc=occurred_at_utc,
        reason=reason,
        change_reference=change_reference,
    )
    return replace(
        record,
        status=posture,
        updated_at_utc=occurred_at_utc,
        downstream_failure_reason=record_failure_reason,
        audit_history=(*record.audit_history, audit),
        owner_receipt=owner_receipt if owner_receipt is not None else record.owner_receipt,
    )


def _audit_entry(
    *,
    idempotency_key: str,
    sequence: int,
    action: DownstreamSubmissionAuditAction,
    actor_subject: str,
    current_posture: DownstreamSubmissionPosture,
    occurred_at_utc: datetime,
    previous_posture: DownstreamSubmissionPosture | None = None,
    reason: str | None = None,
    change_reference: str | None = None,
) -> DownstreamSubmissionAuditEntry:
    identity = hashlib.sha256(
        f"{idempotency_key}:{sequence}:{action.value}".encode("utf-8")
    ).hexdigest()[:24]
    return DownstreamSubmissionAuditEntry(
        audit_id=f"downstream-audit-{identity}",
        action=action,
        actor_subject=actor_subject,
        previous_posture=previous_posture,
        current_posture=current_posture,
        occurred_at_utc=occurred_at_utc,
        reason=reason,
        change_reference=change_reference,
    )


def _validate_lease(record: DownstreamSubmissionRecord) -> None:
    lease_values = (record.lease_owner, record.lease_attempt_id, record.lease_expires_at_utc)
    if record.status is DownstreamSubmissionPosture.IN_FLIGHT and any(
        value is None for value in lease_values
    ):
        raise ValueError("in-flight downstream submission requires a complete lease")
    if record.lease_owner is not None:
        _require_text(record.lease_owner, "lease_owner")
    if record.lease_attempt_id is not None:
        _require_text(record.lease_attempt_id, "lease_attempt_id")
    if record.lease_expires_at_utc is not None:
        _require_aware_utc(record.lease_expires_at_utc, "lease_expires_at_utc")
        if record.lease_expires_at_utc <= record.submitted_at_utc:
            raise ValueError("lease_expires_at_utc must be after submitted_at_utc")


def _validate_posture(record: DownstreamSubmissionRecord) -> None:
    requires_failure = record.status in {
        DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.NOT_CONFIGURED,
        DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        DownstreamSubmissionPosture.QUARANTINED,
    }
    if requires_failure and record.downstream_failure_reason is None:
        raise ValueError(f"{record.status.value} downstream submission requires a failure reason")
    if (
        record.status
        in {
            DownstreamSubmissionPosture.IN_FLIGHT,
            DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        }
        and record.downstream_failure_reason is not None
    ):
        raise ValueError(f"{record.status.value} downstream submission forbids a failure reason")
    if record.owner_receipt is not None:
        if record.status not in {
            DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
            DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
        }:
            raise ValueError("owner_receipt requires a terminal downstream posture")
        if record.owner_receipt.owner_authority is not record.source_authority:
            raise ValueError("owner_receipt authority must match source_authority")


def _lease_blocker(
    record: DownstreamSubmissionRecord,
    lease_owner: str,
    lease_attempt_id: str,
) -> str | None:
    _require_text(lease_owner, "lease_owner")
    _require_text(lease_attempt_id, "lease_attempt_id")
    if record.lease_owner != lease_owner or record.lease_attempt_id != lease_attempt_id:
        return "downstream_submission_lease_conflict"
    return None


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
