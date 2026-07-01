from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER, caller_context_from_headers
from app.api.durable_write_guard import (
    DURABLE_REPOSITORY_NOT_CONFIGURED,
    durable_repository_not_configured_metadata,
    durable_write_problem,
)
from app.api.idempotency import validate_idempotency_key
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    not_found_metadata,
    permission_denied_metadata,
    permission_denied_problem,
)
from app.api.persistence_summary import persistence_summary_payload
from app.api.request_validation import require_non_empty_reason_codes
from app.api.route_metadata import RouteMetadata
from app.api.temporal_validation import require_timezone_aware
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.report_evidence import (
    RequestReportEvidencePackToRepositoryCommand,
    request_report_evidence_pack_to_repository,
)
from app.domain import (
    EvidencePackPersistenceDecision,
    EvidencePackPersistenceResult,
    GovernedReportEvidencePack,
    InvalidReportEvidencePack,
    ReasonCode,
    ReportEvidencePackCommand,
    ReportEvidencePackPurpose,
    ReportEvidenceSourceSummary,
    SourceSystem,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationEvent, OperationOutcome, emit_operation_event
from app.security.caller_context import CallerContext, PermissionDeniedError

_REPORT_EVIDENCE_PACK_CAPABILITY = "idea.report-evidence-pack.request"


class ReportEvidencePackRequest(CamelModel):
    report_evidence_pack_id: str = Field(..., alias="reportEvidencePackId")
    purpose: ReportEvidencePackPurpose
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    retention_policy_ref: str = Field(..., alias="retentionPolicyRef")
    client_ready_publication_requested: bool = Field(
        False,
        alias="clientReadyPublicationRequested",
    )

    @field_validator("report_evidence_pack_id")
    @classmethod
    def _pack_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reportEvidencePackId is required")
        return value

    _reason_codes_must_not_be_empty = field_validator("reason_codes")(
        require_non_empty_reason_codes
    )

    @field_validator("requested_at_utc")
    @classmethod
    def _requested_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="requestedAtUtc")

    @field_validator("retention_policy_ref")
    @classmethod
    def _retention_policy_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("retentionPolicyRef is required")
        return value

    def to_command(
        self,
        *,
        conversion_intent_id: str,
        caller: CallerContext,
        idempotency_key: str,
    ) -> RequestReportEvidencePackToRepositoryCommand:
        return RequestReportEvidencePackToRepositoryCommand(
            conversion_intent_id=conversion_intent_id,
            evidence_pack=ReportEvidencePackCommand(
                report_evidence_pack_id=self.report_evidence_pack_id,
                purpose=self.purpose,
                actor_subject=caller.subject,
                idempotency_key=idempotency_key,
                reason_codes=self.reason_codes,
                requested_at_utc=self.requested_at_utc,
                retention_policy_ref=self.retention_policy_ref,
                client_ready_publication_requested=self.client_ready_publication_requested,
            ),
            idempotency_key=idempotency_key,
        )


class ReportEvidenceSourceSummaryResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    product_version: str = Field(..., alias="productVersion")
    as_of_date: str = Field(..., alias="asOfDate")
    generated_at_utc: datetime = Field(..., alias="generatedAtUtc")
    content_hash: str = Field(..., alias="contentHash")
    data_quality_status: str = Field(..., alias="dataQualityStatus")
    freshness: str

    @classmethod
    def from_domain(
        cls,
        summary: ReportEvidenceSourceSummary,
    ) -> "ReportEvidenceSourceSummaryResponse":
        return cls(
            productId=summary.product_id,
            sourceSystem=summary.source_system,
            productVersion=summary.product_version,
            asOfDate=summary.as_of_date,
            generatedAtUtc=summary.generated_at_utc,
            contentHash=summary.content_hash,
            dataQualityStatus=summary.data_quality_status,
            freshness=summary.freshness,
        )


