from __future__ import annotations

from fastapi import FastAPI, Header, Path, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field

from app.api.base_model import CamelModel
from app.api.caller_headers import caller_context_from_headers
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
    service_unavailable_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    DownstreamRealizationClientsUnavailableError,
    get_conversion_realization_clients,
    get_idea_repository,
    get_report_evidence_pack_realization_client,
    idea_repository_durable_storage_backed,
)
from app.application.downstream_realization import (
    DownstreamRealizationStatus,
    DownstreamRealizationSubmissionResult,
    RealizeConversionIntentCommand,
    RealizeReportEvidencePackCommand,
    submit_conversion_intent_to_downstream,
    submit_report_evidence_pack_to_downstream,
)
from app.domain import ConversionTarget, SourceSystem
from app.api.problem_details import problem_details_response as problem_response
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.security.caller_context import CallerContext, PermissionDeniedError

_DOWNSTREAM_REALIZATION_SUBMIT_CAPABILITY = "idea.downstream-realization.submit"
_SUBMISSION_ERROR_CODES_BY_STATUS = {
    DownstreamRealizationStatus.NOT_FOUND: "downstream_realization_resource_not_found",
    DownstreamRealizationStatus.UNSUPPORTED_TARGET: "unsupported_downstream_realization_target",
    DownstreamRealizationStatus.IDEMPOTENCY_CONFLICT: "idempotency_conflict",
    DownstreamRealizationStatus.NOT_CONFIGURED: "downstream_realization_not_configured",
}


class DownstreamSubmissionResultResponse(CamelModel):
    submission_status: DownstreamRealizationStatus = Field(..., alias="submissionStatus")
    source_authority: SourceSystem | None = Field(default=None, alias="sourceAuthority")
    target: ConversionTarget | None = None
    downstream_failure_reason: str | None = Field(default=None, alias="downstreamFailureReason")
    idempotency_replayed: bool = Field(False, alias="idempotencyReplayed")
    records_downstream_outcome: bool = Field(False, alias="recordsDownstreamOutcome")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        result: DownstreamRealizationSubmissionResult,
    ) -> "DownstreamSubmissionResultResponse":
        return cls(
            submissionStatus=result.status,
            sourceAuthority=result.source_authority,
            target=result.target,
            downstreamFailureReason=result.downstream_failure_reason,
            idempotencyReplayed=result.idempotency_replayed,
            recordsDownstreamOutcome=result.records_downstream_outcome,
            grantsDownstreamAuthority=result.grants_downstream_authority,
            supportedFeaturePromoted=result.supported_feature_promoted,
        )


