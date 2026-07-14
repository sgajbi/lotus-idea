from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionClaimDecision,
    DownstreamSubmissionMutationDecision,
    DownstreamSubmissionPosture,
    DownstreamSubmissionRecord,
    DownstreamSubmissionResourceType,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    SourceSystem,
    create_downstream_submission_claim,
)
from app.domain.idempotency import payload_fingerprint
from app.ports.downstream_realization import (
    AdviseProposalRealizationClient,
    DownstreamRealizationOutcome,
    DownstreamRealizationOutcomePosture,
    ManageActionRealizationClient,
    ReportEvidencePackMaterializationClient,
)
from app.ports.idea_repository import DownstreamSubmissionRepository


_LEASE_DURATION = timedelta(minutes=5)
_LEASE_OWNER = "downstream-realization"


class DownstreamRealizationStatus(StrEnum):
    ACCEPTED_BY_DOWNSTREAM = "accepted_by_downstream"
    REJECTED_BY_DOWNSTREAM = "rejected_by_downstream"
    NOT_CONFIGURED = "not_configured"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    NOT_FOUND = "not_found"
    UNSUPPORTED_TARGET = "unsupported_target"


@dataclass(frozen=True)
class RealizeConversionIntentCommand:
    conversion_intent_id: str
    idempotency_key: str
    actor_subject: str
    correlation_id: str | None = None
    trace_id: str | None = None
    submitted_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _validate_command(self)


@dataclass(frozen=True)
class RealizeReportEvidencePackCommand:
    report_evidence_pack_id: str
    idempotency_key: str
    actor_subject: str
    correlation_id: str | None = None
    trace_id: str | None = None
    submitted_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.report_evidence_pack_id, "report_evidence_pack_id")
        _validate_command(self)


@dataclass(frozen=True)
class DownstreamRealizationSubmissionResult:
    status: DownstreamRealizationStatus
    source_authority: SourceSystem | None
    target: ConversionTarget | None
    downstream_failure_reason: str | None = None
    support_reference: str | None = None
    idempotency_replayed: bool = False
    records_downstream_outcome: bool = False
    grants_downstream_authority: bool = False
    supported_feature_promoted: bool = False


@dataclass(frozen=True)
class _SubmissionRequest:
    idempotency_key: str
    actor_subject: str
    resource_type: DownstreamSubmissionResourceType
    resource_id: str
    source_authority: SourceSystem
    target: ConversionTarget
    request_fingerprint: str
    submitted_at_utc: datetime
    correlation_id: str | None
    trace_id: str | None

    @property
    def lease_attempt_id(self) -> str:
        digest = hashlib.sha256(self.idempotency_key.encode("utf-8")).hexdigest()[:24]
        return f"downstream-attempt-{digest}"


def submit_conversion_intent_to_downstream(
    command: RealizeConversionIntentCommand,
    *,
    repository: DownstreamSubmissionRepository,
    advise_client: AdviseProposalRealizationClient | None,
    manage_client: ManageActionRealizationClient | None,
) -> DownstreamRealizationSubmissionResult:
    conversion_intent = repository.conversion_intent_by_id(command.conversion_intent_id)
    if conversion_intent is None:
        return _unresolved_result(DownstreamRealizationStatus.NOT_FOUND)
    if conversion_intent.intent.target is ConversionTarget.REPORT_EVIDENCE:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.UNSUPPORTED_TARGET,
            source_authority=conversion_intent.target_source_authority,
            target=conversion_intent.intent.target,
            downstream_failure_reason="report_evidence_pack_request_required",
        )

    request = _request_for_conversion(command, conversion_intent)
    if conversion_intent.intent.target is ConversionTarget.ADVISE_PROPOSAL:
        call = (
            None
            if advise_client is None
            else lambda: advise_client.submit_proposal_intent(
                conversion_intent,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
                idempotency_key=command.idempotency_key,
            )
        )
    elif conversion_intent.intent.target is ConversionTarget.MANAGE_REVIEW:
        call = (
            None
            if manage_client is None
            else lambda: manage_client.submit_action_intent(
                conversion_intent,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
                idempotency_key=command.idempotency_key,
            )
        )
    else:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.UNSUPPORTED_TARGET,
            source_authority=conversion_intent.target_source_authority,
            target=conversion_intent.intent.target,
            downstream_failure_reason="unsupported_downstream_realization_target",
        )
    return _execute_claimed_submission(request, repository=repository, call=call)


