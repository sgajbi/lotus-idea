from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.domain import (
    ConversionTarget,
    DownstreamSubmissionPosture,
    DownstreamSubmissionResourceType,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    SourceSystem,
    create_downstream_submission_claim,
    finalize_downstream_submission,
)
from app.domain.idempotency import payload_fingerprint
from app.ports.downstream_realization import (
    AdviseProposalRealizationClient,
    ManageActionRealizationClient,
    ReportEvidencePackMaterializationClient,
)
from app.ports.idea_repository import DownstreamSubmissionRepository


class DownstreamRealizationStatus(StrEnum):
    ACCEPTED_BY_DOWNSTREAM = "accepted_by_downstream"
    REJECTED_BY_DOWNSTREAM = "rejected_by_downstream"
    NOT_CONFIGURED = "not_configured"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    NOT_FOUND = "not_found"
    UNSUPPORTED_TARGET = "unsupported_target"


@dataclass(frozen=True)
class RealizeConversionIntentCommand:
    conversion_intent_id: str
    idempotency_key: str
    correlation_id: str | None = None
    trace_id: str | None = None
    submitted_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")
        _require_text(self.idempotency_key, "idempotency_key")
        if self.submitted_at_utc is not None:
            _require_aware_utc(self.submitted_at_utc, "submitted_at_utc")


@dataclass(frozen=True)
class RealizeReportEvidencePackCommand:
    report_evidence_pack_id: str
    idempotency_key: str
    correlation_id: str | None = None
    trace_id: str | None = None
    submitted_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        _require_text(self.report_evidence_pack_id, "report_evidence_pack_id")
        _require_text(self.idempotency_key, "idempotency_key")
        if self.submitted_at_utc is not None:
            _require_aware_utc(self.submitted_at_utc, "submitted_at_utc")


@dataclass(frozen=True)
class DownstreamRealizationSubmissionResult:
    status: DownstreamRealizationStatus
    source_authority: SourceSystem | None
    target: ConversionTarget | None
    downstream_failure_reason: str | None = None
    idempotency_replayed: bool = False
    records_downstream_outcome: bool = False
    grants_downstream_authority: bool = False
    supported_feature_promoted: bool = False


def submit_conversion_intent_to_downstream(
    command: RealizeConversionIntentCommand,
    *,
    repository: DownstreamSubmissionRepository,
    advise_client: AdviseProposalRealizationClient | None,
    manage_client: ManageActionRealizationClient | None,
) -> DownstreamRealizationSubmissionResult:
    conversion_intent = _find_conversion_intent(
        command.conversion_intent_id,
        repository=repository,
    )
    if conversion_intent is None:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.NOT_FOUND,
            source_authority=None,
            target=None,
        )

    request_fingerprint = _submission_fingerprint(
        resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
        resource_id=command.conversion_intent_id,
        target=conversion_intent.intent.target,
        source_authority=conversion_intent.target_source_authority,
    )
    idempotent = _idempotent_submission_result(
        repository,
        idempotency_key=command.idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    if idempotent is not None:
        return idempotent

    if conversion_intent.intent.target is ConversionTarget.ADVISE_PROPOSAL:
        if advise_client is None:
            return _record_submission_result(
                command,
                repository=repository,
                resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
                resource_id=command.conversion_intent_id,
                source_authority=conversion_intent.target_source_authority,
                target=conversion_intent.intent.target,
                status=DownstreamRealizationStatus.NOT_CONFIGURED,
                request_fingerprint=request_fingerprint,
                failure_reason="downstream_realization_not_configured",
            )
        outcome = advise_client.submit_proposal_intent(
            conversion_intent,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
            idempotency_key=command.idempotency_key,
        )
    elif conversion_intent.intent.target is ConversionTarget.MANAGE_REVIEW:
        if manage_client is None:
            return _record_submission_result(
                command,
                repository=repository,
                resource_type=DownstreamSubmissionResourceType.CONVERSION_INTENT,
                resource_id=command.conversion_intent_id,
                source_authority=conversion_intent.target_source_authority,
                target=conversion_intent.intent.target,
                status=DownstreamRealizationStatus.NOT_CONFIGURED,
                request_fingerprint=request_fingerprint,
                failure_reason="downstream_realization_not_configured",
            )
        outcome = manage_client.submit_action_intent(
            conversion_intent,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
            idempotency_key=command.idempotency_key,
        )
    else:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.UNSUPPORTED_TARGET,
            source_authority=conversion_intent.target_source_authority,
            target=conversion_intent.intent.target,
            downstream_failure_reason="report_evidence_pack_request_required",
        )

    return _submission_result(
        accepted=outcome.accepted,
        source_authority=conversion_intent.target_source_authority,
        target=conversion_intent.intent.target,
        failure_reason=outcome.failure_reason,
        idempotency_replayed=False,
        record_with=(
            command,
            repository,
            DownstreamSubmissionResourceType.CONVERSION_INTENT,
            command.conversion_intent_id,
            request_fingerprint,
        ),
    )