class DownstreamSubmissionApiResponse(CamelModel):
    downstream_submission: DownstreamSubmissionResultResponse = Field(
        ...,
        alias="downstreamSubmission",
    )
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def submit_conversion_intent_downstream(
    request: Request,
    conversion_intent_id: str = Path(..., alias="conversionIntentId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> DownstreamSubmissionApiResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_submission_caller(caller)
        validate_idempotency_key(idempotency_key)
    except PermissionDeniedError:
        _emit_downstream_submission_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied()
    except ValueError:
        _emit_downstream_submission_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return _invalid_request()

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        _emit_downstream_submission_event(
            OperationOutcome.BLOCKED,
            DURABLE_REPOSITORY_NOT_CONFIGURED,
            durable_storage_backed=durable_storage_backed,
        )
        return configuration_problem
    try:
        clients = get_conversion_realization_clients()
        advise_client = clients.advise_client
        manage_client = clients.manage_client
    except DownstreamRealizationClientsUnavailableError:
        advise_client = None
        manage_client = None
    result = submit_conversion_intent_to_downstream(
        RealizeConversionIntentCommand(
            conversion_intent_id=conversion_intent_id,
            idempotency_key=idempotency_key,
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        repository=repository,
        advise_client=advise_client,
        manage_client=manage_client,
    )
    problem = _problem_for_submission_result(result)
    if problem is not None:
        _emit_downstream_submission_event(
            _operation_outcome_from_submission_status(result.status),
            _error_code_from_submission_status(result.status),
            durable_storage_backed=durable_storage_backed,
        )
        return problem
    _emit_downstream_submission_event(
        _operation_outcome_from_submission_status(result.status),
        result.downstream_failure_reason,
        durable_storage_backed=durable_storage_backed,
    )
    return DownstreamSubmissionApiResponse(
        downstreamSubmission=DownstreamSubmissionResultResponse.from_domain(result),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


async def submit_report_evidence_pack_downstream(
    request: Request,
    report_evidence_pack_id: str = Path(..., alias="reportEvidencePackId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> DownstreamSubmissionApiResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_submission_caller(caller)
        validate_idempotency_key(idempotency_key)
    except PermissionDeniedError:
        _emit_downstream_submission_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied()
    except ValueError:
        _emit_downstream_submission_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return _invalid_request()

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        _emit_downstream_submission_event(
            OperationOutcome.BLOCKED,
            DURABLE_REPOSITORY_NOT_CONFIGURED,
            durable_storage_backed=durable_storage_backed,
        )
        return configuration_problem
    try:
        report_client = get_report_evidence_pack_realization_client()
    except DownstreamRealizationClientsUnavailableError:
        report_client = None
    result = submit_report_evidence_pack_to_downstream(
        RealizeReportEvidencePackCommand(
            report_evidence_pack_id=report_evidence_pack_id,
            idempotency_key=idempotency_key,
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        repository=repository,
        report_client=report_client,
    )
    problem = _problem_for_submission_result(result)
    if problem is not None:
        _emit_downstream_submission_event(
            _operation_outcome_from_submission_status(result.status),
            _error_code_from_submission_status(result.status),
            durable_storage_backed=durable_storage_backed,
        )
        return problem
    _emit_downstream_submission_event(
        _operation_outcome_from_submission_status(result.status),
        result.downstream_failure_reason,
        durable_storage_backed=durable_storage_backed,
    )
    return DownstreamSubmissionApiResponse(
        downstreamSubmission=DownstreamSubmissionResultResponse.from_domain(result),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _require_submission_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_DOWNSTREAM_REALIZATION_SUBMIT_CAPABILITY):
        raise PermissionDeniedError(_DOWNSTREAM_REALIZATION_SUBMIT_CAPABILITY)


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


def _problem_for_submission_result(
    result: DownstreamRealizationSubmissionResult,
) -> JSONResponse | None:
    if result.status is DownstreamRealizationStatus.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="downstream_realization_resource_not_found",
            title="Downstream realization resource not found",
            detail="The requested idea downstream realization resource was not found.",
        )
    if result.status is DownstreamRealizationStatus.UNSUPPORTED_TARGET:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="unsupported_downstream_realization_target",
            title="Unsupported downstream realization target",
            detail=(
                "The requested conversion target cannot be submitted through this "
                "downstream realization route."
            ),
        )
    if result.status is DownstreamRealizationStatus.IDEMPOTENCY_CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail=(
                "The supplied Idempotency-Key was already used for a different "
                "downstream realization submission target."
            ),
        )
    if result.status is DownstreamRealizationStatus.NOT_CONFIGURED:
        return _downstream_not_configured()
    return None


def _permission_denied() -> JSONResponse:
    return problem_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail="The caller is not permitted to submit idea downstream realization requests.",
    )


def _invalid_request() -> JSONResponse:
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="Correct the downstream realization request and retry.",
    )


def _downstream_not_configured() -> JSONResponse:
    return problem_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="downstream_realization_not_configured",
        title="Downstream realization not configured",
        detail=(
            "The service is not configured to submit this downstream realization "
            "request. Configure the owning downstream service adapter before retrying."
        ),
    )


def _operation_outcome_from_submission_status(
    submission_status: DownstreamRealizationStatus,
) -> OperationOutcome:
    if submission_status is DownstreamRealizationStatus.ACCEPTED_BY_DOWNSTREAM:
        return OperationOutcome.ACCEPTED
    if submission_status is DownstreamRealizationStatus.REJECTED_BY_DOWNSTREAM:
        return OperationOutcome.BLOCKED
    if submission_status is DownstreamRealizationStatus.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    if submission_status is DownstreamRealizationStatus.IDEMPOTENCY_CONFLICT:
        return OperationOutcome.CONFLICT
    if submission_status is DownstreamRealizationStatus.NOT_CONFIGURED:
        return OperationOutcome.BLOCKED
    return OperationOutcome.INVALID_STATE


def _error_code_from_submission_status(
    submission_status: DownstreamRealizationStatus,
) -> str | None:
    return _SUBMISSION_ERROR_CODES_BY_STATUS.get(submission_status)


def _emit_downstream_submission_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    *,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.DOWNSTREAM_REALIZATION_SUBMISSION,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE: RouteMetadata = {
    "path": "/api/v1/conversion-intents/{conversionIntentId}/downstream-submissions",
    "operation_id": "submitIdeaConversionIntentDownstream",
    "summary": "Submit an idea conversion intent downstream",
    "description": (
        "Submits an existing Advise or Manage conversion intent through the source-safe "
        "downstream realization adapter foundation. The route requires the "
        "idea.downstream-realization.submit capability and Idempotency-Key, propagates "
        "correlation and trace identifiers, and returns only submission posture. It does "
        "not record authoritative downstream outcomes, grant suitability or execution "
        "authority, prove downstream route certification, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DownstreamSubmissionApiResponse,
    "tags": ["Idea Downstream Realization"],
    "responses": {
        200: {
            "description": "Downstream submission accepted or source-safely rejected.",
            "content": {
                "application/json": {
                    "example": {
                        "downstreamSubmission": {
                            "submissionStatus": "accepted_by_downstream",
                            "sourceAuthority": "lotus-advise",
                            "target": "advise_proposal",
                            "downstreamFailureReason": None,
                            "idempotencyReplayed": False,
                            "recordsDownstreamOutcome": False,
                            "grantsDownstreamAuthority": False,
                            "supportedFeaturePromoted": False,
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the downstream submission request and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to submit idea conversion intents downstream.",
            description="Caller lacks submission permission.",
        ),
        **not_found_metadata(
            code="conversion_intent_not_found",
            title="Conversion intent not found",
            detail="No conversion intent exists for the requested conversionIntentId.",
            description="Conversion intent was not found.",
        ),
        **conflict_metadata(
            code="unsupported_downstream_target",
            title="Unsupported downstream target",
            detail=(
                "The conversion intent target is not supported by the requested "
                "downstream submission route."
            ),
            description="Conversion intent target is not supported by this submission route.",
        ),
        **service_unavailable_metadata(
            code="downstream_realization_unavailable",
            title="Downstream realization unavailable",
            detail="The downstream realization adapter foundation is not configured.",
            description="Downstream realization adapters are not configured.",
        ),
        **durable_repository_not_configured_metadata(),
    },
}


REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE: RouteMetadata = {
    "path": "/api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions",
    "operation_id": "submitIdeaReportEvidencePackDownstream",
    "summary": "Submit an idea report evidence pack downstream",
    "description": (
        "Submits an existing governed report evidence-pack request through the source-safe "
        "Report downstream realization adapter foundation. The route requires the "
        "idea.downstream-realization.submit capability and Idempotency-Key, propagates "
        "correlation and trace identifiers, and returns only submission posture. It does "
        "not create Report packages, Render outputs, Archive records, client-ready "
        "publication authority, downstream outcome records, or a supported feature claim."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": DownstreamSubmissionApiResponse,
    "tags": ["Idea Downstream Realization"],
    "responses": {
        200: {
            "description": "Report evidence-pack downstream submission accepted or rejected.",
            "content": {
                "application/json": {
                    "example": {
                        "downstreamSubmission": {
                            "submissionStatus": "accepted_by_downstream",
                            "sourceAuthority": "lotus-report",
                            "target": "report_evidence",
                            "downstreamFailureReason": None,
                            "idempotencyReplayed": False,
                            "recordsDownstreamOutcome": False,
                            "grantsDownstreamAuthority": False,
                            "supportedFeaturePromoted": False,
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the report evidence-pack downstream submission request and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to submit report evidence packs downstream.",
            description="Caller lacks submission permission.",
        ),
        **not_found_metadata(
            code="report_evidence_pack_not_found",
            title="Report evidence pack not found",
            detail="No report evidence pack exists for the requested reportEvidencePackId.",
            description="Report evidence-pack was not found.",
        ),
        **service_unavailable_metadata(
            code="downstream_realization_unavailable",
            title="Downstream realization unavailable",
            detail="The downstream realization adapter foundation is not configured.",
            description="Downstream realization adapters are not configured.",
        ),
        **durable_repository_not_configured_metadata(),
    },
}


def register_downstream_realization_routes(app: FastAPI) -> None:
    app.post(
        path=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["path"],
        operation_id=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["operation_id"],
        summary=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["summary"],
        description=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["description"],
        status_code=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["status_code"],
        response_model=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["response_model"],
        tags=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["tags"],
        responses=CONVERSION_INTENT_DOWNSTREAM_SUBMISSION_ROUTE["responses"],
    )(submit_conversion_intent_downstream)
    app.post(
        path=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["path"],
        operation_id=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["operation_id"],
        summary=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["summary"],
        description=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["description"],
        status_code=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["status_code"],
        response_model=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["response_model"],
        tags=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["tags"],
        responses=REPORT_EVIDENCE_PACK_DOWNSTREAM_SUBMISSION_ROUTE["responses"],
    )(submit_report_evidence_pack_downstream)
