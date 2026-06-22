from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain import (
    ConversionTarget,
    GovernedConversionIntent,
    GovernedReportEvidencePack,
    SourceSystem,
)
from app.ports.downstream_realization import (
    AdviseProposalRealizationClient,
    ManageActionRealizationClient,
    ReportEvidencePackMaterializationClient,
)
from app.ports.idea_repository import CandidateSnapshotRepository


class DownstreamRealizationStatus(StrEnum):
    ACCEPTED_BY_DOWNSTREAM = "accepted_by_downstream"
    REJECTED_BY_DOWNSTREAM = "rejected_by_downstream"
    NOT_FOUND = "not_found"
    UNSUPPORTED_TARGET = "unsupported_target"


@dataclass(frozen=True)
class RealizeConversionIntentCommand:
    conversion_intent_id: str
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.conversion_intent_id, "conversion_intent_id")


@dataclass(frozen=True)
class RealizeReportEvidencePackCommand:
    report_evidence_pack_id: str
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.report_evidence_pack_id, "report_evidence_pack_id")


@dataclass(frozen=True)
class DownstreamRealizationSubmissionResult:
    status: DownstreamRealizationStatus
    source_authority: SourceSystem | None
    target: ConversionTarget | None
    downstream_failure_reason: str | None = None
    records_downstream_outcome: bool = False
    grants_downstream_authority: bool = False
    supported_feature_promoted: bool = False


def submit_conversion_intent_to_downstream(
    command: RealizeConversionIntentCommand,
    *,
    repository: CandidateSnapshotRepository,
    advise_client: AdviseProposalRealizationClient,
    manage_client: ManageActionRealizationClient,
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

    if conversion_intent.intent.target is ConversionTarget.ADVISE_PROPOSAL:
        outcome = advise_client.submit_proposal_intent(
            conversion_intent,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
        )
    elif conversion_intent.intent.target is ConversionTarget.MANAGE_REVIEW:
        outcome = manage_client.submit_action_intent(
            conversion_intent,
            correlation_id=command.correlation_id,
            trace_id=command.trace_id,
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
    )


def submit_report_evidence_pack_to_downstream(
    command: RealizeReportEvidencePackCommand,
    *,
    repository: CandidateSnapshotRepository,
    report_client: ReportEvidencePackMaterializationClient,
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

    outcome = report_client.submit_report_evidence_pack_request(
        evidence_pack,
        correlation_id=command.correlation_id,
        trace_id=command.trace_id,
    )
    return _submission_result(
        accepted=outcome.accepted,
        source_authority=evidence_pack.report_source_authority,
        target=ConversionTarget.REPORT_EVIDENCE,
        failure_reason=outcome.failure_reason,
    )


def _submission_result(
    *,
    accepted: bool,
    source_authority: SourceSystem,
    target: ConversionTarget,
    failure_reason: str | None,
) -> DownstreamRealizationSubmissionResult:
    return DownstreamRealizationSubmissionResult(
        status=(
            DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM
            if accepted
            else DownstreamRealizationStatus.REJECTED_BY_DOWNSTREAM
        ),
        source_authority=source_authority,
        target=target,
        downstream_failure_reason=failure_reason,
    )


def _find_conversion_intent(
    conversion_intent_id: str,
    *,
    repository: CandidateSnapshotRepository,
) -> GovernedConversionIntent | None:
    for record in repository.snapshot().candidate_records.values():
        for conversion_intent in record.conversion_intents:
            if conversion_intent.intent.conversion_intent_id == conversion_intent_id:
                return conversion_intent
    return None


def _find_report_evidence_pack(
    report_evidence_pack_id: str,
    *,
    repository: CandidateSnapshotRepository,
) -> GovernedReportEvidencePack | None:
    for record in repository.snapshot().candidate_records.values():
        for evidence_pack in record.report_evidence_packs:
            if evidence_pack.report_evidence_pack_id == report_evidence_pack_id:
                return evidence_pack
    return None


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