def submit_report_evidence_pack_to_downstream(
    command: RealizeReportEvidencePackCommand,
    *,
    repository: DownstreamSubmissionRepository,
    report_client: ReportEvidencePackMaterializationClient | None,
) -> DownstreamRealizationSubmissionResult:
    evidence_pack = repository.report_evidence_pack_by_id(command.report_evidence_pack_id)
    if evidence_pack is None:
        return _unresolved_result(DownstreamRealizationStatus.NOT_FOUND)
    request = _request_for_report_pack(command, evidence_pack)
    call = (
        None
        if report_client is None
        else lambda: report_client.submit_report_evidence_pack_request(
            evidence_pack,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
            idempotency_key=command.idempotency_key,
        )
    )
    return _execute_claimed_submission(request, repository=repository, call=call)


def _execute_claimed_submission(
    request: _SubmissionRequest,
    *,
    repository: DownstreamSubmissionRepository,
    call: Callable[[], DownstreamRealizationOutcome] | None,
) -> DownstreamRealizationSubmissionResult:
    claim = repository.claim_downstream_submission(_claim_record(request))
    if claim.decision is DownstreamSubmissionClaimDecision.CONFLICT:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.IDEMPOTENCY_CONFLICT,
            source_authority=None,
            target=None,
            downstream_failure_reason="idempotency_conflict",
        )
    if claim.decision is not DownstreamSubmissionClaimDecision.ACCEPTED:
        assert claim.record is not None
        return _result_from_existing(
            claim.record,
            reconciliation_required=(
                claim.decision is DownstreamSubmissionClaimDecision.RECONCILIATION_REQUIRED
            ),
            idempotency_replayed=True,
        )

    if call is None:
        return _finalize_submission(
            request,
            repository=repository,
            posture=DownstreamSubmissionPosture.NOT_CONFIGURED,
            failure_reason="downstream_realization_not_configured",
        )
    try:
        outcome = call()
    except Exception:
        return _finalize_submission(
            request,
            repository=repository,
            posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            failure_reason="downstream_call_outcome_unknown",
        )
    posture = _posture_from_outcome(outcome)
    return _finalize_submission(
        request,
        repository=repository,
        posture=posture,
        failure_reason=outcome.failure_reason,
    )


def _finalize_submission(
    request: _SubmissionRequest,
    *,
    repository: DownstreamSubmissionRepository,
    posture: DownstreamSubmissionPosture,
    failure_reason: str | None,
) -> DownstreamRealizationSubmissionResult:
    try:
        result = repository.finalize_downstream_submission(
            idempotency_key=request.idempotency_key,
            lease_owner=_LEASE_OWNER,
            lease_attempt_id=request.lease_attempt_id,
            posture=posture,
            finalized_at_utc=max(datetime.now(UTC), request.submitted_at_utc),
            failure_reason=failure_reason,
        )
    except Exception:
        return _uncertain_result(request, "downstream_submission_finalization_failed")
    if result.decision is not DownstreamSubmissionMutationDecision.ACCEPTED:
        return _uncertain_result(
            request,
            result.blocker or "downstream_submission_finalization_conflict",
        )
    assert result.record is not None
    return _result_from_existing(
        result.record,
        reconciliation_required=False,
        idempotency_replayed=False,
    )


