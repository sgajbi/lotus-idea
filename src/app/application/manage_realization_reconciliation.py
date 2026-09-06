from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    ManageActionRealizationHistory,
    ManageRealizationHistoryMutationDecision,
    QueueAccessScopeFilter,
    ReviewAccessScope,
    SourceSystem,
)
from app.ports.downstream_realization import (
    DownstreamRealizationNotObserved,
    DownstreamRealizationReadError,
    ManageActionRealizationReader,
)
from app.ports.idea_repository import DownstreamSubmissionRepository


class ManageRealizationReconciliationStatus(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"
    NOT_ELIGIBLE = "not_eligible"
    CONFLICT = "conflict"
    OWNER_ACCEPTANCE_NOT_OBSERVED = "owner_acceptance_not_observed"
    OWNER_UNAVAILABLE = "owner_unavailable"


@dataclass(frozen=True)
class ReconcileManageRealizationCommand:
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
class ManageRealizationReconciliationResult:
    status: ManageRealizationReconciliationStatus
    history: ManageActionRealizationHistory | None
    blocker: str | None = None
    appended_event_count: int = 0
    grants_rebalance_execution_authority: bool = False
    grants_order_authority: bool = False
    grants_client_publication_authority: bool = False


class ManageRealizationAccessScopeDenied(Exception):
    """Raised before owner access when caller scope does not cover the conversion candidate."""


def reconcile_manage_realization_history(
    command: ReconcileManageRealizationCommand,
    *,
    repository: DownstreamSubmissionRepository,
    manage_reader: ManageActionRealizationReader | None,
) -> ManageRealizationReconciliationResult:
    submission = repository.downstream_submission_by_support_reference(command.support_reference)
    if submission is None:
        return _result(ManageRealizationReconciliationStatus.NOT_FOUND)
    blocker = _submission_eligibility_blocker(
        submission,
        accepted_at_utc=command.accepted_at_utc,
    )
    if blocker is not None:
        return _result(ManageRealizationReconciliationStatus.NOT_ELIGIBLE, blocker=blocker)
    candidate_record = repository.candidate_record_for_conversion_intent(submission.resource_id)
    conversion_intent = repository.conversion_intent_by_id(submission.resource_id)
    if candidate_record is None or conversion_intent is None:
        return _result(
            ManageRealizationReconciliationStatus.CONFLICT,
            blocker="manage_realization_source_resource_missing",
        )
    access_scope = _authorized_access_scope(
        command.access_scope_filter,
        candidate_record.candidate.access_scope,
    )
    if manage_reader is None:
        return _result(
            ManageRealizationReconciliationStatus.OWNER_UNAVAILABLE,
            blocker="manage_realization_reader_not_configured",
        )
    try:
        history = _load_owner_history(
            manage_reader=manage_reader,
            submission=submission,
            access_scope=access_scope,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
    except DownstreamRealizationNotObserved:
        return _result(
            ManageRealizationReconciliationStatus.OWNER_ACCEPTANCE_NOT_OBSERVED,
            blocker="manage_realization_owner_acceptance_not_observed",
        )
    except DownstreamRealizationReadError:
        return _result(
            ManageRealizationReconciliationStatus.OWNER_UNAVAILABLE,
            blocker="manage_realization_owner_unavailable",
        )
    except ValueError:
        return _result(
            ManageRealizationReconciliationStatus.CONFLICT,
            blocker="manage_realization_history_invalid",
        )
    identity_blocker = _history_identity_blocker(
        history,
        access_scope=access_scope,
        candidate_id=candidate_record.candidate.candidate_id,
        conversion_intent_id=conversion_intent.intent.conversion_intent_id,
        intake_id=(
            submission.owner_receipt.owner_request_id
            if submission.owner_receipt is not None
            else None
        ),
    )
    if identity_blocker is not None:
        return _result(ManageRealizationReconciliationStatus.CONFLICT, blocker=identity_blocker)
    if submission.owner_receipt is None:
        recovery_blocker = _recover_submission_receipt(
            repository=repository,
            submission=submission,
            history=history,
            actor_subject=command.actor_subject,
            accepted_at_utc=command.accepted_at_utc,
        )
        if recovery_blocker is not None:
            return _result(
                ManageRealizationReconciliationStatus.CONFLICT,
                blocker=recovery_blocker,
            )
    mutation = repository.persist_manage_realization_history(
        support_reference=command.support_reference,
        history=history,
    )
    if mutation.decision is ManageRealizationHistoryMutationDecision.NOT_FOUND:
        return _result(ManageRealizationReconciliationStatus.NOT_FOUND)
    if mutation.decision is ManageRealizationHistoryMutationDecision.CONFLICT:
        return _result(
            ManageRealizationReconciliationStatus.CONFLICT,
            blocker=mutation.blocker or "manage_realization_history_conflict",
        )
    status = (
        ManageRealizationReconciliationStatus.REPLAYED
        if mutation.decision is ManageRealizationHistoryMutationDecision.REPLAYED
        else ManageRealizationReconciliationStatus.ACCEPTED
    )
    return ManageRealizationReconciliationResult(
        status=status,
        history=mutation.history,
        appended_event_count=mutation.appended_event_count,
    )


def _submission_eligibility_blocker(
    submission: DownstreamSubmissionRecord,
    *,
    accepted_at_utc: datetime,
) -> str | None:
    if submission.resource_type is not DownstreamSubmissionResourceType.CONVERSION_INTENT:
        return "manage_realization_requires_conversion_intent_submission"
    if submission.target is not ConversionTarget.MANAGE_REVIEW:
        return "manage_realization_requires_manage_target"
    if submission.source_authority is not SourceSystem.LOTUS_MANAGE:
        return "manage_realization_requires_manage_authority"
    if submission.status is DownstreamSubmissionPosture.IN_FLIGHT:
        if (
            submission.lease_expires_at_utc is None
            or submission.lease_expires_at_utc > accepted_at_utc
        ):
            return "manage_realization_submission_still_in_flight"
        return None
    if submission.status is DownstreamSubmissionPosture.RECONCILIATION_REQUIRED:
        return None
    if submission.status not in {
        DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
    }:
        return "manage_realization_requires_terminal_owner_submission"
    if submission.owner_receipt is None:
        return "manage_realization_owner_receipt_missing"
    return None


def _load_owner_history(
    *,
    manage_reader: ManageActionRealizationReader,
    submission: DownstreamSubmissionRecord,
    access_scope: ReviewAccessScope,
    correlation_id: str | None,
    trace_id: str | None,
) -> ManageActionRealizationHistory:
    receipt = submission.owner_receipt
    if receipt is not None:
        return manage_reader.load_action_realization(
            intake_id=receipt.owner_request_id,
            access_scope=access_scope,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
    return manage_reader.load_realization_by_conversion_intent(
        conversion_intent_id=submission.resource_id,
        access_scope=access_scope,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )


def _recover_submission_receipt(
    *,
    repository: DownstreamSubmissionRepository,
    submission: DownstreamSubmissionRecord,
    history: ManageActionRealizationHistory,
    actor_subject: str,
    accepted_at_utc: datetime,
) -> str | None:
    initial_event = history.events[0]
    receipt = DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_MANAGE,
        owner_request_id=history.intake_id,
        owner_realization_id=history.management_action_id,
        owner_work_id=history.management_action_id,
        source_event_version=initial_event.source_event_version,
        source_evidence_fingerprint=history.request_fingerprint,
    )
    mutation = repository.reconcile_downstream_submission(
        support_reference=submission.support_reference,
        resolution=DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM,
        actor_subject=actor_subject,
        reason="authoritative_manage_owner_history_recovered",
        change_reference=f"manage-owner-recovery-v{history.source_event_version}",
        reconciled_at_utc=accepted_at_utc,
        owner_receipt=receipt,
    )
    if mutation.decision in {
        DownstreamSubmissionMutationDecision.ACCEPTED,
        DownstreamSubmissionMutationDecision.REPLAYED,
    }:
        return None
    return mutation.blocker or "manage_realization_submission_recovery_conflict"


def _history_identity_blocker(
    history: ManageActionRealizationHistory,
    *,
    access_scope: ReviewAccessScope,
    candidate_id: str,
    conversion_intent_id: str,
    intake_id: str | None,
) -> str | None:
    # The owner history carries no tenant or evidence-fingerprint restatement
    # (manage#660 scopes reads by trusted principal); identity binds through
    # the intake, the portfolio, and the exact Idea resource identities.
    if history.portfolio_id != access_scope.portfolio_id:
        return "manage_realization_scope_conflict"
    if intake_id is not None and history.intake_id != intake_id:
        return "manage_realization_intake_conflict"
    if history.idea_candidate_id != candidate_id:
        return "manage_realization_candidate_conflict"
    if history.conversion_intent_id != conversion_intent_id:
        return "manage_realization_conversion_intent_conflict"
    return None


def _authorized_access_scope(
    access_scope_filter: QueueAccessScopeFilter,
    access_scope: ReviewAccessScope | None,
) -> ReviewAccessScope:
    if access_scope_filter.is_empty or not access_scope_filter.matches(access_scope):
        raise ManageRealizationAccessScopeDenied
    assert access_scope is not None
    return access_scope


def _result(
    status: ManageRealizationReconciliationStatus,
    *,
    blocker: str | None = None,
) -> ManageRealizationReconciliationResult:
    return ManageRealizationReconciliationResult(status=status, history=None, blocker=blocker)


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