class ReportEvidencePackResponse(CamelModel):
    report_evidence_pack_id: str = Field(..., alias="reportEvidencePackId")
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    candidate_id: str = Field(..., alias="candidateId")
    purpose: ReportEvidencePackPurpose
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    source_summaries: tuple[ReportEvidenceSourceSummaryResponse, ...] = Field(
        ...,
        alias="sourceSummaries",
    )
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    report_source_authority: SourceSystem = Field(..., alias="reportSourceAuthority")
    render_source_authority: SourceSystem = Field(..., alias="renderSourceAuthority")
    archive_source_authority: SourceSystem = Field(..., alias="archiveSourceAuthority")
    boundary: str
    retention_policy_ref: str = Field(..., alias="retentionPolicyRef")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    grants_client_publication_authority: bool = Field(
        False,
        alias="grantsClientPublicationAuthority",
    )
    creates_rendered_output: bool = Field(False, alias="createsRenderedOutput")
    creates_archive_record: bool = Field(False, alias="createsArchiveRecord")

    @classmethod
    def from_domain(cls, evidence_pack: GovernedReportEvidencePack) -> "ReportEvidencePackResponse":
        return cls(
            reportEvidencePackId=evidence_pack.report_evidence_pack_id,
            conversionIntentId=evidence_pack.conversion_intent_id,
            candidateId=evidence_pack.candidate_id,
            purpose=evidence_pack.purpose,
            evidencePacketId=evidence_pack.evidence_packet_id,
            evidenceContentHash=evidence_pack.evidence_content_hash,
            sourceSignalIds=evidence_pack.source_signal_ids,
            sourceSummaries=tuple(
                ReportEvidenceSourceSummaryResponse.from_domain(summary)
                for summary in evidence_pack.source_summaries
            ),
            reasonCodes=tuple(reason.value for reason in evidence_pack.reason_codes),
            reportSourceAuthority=evidence_pack.report_source_authority,
            renderSourceAuthority=evidence_pack.render_source_authority,
            archiveSourceAuthority=evidence_pack.archive_source_authority,
            boundary=evidence_pack.boundary.value,
            retentionPolicyRef=evidence_pack.retention_policy_ref,
            requestedAtUtc=evidence_pack.requested_at_utc,
            grantsClientPublicationAuthority=evidence_pack.grants_client_publication_authority,
            createsRenderedOutput=evidence_pack.creates_rendered_output,
            createsArchiveRecord=evidence_pack.creates_archive_record,
        )


class EvidencePackPersistenceSummaryResponse(CamelModel):
    decision: EvidencePackPersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    review_posture: str | None = Field(default=None, alias="reviewPosture")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_result(
        cls,
        result: EvidencePackPersistenceResult,
    ) -> "EvidencePackPersistenceSummaryResponse":
        return cls(**persistence_summary_payload(result))


class ReportEvidencePackApiResponse(CamelModel):
    report_evidence_pack: ReportEvidencePackResponse | None = Field(
        default=None,
        alias="reportEvidencePack",
    )
    persistence: EvidencePackPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def record_report_evidence_pack(
    request: ReportEvidencePackRequest,
    conversion_intent_id: str = Path(..., alias="conversionIntentId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ReportEvidencePackApiResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        _require_report_evidence_caller(caller)
        validate_idempotency_key(idempotency_key)
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        configuration_problem = durable_write_problem(repository)
        if configuration_problem is not None:
            _emit_report_evidence_operation_event(
                OperationOutcome.BLOCKED,
                DURABLE_REPOSITORY_NOT_CONFIGURED,
                durable_storage_backed,
            )
            return configuration_problem
        result = request_report_evidence_pack_to_repository(
            request.to_command(
                conversion_intent_id=conversion_intent_id,
                caller=caller,
                idempotency_key=idempotency_key,
            ),
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_report_evidence_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied(
            "The caller is not permitted to request idea report evidence packs."
        )
    except InvalidReportEvidencePack:
        _emit_report_evidence_operation_event(
            OperationOutcome.INVALID_STATE,
            "report_evidence_pack_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="report_evidence_pack_conflict",
            title="Report evidence pack conflict",
            detail="The report evidence pack request is not valid for the current conversion state.",
        )
    except ValueError:
        _emit_report_evidence_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the report evidence pack request and retry.",
        )

    problem = _problem_for_evidence_pack_persistence(result.persistence)
    if problem is not None:
        _emit_report_evidence_operation_event(
            _operation_outcome_from_evidence_pack_decision(result.persistence.decision),
            _error_code_from_evidence_pack_decision(result.persistence.decision),
            durable_storage_backed,
        )
        return problem
    _emit_report_evidence_operation_event(
        _operation_outcome_from_evidence_pack_decision(result.persistence.decision),
        durable_storage_backed=durable_storage_backed,
    )
    return ReportEvidencePackApiResponse(
        reportEvidencePack=(
            ReportEvidencePackResponse.from_domain(result.evidence_pack_result.evidence_pack)
            if result.evidence_pack_result is not None
            else None
        ),
        persistence=EvidencePackPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _require_report_evidence_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_REPORT_EVIDENCE_PACK_CAPABILITY):
        raise PermissionDeniedError(_REPORT_EVIDENCE_PACK_CAPABILITY)


def _problem_for_evidence_pack_persistence(
    result: EvidencePackPersistenceResult,
) -> JSONResponse | None:
    if result.decision is EvidencePackPersistenceDecision.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="report_evidence_pack_resource_not_found",
            title="Report evidence pack resource not found",
            detail="The requested report evidence pack resource was not found.",
        )
    if result.decision is EvidencePackPersistenceDecision.CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )
    return None