def _result_from_existing(
    record: DownstreamSubmissionRecord,
    *,
    reconciliation_required: bool,
    idempotency_replayed: bool,
) -> DownstreamRealizationSubmissionResult:
    status = (
        DownstreamRealizationStatus.RECONCILIATION_REQUIRED
        if reconciliation_required
        or record.status
        in {
            DownstreamSubmissionPosture.IN_FLIGHT,
            DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
            DownstreamSubmissionPosture.QUARANTINED,
        }
        else DownstreamRealizationStatus(record.status.value)
    )
    return DownstreamRealizationSubmissionResult(
        status=status,
        source_authority=record.source_authority,
        target=record.target,
        downstream_failure_reason=(
            record.downstream_failure_reason
            if record.downstream_failure_reason is not None
            else (
                "downstream_submission_requires_reconciliation"
                if status is DownstreamRealizationStatus.RECONCILIATION_REQUIRED
                else None
            )
        ),
        support_reference=record.support_reference,
        idempotency_replayed=idempotency_replayed,
    )


def _uncertain_result(
    request: _SubmissionRequest,
    failure_reason: str,
) -> DownstreamRealizationSubmissionResult:
    return DownstreamRealizationSubmissionResult(
        status=DownstreamRealizationStatus.RECONCILIATION_REQUIRED,
        source_authority=request.source_authority,
        target=request.target,
        downstream_failure_reason=failure_reason,
        support_reference=_claim_record(request).support_reference,
    )


def _posture_from_outcome(outcome: DownstreamRealizationOutcome) -> DownstreamSubmissionPosture:
    if outcome.posture is DownstreamRealizationOutcomePosture.ACCEPTED:
        return DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM
    if outcome.posture is DownstreamRealizationOutcomePosture.REJECTED:
        return DownstreamSubmissionPosture.REJECTED_BY_DOWNSTREAM
    return DownstreamSubmissionPosture.RECONCILIATION_REQUIRED


def _claim_record(request: _SubmissionRequest) -> DownstreamSubmissionRecord:
    return create_downstream_submission_claim(
        idempotency_key=request.idempotency_key,
        request_fingerprint=request.request_fingerprint,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        target=request.target,
        source_authority=request.source_authority,
        actor_subject=request.actor_subject,
        claimed_at_utc=request.submitted_at_utc,
        lease_owner=_LEASE_OWNER,
        lease_attempt_id=request.lease_attempt_id,
        lease_expires_at_utc=request.submitted_at_utc + _LEASE_DURATION,
        correlation_id=request.correlation_id,
        trace_id=request.trace_id,
    )


def _request_for_conversion(
    command: RealizeConversionIntentCommand,
    conversion_intent: GovernedConversionIntent,
) -> _SubmissionRequest:
    return _submission_request(
        command=command,
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id=command.conversion_intent_id,
        target=conversion_intent.intent.target,
        source_authority=conversion_intent.target_source_authority,
    )


def _request_for_report_pack(
    command: RealizeReportEvidencePackCommand,
    evidence_pack: GovernedReportEvidencePack,
) -> _SubmissionRequest:
    return _submission_request(
        command=command,
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id=command.report_evidence_pack_id,
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=evidence_pack.report_source_authority,
    )


def _submission_request(
    *,
    command: RealizeConversionIntentCommand | RealizeReportEvidencePackCommand,
    resource_type: DownstreamSubmissionResourceType,
    resource_id: str,
    target: ConversionTarget,
    source_authority: SourceSystem,
) -> _SubmissionRequest:
    return _SubmissionRequest(
        idempotency_key=command.idempotency_key,
        actor_subject=command.actor_subject,
        resource_type=resource_type,
        resource_id=resource_id,
        source_authority=source_authority,
        target=target,
        request_fingerprint=payload_fingerprint(
            {
                "resource_type": resource_type.value,
                "resource_id": resource_id,
                "target": target.value,
                "source_authority": source_authority.value,
            }
        ),
        submitted_at_utc=command.submitted_at_utc or datetime.now(UTC),
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
    )


def _unresolved_result(
    status: DownstreamRealizationStatus,
) -> DownstreamRealizationSubmissionResult:
    return DownstreamRealizationSubmissionResult(
        status=status,
        source_authority=None,
        target=None,
    )


def _validate_command(
    command: RealizeConversionIntentCommand | RealizeReportEvidencePackCommand,
) -> None:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    if command.submitted_at_utc is not None:
        _require_aware_utc(command.submitted_at_utc, "submitted_at_utc")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
