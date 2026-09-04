from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain import (
    AdviseProposalRealizationHistory,
    AdviseProposalRealizationStatus,
    AdviseRealizationHistoryMutationDecision,
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionOwnerReceipt,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResolution,
    DownstreamSubmissionResourceType,
    QueueAccessScopeFilter,
    ReviewAccessScope,
    SourceSystem,
)
from app.ports.downstream_realization import (
    AdviseProposalRealizationReader,
    DownstreamRealizationReadError,
)
from app.ports.idea_repository import DownstreamSubmissionRepository


class AdviseRealizationReconciliationStatus(StrEnum):
    ACCEPTED = "accepted"
    REPLAYED = "replayed"
    NOT_FOUND = "not_found"
    NOT_ELIGIBLE = "not_eligible"
    CONFLICT = "conflict"
    OWNER_UNAVAILABLE = "owner_unavailable"


@dataclass(frozen=True)
class ReconcileAdviseRealizationCommand:
    support_reference: str
    actor_subject: str
    access_scope_filter: QueueAccessScopeFilter
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.support_reference, "support_reference")
        _require_text(self.actor_subject, "actor_subject")


@dataclass(frozen=True)
class AdviseRealizationReconciliationResult:
    status: AdviseRealizationReconciliationStatus
    history: AdviseProposalRealizationHistory | None
    blocker: str | None = None
    appended_outcome_count: int = 0
    grants_execution_authority: bool = False
    grants_suitability_authority: bool = False
    grants_client_publication_authority: bool = False


class AdviseRealizationAccessScopeDenied(Exception):
    """Raised before owner access when caller scope does not cover the conversion candidate."""


