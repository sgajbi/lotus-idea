from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
import hashlib

from app.application.downstream_realization.report_receipt_validation import (
    validated_report_submission_receipt,
)
from app.domain import (
    ConversionTarget,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    GovernedReportEvidencePack,
    QueueAccessScopeFilter,
    ReviewAccessScope,
    SourceSystem,
)
from app.ports.downstream_realization import (
    DownstreamOwnerReceipt,
    DownstreamRealizationReadConflict,
    DownstreamRealizationReadError,
    ReportEvidencePackMaterializationReader,
)
from app.ports.idea_repository import DownstreamSubmissionRepository


class ReportMaterializationReconciliationStatus(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"
    NOT_ELIGIBLE = "not_eligible"
    CONFLICT = "conflict"
    OWNER_UNAVAILABLE = "owner_unavailable"


@dataclass(frozen=True)
class ReconcileReportMaterializationCommand:
    support_reference: str
    actor_subject: str
    access_scope_filter: QueueAccessScopeFilter
    accepted_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.support_reference, "support_reference")
        _require_text(self.actor_subject, "actor_subject")
        _require_aware_utc(self.accepted_at_utc, "accepted_at_utc")


@dataclass(frozen=True)
class ReportMaterializationReconciliationResult:
    status: ReportMaterializationReconciliationStatus
    owner_receipt: DownstreamSubmissionOwnerReceipt | None
    blocker: str | None = None
    grants_client_publication_authority: bool = False
    supported_feature_promoted: bool = False


class ReportMaterializationAccessScopeDenied(Exception):
    """Raised before owner access when caller scope does not cover the evidence pack."""


def reconcile_report_materialization_receipt(
    command: ReconcileReportMaterializationCommand,
    *,
    repository: DownstreamSubmissionRepository,
    report_reader: ReportEvidencePackMaterializationReader | None,
) -> ReportMaterializationReconciliationResult:
    submission = repository.downstream_submission_by_support_reference(command.support_reference)
    if submission is None:
        return _result(ReportMaterializationReconciliationStatus.NOT_FOUND)
    blocker = _submission_eligibility_blocker(
        submission,
        accepted_at_utc=command.accepted_at_utc,
    )
    if blocker is not None:
        return _result(ReportMaterializationReconciliationStatus.NOT_ELIGIBLE, blocker=blocker)
    evidence_pack = repository.report_evidence_pack_by_id(submission.resource_id)
    candidate_record = repository.candidate_record_for_report_evidence_pack(submission.resource_id)
    if evidence_pack is None or candidate_record is None:
        return _result(
            ReportMaterializationReconciliationStatus.CONFLICT,
            blocker="report_materialization_source_resource_missing",
        )
    access_scope = _authorized_access_scope(
        command.access_scope_filter,
        candidate_record.candidate.access_scope,
    )
    if submission.owner_receipt is not None:
        try:
            _validate_stored_receipt(submission.owner_receipt, evidence_pack)
        except ValueError:
            return _result(
                ReportMaterializationReconciliationStatus.CONFLICT,
                blocker="report_materialization_persisted_receipt_invalid",
            )
        return ReportMaterializationReconciliationResult(
            status=ReportMaterializationReconciliationStatus.REPLAYED,
            owner_receipt=submission.owner_receipt,
        )
    if report_reader is None:
        return _result(
            ReportMaterializationReconciliationStatus.OWNER_UNAVAILABLE,
            blocker="report_materialization_reader_not_configured",
        )
    try:
        owner_receipt = report_reader.recover_report_evidence_pack_receipt(
            evidence_pack,
            access_scope=access_scope,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
            idempotency_key=submission.idempotency_key,
        )
        durable_receipt = validated_report_submission_receipt(owner_receipt, evidence_pack)
    except DownstreamRealizationReadConflict:
        return _result(
            ReportMaterializationReconciliationStatus.CONFLICT,
            blocker="report_materialization_owner_identity_conflict",
        )
    except DownstreamRealizationReadError:
        return _result(
            ReportMaterializationReconciliationStatus.OWNER_UNAVAILABLE,
            blocker="report_materialization_owner_unavailable",
        )
    except ValueError:
        return _result(
            ReportMaterializationReconciliationStatus.CONFLICT,
            blocker="report_materialization_receipt_invalid",
        )
    mutation = repository.reconcile_downstream_submission(
        support_reference=submission.support_reference,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject=command.actor_subject,
        reason="authoritative_report_materialization_receipt_recovered",
        change_reference=_recovery_change_reference(durable_receipt),
        reconciled_at_utc=command.accepted_at_utc,
        owner_receipt=durable_receipt,
    )
    if mutation.decision not in {
        DownstreamSubmissionMutationDecision.ACCEPTED,
        DownstreamSubmissionMutationDecision.REPLAYED,
    }:
        return _result(
            ReportMaterializationReconciliationStatus.CONFLICT,
            blocker=mutation.blocker or "report_materialization_reconciliation_conflict",
        )
    assert mutation.record is not None
    assert mutation.record.owner_receipt is not None
    return ReportMaterializationReconciliationResult(
        status=(
            ReportMaterializationReconciliationStatus.REPLAYED
            if mutation.decision is DownstreamSubmissionMutationDecision.REPLAYED
            else ReportMaterializationReconciliationStatus.ACCEPTED
        ),
        owner_receipt=mutation.record.owner_receipt,
    )