def _permission_denied(detail: str) -> JSONResponse:
    return permission_denied_problem(detail)


def _emit_report_evidence_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.REPORT_EVIDENCE_PACK,
            outcome=outcome,
            source_authority="lotus-report",
            error_code=error_code,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
        )
    )


def _operation_outcome_from_evidence_pack_decision(
    decision: EvidencePackPersistenceDecision,
) -> OperationOutcome:
    if decision is EvidencePackPersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if decision is EvidencePackPersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if decision is EvidencePackPersistenceDecision.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    return OperationOutcome.CONFLICT


def _error_code_from_evidence_pack_decision(
    decision: EvidencePackPersistenceDecision,
) -> str | None:
    if decision is EvidencePackPersistenceDecision.NOT_FOUND:
        return "report_evidence_pack_resource_not_found"
    if decision is EvidencePackPersistenceDecision.CONFLICT:
        return "idempotency_conflict"
    return None


REPORT_EVIDENCE_PACK_ROUTE: RouteMetadata = {
    "path": "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
    "operation_id": "recordIdeaReportEvidencePack",
    "summary": "Record an idea report evidence pack request",
    "description": (
        "Records an internal report evidence-pack request for a reviewed idea that already "
        "has a report-evidence conversion intent. The route preserves source refs, lineage, "
        "retention posture, Report/Render/Archive source authority, and idempotency evidence, "
        "but it does not create lotus-report, lotus-render, or lotus-archive records and does "
        "not authorize client-ready publication."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ReportEvidencePackApiResponse,
    "tags": ["Idea Evidence Packs"],
    "responses": {
        200: {
            "description": (
                "Report evidence-pack request accepted or replayed through the internal "
                "repository foundation."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "reportEvidencePack": {
                            "reportEvidencePackId": "report-evidence-pack-001",
                            "conversionIntentId": "conversion-report-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "purpose": "client_review_report_section",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "evidenceContentHash": "sha256:evidence-lineage",
                            "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                            "sourceSummaries": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "contentHash": "sha256:portfolio-state",
                                    "dataQualityStatus": "complete",
                                    "freshness": "current",
                                }
                            ],
                            "reasonCodes": ["review_approved_for_conversion"],
                            "reportSourceAuthority": "lotus-report",
                            "renderSourceAuthority": "lotus-render",
                            "archiveSourceAuthority": "lotus-archive",
                            "boundary": "request_only",
                            "retentionPolicyRef": "lotus-report:idea-evidence-retention:v1",
                            "requestedAtUtc": "2026-06-21T10:25:00Z",
                            "grantsClientPublicationAuthority": False,
                            "createsRenderedOutput": False,
                            "createsArchiveRecord": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "converted_to_report",
                            "reviewPosture": "approved_for_conversion",
                            "auditEventType": "idea.report_evidence_pack.requested",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the report evidence pack request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to request idea report evidence packs.",
            description="Caller lacks evidence-pack permission.",
        ),
        **not_found_metadata(
            code="report_evidence_pack_resource_not_found",
            title="Report evidence pack resource not found",
            detail="The requested report evidence pack resource was not found.",
            description="Conversion intent or related candidate was not found.",
        ),
        **conflict_metadata(
            code="report_evidence_pack_conflict",
            title="Report evidence pack conflict",
            detail=(
                "The report evidence pack request is not valid for the current conversion state."
            ),
            description="Idempotency conflict or invalid report evidence-pack state.",
        ),
        **durable_repository_not_configured_metadata(),
    },
}


def register_report_evidence_routes(app: FastAPI) -> None:
    app.post(
        path=REPORT_EVIDENCE_PACK_ROUTE["path"],
        operation_id=REPORT_EVIDENCE_PACK_ROUTE["operation_id"],
        summary=REPORT_EVIDENCE_PACK_ROUTE["summary"],
        description=REPORT_EVIDENCE_PACK_ROUTE["description"],
        status_code=REPORT_EVIDENCE_PACK_ROUTE["status_code"],
        response_model=REPORT_EVIDENCE_PACK_ROUTE["response_model"],
        tags=REPORT_EVIDENCE_PACK_ROUTE["tags"],
        responses=REPORT_EVIDENCE_PACK_ROUTE["responses"],
    )(record_report_evidence_pack)