def reconcile_advise_realization_history(
    command: ReconcileAdviseRealizationCommand,
    *,
    repository: DownstreamSubmissionRepository,
    advise_reader: AdviseProposalRealizationReader | None,
) -> AdviseRealizationReconciliationResult:
    submission = repository.downstream_submission_by_support_reference(command.support_reference)
    if submission is None:
        return _result(AdviseRealizationReconciliationStatus.NOT_FOUND)
    blocker = _submission_eligibility_blocker(submission)
    if blocker is not None:
        return _result(AdviseRealizationReconciliationStatus.NOT_ELIGIBLE, blocker=blocker)
    candidate_record = repository.candidate_record_for_conversion_intent(submission.resource_id)
    conversion_intent = repository.conversion_intent_by_id(submission.resource_id)
    if candidate_record is None or conversion_intent is None:
        return _result(
            AdviseRealizationReconciliationStatus.CONFLICT,
            blocker="advise_realization_source_resource_missing",
        )
    access_scope = _authorized_access_scope(
        command.access_scope_filter,
        candidate_record.candidate.access_scope,
    )
    if advise_reader is None:
        return _result(
            AdviseRealizationReconciliationStatus.OWNER_UNAVAILABLE,
            blocker="advise_realization_reader_not_configured",
        )
    try:
        history = _load_owner_history(
            advise_reader=advise_reader,
            submission=submission,
            access_scope=access_scope,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
    except DownstreamRealizationReadError:
        return _result(
            AdviseRealizationReconciliationStatus.OWNER_UNAVAILABLE,
            blocker="advise_realization_owner_unavailable",
        )
    except ValueError:
        return _result(
            AdviseRealizationReconciliationStatus.CONFLICT,
            blocker="advise_realization_history_invalid",
        )
    identity_blocker = _history_identity_blocker(
        history,
        access_scope=access_scope,
        candidate_id=candidate_record.candidate.candidate_id,
        conversion_intent_id=conversion_intent.intent.conversion_intent_id,
        evidence_fingerprint=conversion_intent.evidence_content_hash,
    )
    if identity_blocker is not None:
        return _result(AdviseRealizationReconciliationStatus.CONFLICT, blocker=identity_blocker)
    if submission.owner_receipt is None:
        recovery_blocker = _recover_submission_receipt(
            repository=repository,
            submission=submission,
            history=history,
            actor_subject=command.actor_subject,
        )
        if recovery_blocker is not None:
            return _result(
                AdviseRealizationReconciliationStatus.CONFLICT,
                blocker=recovery_blocker,
            )
    existing = repository.advise_realization_history_by_support_reference(command.support_reference)
    mutation = repository.persist_advise_realization_history(
        support_reference=command.support_reference,
        history=history,
    )
    if mutation.decision is AdviseRealizationHistoryMutationDecision.NOT_FOUND:
        return _result(AdviseRealizationReconciliationStatus.NOT_FOUND)
    if mutation.decision is AdviseRealizationHistoryMutationDecision.CONFLICT:
        return _result(
            AdviseRealizationReconciliationStatus.CONFLICT,
            blocker=mutation.blocker or "advise_realization_history_conflict",
        )
    status = (
        AdviseRealizationReconciliationStatus.REPLAYED
        if mutation.decision is AdviseRealizationHistoryMutationDecision.REPLAYED
        else AdviseRealizationReconciliationStatus.ACCEPTED
    )
    previous_count = len(existing.outcomes) if existing is not None else 0
    return AdviseRealizationReconciliationResult(
        status=status,
        history=mutation.history,
        appended_outcome_count=len(history.outcomes) - previous_count,
    )


def _submission_eligibility_blocker(submission: DownstreamSubmissionRecord) -> str | None:
    if submission.resource_type is not DownstreamSubmissionResourceType.CONVERSION_INTENT:
        return "advise_realization_requires_conversion_intent_submission"
    if submission.target is not ConversionTarget.ADVISE_PROPOSAL:
        return "advise_realization_requires_advise_target"
    if submission.source_authority is not SourceSystem.LOTUS_ADVISE:
        return "advise_realization_requires_advise_authority"
    if submission.status in {
        DownstreamSubmissionPosture.IN_FLIGHT,
        DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
    }:
        if submission.owner_receipt is not None:
            return "advise_realization_uncertain_submission_has_owner_receipt"
        return None
    if submission.status not in {
        DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
        DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM,
    }:
        return "advise_realization_requires_terminal_owner_submission"
    if submission.owner_receipt is None:
        return "advise_realization_owner_receipt_missing"
    return None


def _load_owner_history(
    *,
    advise_reader: AdviseProposalRealizationReader,
    submission: DownstreamSubmissionRecord,
    access_scope: ReviewAccessScope,
    correlation_id: str | None,
    trace_id: str | None,
) -> AdviseProposalRealizationHistory:
    receipt = submission.owner_receipt
    if receipt is not None:
        return advise_reader.load_proposal_realization(
            intake_id=receipt.owner_request_id,
            access_scope=access_scope,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
    return advise_reader.load_proposal_realization_by_conversion_intent(
        conversion_intent_id=submission.resource_id,
        access_scope=access_scope,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )


def _recover_submission_receipt(
    *,
    repository: DownstreamSubmissionRepository,
    submission: DownstreamSubmissionRecord,
    history: AdviseProposalRealizationHistory,
    actor_subject: str,
) -> str | None:
    initial_outcome = history.outcomes[0]
    accepted = initial_outcome.status is AdviseProposalRealizationStatus.ACCEPTED_FOR_REVIEW
    resolution = (
        DownstreamSubmissionResolution.ACCEPTED_BY_DOWNSTREAM
        if accepted
        else DownstreamSubmissionResolution.REJECTED_BY_DOWNSTREAM
    )
    receipt = DownstreamSubmissionOwnerReceipt(
        owner_authority=SourceSystem.LOTUS_ADVISE,
        owner_request_id=history.intake_id,
        owner_realization_id=history.realization_id,
        owner_work_id=history.review_work_id,
        # Reconstruct the exact intake receipt that was lost. Later owner
        # outcomes remain history evidence and must not rewrite acceptance.
        source_event_version=initial_outcome.source_event_version,
        source_evidence_fingerprint=history.source_evidence_fingerprint,
    )
    mutation = repository.reconcile_downstream_submission(
        support_reference=submission.support_reference,
        resolution=resolution,
        actor_subject=actor_subject,
        reason="authoritative_advise_owner_history_recovered",
        change_reference=(f"advise-owner-recovery-v{history.current_source_event_version}"),
        reconciled_at_utc=datetime.now(UTC),
        owner_receipt=receipt,
    )
    if mutation.decision in {
        DownstreamSubmissionMutationDecision.ACCEPTED,
        DownstreamSubmissionMutationDecision.REPLAYED,
    }:
        return None
    return mutation.blocker or "advise_realization_submission_recovery_conflict"


def _history_identity_blocker(
    history: AdviseProposalRealizationHistory,
    *,
    access_scope: ReviewAccessScope,
    candidate_id: str,
    conversion_intent_id: str,
    evidence_fingerprint: str,
) -> str | None:
    if (
        history.tenant_id != access_scope.tenant_id
        or history.portfolio_id != access_scope.portfolio_id
    ):
        return "advise_realization_scope_conflict"
    if history.idea_candidate_id != candidate_id:
        return "advise_realization_candidate_conflict"
    if history.conversion_intent_id != conversion_intent_id:
        return "advise_realization_conversion_intent_conflict"
    if history.source_evidence_fingerprint != evidence_fingerprint:
        return "advise_realization_evidence_conflict"
    return None


def _authorized_access_scope(
    access_scope_filter: QueueAccessScopeFilter,
    access_scope: ReviewAccessScope | None,
) -> ReviewAccessScope:
    if access_scope_filter.is_empty or not access_scope_filter.matches(access_scope):
        raise AdviseRealizationAccessScopeDenied
    assert access_scope is not None
    return access_scope


def _result(
    status: AdviseRealizationReconciliationStatus,
    *,
    blocker: str | None = None,
) -> AdviseRealizationReconciliationResult:
    return AdviseRealizationReconciliationResult(status=status, history=None, blocker=blocker)


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