def _submission_eligibility_blocker(
    submission: DownstreamSubmissionRecord,
    *,
    accepted_at_utc: datetime,
) -> str | None:
    if submission.resource_type is not DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK:
        return "report_materialization_requires_evidence_pack_submission"
    if submission.target is not ConversionTarget.REPORT_EVIDENCE:
        return "report_materialization_requires_report_target"
    if submission.source_authority is not SourceSystem.LOTUS_REPORT:
        return "report_materialization_requires_report_authority"
    if submission.status is DownstreamSubmissionPosture.IN_FLIGHT:
        if (
            submission.lease_expires_at_utc is None
            or submission.lease_expires_at_utc > accepted_at_utc
        ):
            return "report_materialization_submission_still_in_flight"
        if submission.owner_receipt is not None:
            return "report_materialization_uncertain_submission_has_owner_receipt"
        return None
    if submission.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED:
        if submission.owner_receipt is not None:
            return "report_materialization_uncertain_submission_has_owner_receipt"
        return None
    if (
        submission.status is DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM
        and submission.owner_receipt is not None
    ):
        return None
    return "report_materialization_submission_not_recoverable"


def _validate_stored_receipt(
    receipt: DownstreamSubmissionOwnerReceipt,
    evidence_pack: GovernedReportEvidencePack,
) -> None:
    validated_report_submission_receipt(
        DownstreamOwnerReceipt(
            owner_authority=receipt.owner_authority,
            owner_request_id=receipt.owner_request_id,
            owner_realization_id=receipt.owner_realization_id,
            owner_work_id=receipt.owner_work_id,
            source_event_version=receipt.source_event_version,
            source_evidence_fingerprint=receipt.source_evidence_fingerprint,
            report_materialization=receipt.report_materialization,
        ),
        evidence_pack,
    )


def _recovery_change_reference(receipt: DownstreamSubmissionOwnerReceipt) -> str:
    identity = f"{receipt.owner_request_id}:{receipt.owner_realization_id}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"report-owner-recovery-{digest}"


def _authorized_access_scope(
    access_scope_filter: QueueAccessScopeFilter,
    access_scope: ReviewAccessScope | None,
) -> ReviewAccessScope:
    if access_scope_filter.is_empty or not access_scope_filter.matches(access_scope):
        raise ReportMaterializationAccessScopeDenied
    assert access_scope is not None
    return access_scope


def _result(
    status: ReportMaterializationReconciliationStatus,
    *,
    blocker: str | None = None,
) -> ReportMaterializationReconciliationResult:
    return ReportMaterializationReconciliationResult(
        status=status,
        owner_receipt=None,
        blocker=blocker,
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