def submit_report_evidence_pack_to_downstream(
    command: RealizeReportEvidencePackCommand,
    *,
    repository: DownstreamSubmissionRepository,
    report_client: ReportEvidencePackMaterializationClient | None,
) -> DownstreamRealizationSubmissionResult:
    evidence_pack = _find_report_evidence_pack(
        command.report_evidence_pack_id,
        repository=repository,
    )
    if evidence_pack is None:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.NOT_FOUND,
            source_authority=None,
            target=None,
        )

    request_fingerprint = _submission_fingerprint(
        resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
        resource_id=command.report_evidence_pack_id,
        target=ConversionTarget.REPORT_EVIDENCE,
        source_authority=evidence_pack.report_source_authority,
    )
    idempotent = _idempotent_submission_result(
        repository,
        idempotency_key=command.idempotency_key,
        request_fingerprint=request_fingerprint,
    )
    if idempotent is not None:
        return idempotent

    if report_client is None:
        return _record_submission_result(
            command,
            repository=repository,
            resource_type=DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
            resource_id=command.report_evidence_pack_id,
            source_authority=evidence_pack.report_source_authority,
            target=ConversionTarget.REPORT_EVIDENCE,
            status=DownstreamRealizationStatus.NOT_CONFIGURED,
            request_fingerprint=request_fingerprint,
            failure_reason="downstream_realization_not_configured",
        )

    outcome = report_client.submit_report_evidence_pack_request(
        evidence_pack,
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
        idempotency_key=command.idempotency_key,
    )
    return _submission_result(
        accepted=outcome.accepted,
        source_authority=evidence_pack.report_source_authority,
        target=ConversionTarget.REPORT_EVIDENCE,
        failure_reason=outcome.failure_reason,
        idempotency_replayed=False,
        record_with=(
            command,
            repository,
            DownstreamSubmissionResourceType.REPORT_EVIDENCE_PACK,
            command.report_evidence_pack_id,
            request_fingerprint,
        ),
    )


def _submission_result(
    *,
    accepted: bool,
    source_authority: SourceSystem,
    target: ConversionTarget,
    failure_reason: str | None,
    idempotency_replayed: bool,
    record_with: tuple[
        RealizeConversionIntentCommand | RealizeReportEvidencePackCommand,
        DownstreamSubmissionRepository,
        DownstreamSubmissionResourceType,
        str,
        str,
    ]
    | None = None,
) -> DownstreamRealizationSubmissionResult:
    result = DownstreamRealizationSubmissionResult(
        status=(
            DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
            if accepted
            else DownstreamRealizationStatus.REJECTED_BY_DOWNSTREAM
        ),
        source_authority=source_authority,
        target=target,
        downstream_failure_reason=failure_reason,
        idempotency_replayed=idempotency_replayed,
    )
    if record_with is not None:
        command, repository, resource_type, resource_id, request_fingerprint = record_with
        _record_submission(
            command,
            repository=repository,
            resource_type=resource_type,
            resource_id=resource_id,
            source_authority=source_authority,
            target=target,
            status=result.status,
            request_fingerprint=request_fingerprint,
            failure_reason=failure_reason,
        )
    return result


def _record_submission_result(
    command: RealizeConversionIntentCommand | RealizeReportEvidencePackCommand,
    *,
    repository: DownstreamSubmissionRepository,
    resource_type: DownstreamSubmissionResourceType,
    resource_id: str,
    source_authority: SourceSystem,
    target: ConversionTarget,
    status: DownstreamRealizationStatus,
    request_fingerprint: str,
    failure_reason: str | None,
) -> DownstreamRealizationSubmissionResult:
    _record_submission(
        command,
        repository=repository,
        resource_type=resource_type,
        resource_id=resource_id,
        source_authority=source_authority,
        target=target,
        status=status,
        request_fingerprint=request_fingerprint,
        failure_reason=failure_reason,
    )
    return DownstreamRealizationSubmissionResult(
        status=status,
        source_authority=source_authority,
        target=target,
        downstream_failure_reason=failure_reason,
    )


def _record_submission(
    command: RealizeConversionIntentCommand | RealizeReportEvidencePackCommand,
    *,
    repository: DownstreamSubmissionRepository,
    resource_type: DownstreamSubmissionResourceType,
    resource_id: str,
    source_authority: SourceSystem,
    target: ConversionTarget,
    status: DownstreamRealizationStatus,
    request_fingerprint: str,
    failure_reason: str | None,
) -> None:
    submitted_at = command.submitted_at_utc or datetime.now(UTC)
    lease_owner = "downstream-realization"
    lease_attempt_id = f"legacy-{command.idempotency_key}"
    claimed = create_downstream_submission_claim(
        idempotency_key=command.idempotency_key,
        request_fingerprint=request_fingerprint,
        resource_type=resource_type,
        resource_id=resource_id,
        target=target,
        source_authority=source_authority,
        actor_subject=lease_owner,
        claimed_at_utc=submitted_at,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        lease_expires_at_utc=submitted_at + timedelta(minutes=5),
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
    )
    finalized = finalize_downstream_submission(
        claimed,
        lease_owner=lease_owner,
        lease_attempt_id=lease_attempt_id,
        posture=DownstreamSubmissionPosture(status.value),
        finalized_at_utc=submitted_at,
        failure_reason=failure_reason,
    )
    assert finalized.record is not None
    repository.record_downstream_submission(finalized.record)


def _idempotent_submission_result(
    repository: DownstreamSubmissionRepository,
    *,
    idempotency_key: str,
    request_fingerprint: str,
) -> DownstreamRealizationSubmissionResult | None:
    existing = repository.downstream_submission_by_idempotency_key(idempotency_key)
    if existing is None:
        return None
    if existing.request_fingerprint != request_fingerprint:
        return DownstreamRealizationSubmissionResult(
            status=DownstreamRealizationStatus.IDEMPOTENCY_CONFLICT,
            source_authority=None,
            target=None,
            downstream_failure_reason="idempotency_conflict",
        )
    return DownstreamRealizationSubmissionResult(
        status=DownstreamRealizationStatus(existing.status.value),
        source_authority=existing.source_authority,
        target=existing.target,
        downstream_failure_reason=existing.downstream_failure_reason,
        idempotency_replayed=True,
    )


def _submission_fingerprint(
    *,
    resource_type: DownstreamSubmissionResourceType,
    resource_id: str,
    target: ConversionTarget,
    source_authority: SourceSystem,
) -> str:
    return payload_fingerprint(
        {
            "resource_type": resource_type.value,
            "resource_id": resource_id,
            "target": target.value,
            "source_authority": source_authority.value,
        }
    )


def _find_conversion_intent(
    conversion_intent_id: str,
    *,
    repository: DownstreamSubmissionRepository,
) -> GovernedConversionIntent | None:
    return repository.conversion_intent_by_id(conversion_intent_id)


def _find_report_evidence_pack(
    report_evidence_pack_id: str,
    *,
    repository: DownstreamSubmissionRepository,
) -> GovernedReportEvidencePack | None:
    return repository.report_evidence_pack_by_id(report_evidence_pack_id)


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be UTC")
