from __future__ import annotations

from fastapi import FastAPI, Header, Path, Request, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER
from app.api.conversion_governance_models import (
    ConversionIntentApiResponse,
    ConversionIntentRequest,
    ConversionIntentResponse,
    ConversionOutcomeApiResponse,
    ConversionOutcomeRequest,
    ConversionOutcomeResponse,
    ConversionPersistenceSummaryResponse,
)
from app.api.conversion_governance_operations import (
    ConversionCallerHeaders,
    emit_conversion_operation_event,
    error_code_from_conversion_decision,
    operation_outcome_from_conversion_decision,
    permission_denied,
    prepare_conversion_mutation,
    problem_for_conversion_persistence,
)
from app.api.durable_write_guard import durable_repository_write_unavailable_metadata
from app.api.event_lineage import EventCausationHeader, event_lineage_from_request
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    merged_problem_response_metadata,
    not_found_metadata,
    permission_denied_metadata,
)
from app.api.route_metadata import RouteMetadata
from app.application.conversion_workflow import (
    record_conversion_outcome_to_repository,
    request_conversion_intent_to_repository,
)
from app.domain import (
    InvalidConversionIntent,
    InvalidConversionOutcome,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import PermissionDeniedError

_CONVERSION_INTENT_CAPABILITY = "idea.conversion.intent.record"
_CONVERSION_OUTCOME_CAPABILITY = "idea.conversion.outcome.record"

_CONVERSION_IDEMPOTENCY_CONFLICT = conflict_metadata(
    code="idempotency_conflict",
    title="Idempotency conflict",
    detail="The idempotency key was already used with a different request payload.",
    description="The transport idempotency key conflicts with an earlier request.",
)
_CONVERSION_OUTCOME_CONFLICT = conflict_metadata(
    code="conversion_outcome_conflict",
    title="Conversion outcome conflict",
    detail="The conversion outcome conflicts with the governed source-event history.",
    description="The source event identity, version, transition, or correction is invalid.",
)

__all__ = [
    "ConversionIntentApiResponse",
    "ConversionIntentRequest",
    "ConversionIntentResponse",
    "ConversionOutcomeApiResponse",
    "ConversionOutcomeRequest",
    "ConversionOutcomeResponse",
    "ConversionPersistenceSummaryResponse",
    "register_conversion_governance_routes",
]


async def record_conversion_intent(
    request: ConversionIntentRequest,
    http_request: Request,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
    x_causation_id: EventCausationHeader = None,
) -> ConversionIntentApiResponse | JSONResponse:
    try:
        context = prepare_conversion_mutation(
            headers=ConversionCallerHeaders(
                subject=x_caller_subject,
                roles=x_caller_roles,
                capabilities=x_caller_capabilities,
                trusted_caller_context=x_lotus_trusted_caller_context,
            ),
            capability=_CONVERSION_INTENT_CAPABILITY,
            idempotency_key=idempotency_key,
            operation=IdeaOperation.CONVERSION_INTENT,
        )
        if isinstance(context, JSONResponse):
            return context
        result = request_conversion_intent_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=context.caller,
                idempotency_key=idempotency_key,
                event_lineage=event_lineage_from_request(
                    http_request,
                    causation_id=x_causation_id,
                ),
            ),
            repository=context.repository,
        )
    except PermissionDeniedError:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_INTENT,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return permission_denied("The caller is not permitted to record idea conversion intents.")
    except InvalidConversionIntent:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_INTENT,
            OperationOutcome.INVALID_STATE,
            "conversion_intent_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="conversion_intent_conflict",
            title="Conversion intent conflict",
            detail="The conversion intent is not valid for the current idea candidate state.",
        )
    except ValueError:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_INTENT,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the conversion intent request and retry.",
        )

    problem = problem_for_conversion_persistence(result.persistence)
    if problem is not None:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_INTENT,
            operation_outcome_from_conversion_decision(result.persistence.decision),
            error_code_from_conversion_decision(result.persistence.decision),
            context.durable_storage_backed,
        )
        return problem
    emit_conversion_operation_event(
        IdeaOperation.CONVERSION_INTENT,
        operation_outcome_from_conversion_decision(result.persistence.decision),
        durable_storage_backed=context.durable_storage_backed,
    )
    return ConversionIntentApiResponse(
        conversionIntent=(
            ConversionIntentResponse.from_domain(result.conversion_result.conversion_intent)
            if result.conversion_result is not None
            else None
        ),
        persistence=ConversionPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=context.durable_storage_backed,
        supportedFeaturePromoted=False,
    )


async def record_conversion_outcome(
    request: ConversionOutcomeRequest,
    http_request: Request,
    conversion_intent_id: str = Path(..., alias="conversionIntentId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
    x_causation_id: EventCausationHeader = None,
) -> ConversionOutcomeApiResponse | JSONResponse:
    try:
        context = prepare_conversion_mutation(
            headers=ConversionCallerHeaders(
                subject=x_caller_subject,
                roles=x_caller_roles,
                capabilities=x_caller_capabilities,
                trusted_caller_context=x_lotus_trusted_caller_context,
            ),
            capability=_CONVERSION_OUTCOME_CAPABILITY,
            idempotency_key=idempotency_key,
            operation=IdeaOperation.CONVERSION_OUTCOME,
        )
        if isinstance(context, JSONResponse):
            return context
        result = record_conversion_outcome_to_repository(
            request.to_command(
                conversion_intent_id=conversion_intent_id,
                caller=context.caller,
                idempotency_key=idempotency_key,
                event_lineage=event_lineage_from_request(
                    http_request,
                    causation_id=x_causation_id,
                ),
            ),
            repository=context.repository,
        )
    except PermissionDeniedError:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_OUTCOME,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return permission_denied("The caller is not permitted to record idea conversion outcomes.")
    except InvalidConversionOutcome:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_OUTCOME,
            OperationOutcome.INVALID_STATE,
            "conversion_outcome_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="conversion_outcome_conflict",
            title="Conversion outcome conflict",
            detail="The conversion outcome is not valid for the recorded conversion intent.",
        )
    except ValueError:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_OUTCOME,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the conversion outcome request and retry.",
        )

    problem = problem_for_conversion_persistence(result.persistence)
    if problem is not None:
        emit_conversion_operation_event(
            IdeaOperation.CONVERSION_OUTCOME,
            operation_outcome_from_conversion_decision(result.persistence.decision),
            error_code_from_conversion_decision(result.persistence.decision),
            context.durable_storage_backed,
        )
        return problem
    emit_conversion_operation_event(
        IdeaOperation.CONVERSION_OUTCOME,
        operation_outcome_from_conversion_decision(result.persistence.decision),
        durable_storage_backed=context.durable_storage_backed,
    )
    return ConversionOutcomeApiResponse(
        conversionOutcome=(
            ConversionOutcomeResponse.from_domain(result.outcome_result.conversion_outcome)
            if result.outcome_result is not None
            else None
        ),
        persistence=ConversionPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=context.durable_storage_backed,
        supportedFeaturePromoted=False,
    )


CONVERSION_INTENT_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/conversion-intents",
    "operation_id": "recordIdeaCandidateConversionIntent",
    "summary": "Record an idea candidate conversion intent",
    "description": (
        "Records an internal governed conversion intent for an approved idea candidate "
        "through the RFC-0002 Slice 12 conversion foundation. The route requires a "
        "conversion-intent capability and Idempotency-Key, transitions only through the "
        "canonical idea lifecycle graph, and does not grant Advise, Manage, Report, "
        "suitability, execution, or client-communication authority."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ConversionIntentApiResponse,
    "tags": ["Idea Conversion"],
    "responses": {
        200: {
            "description": "Conversion intent accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "conversionIntent": {
                            "conversionIntentId": "conversion-report-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "target": "report_evidence",
                            "sourceStatus": "approved",
                            "targetSourceAuthority": "lotus-report",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "evidenceContentHash": "sha256:evidence-lineage",
                            "sourceSignalIds": ["signal_high_cash_8d57adbf52f7f5a7"],
                            "boundary": "intent_only",
                            "reasonCodes": ["review_approved_for_conversion"],
                            "requestedAtUtc": "2026-06-21T10:15:00Z",
                            "grantsDownstreamAuthority": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "converted_to_report",
                            "reviewPosture": "approved_for_conversion",
                            "auditEventType": "idea.conversion.intent_requested",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the conversion intent request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to record idea conversion intents.",
            description="Caller lacks conversion permission.",
        ),
        **not_found_metadata(
            code="conversion_resource_not_found",
            title="Conversion resource not found",
            detail="The requested idea conversion resource was not found.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="conversion_intent_conflict",
            title="Conversion intent conflict",
            detail="The conversion intent is not valid for the current idea candidate state.",
            description="Idempotency conflict or invalid conversion intent state.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


CONVERSION_OUTCOME_ROUTE: RouteMetadata = {
    "path": "/api/v1/conversion-intents/{conversionIntentId}/outcomes",
    "operation_id": "recordIdeaConversionOutcome",
    "summary": "Record an idea conversion outcome",
    "description": (
        "Records an internal downstream conversion outcome against a previously recorded "
        "idea conversion intent. Source-event identity and version are independent of the "
        "transport idempotency key; legal progression and append-only corrections are "
        "validated before persistence. The route verifies that the reporting source system "
        "matches the target source authority, writes audit evidence, and remains an "
        "internal foundation. Process-local writes are allowed only for local/test "
        "profiles; production-like profiles require LOTUS_IDEA_DATABASE_URL. "
        "Downstream contracts, Gateway, "
        "Workbench, and data-product certification remain separate promotion gates."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ConversionOutcomeApiResponse,
    "tags": ["Idea Conversion"],
    "responses": {
        200: {
            "description": "Conversion outcome accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "conversionOutcome": {
                            "conversionOutcomeId": "conversion-report-outcome-001",
                            "conversionIntentId": "conversion-report-001",
                            "target": "report_evidence",
                            "status": "accepted",
                            "sourceSystem": "lotus-report",
                            "sourceEventVersion": 1,
                            "downstreamReference": "report-evidence-pack-001",
                            "supersedesConversionOutcomeId": None,
                            "correctionReason": None,
                            "boundary": "downstream_realization_required",
                            "recordedAtUtc": "2026-06-21T10:20:00Z",
                            "grantsExecutionAuthority": False,
                            "grantsClientCommunicationAuthority": False,
                            "grantsSuitabilityAuthority": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "converted_to_report",
                            "reviewPosture": "approved_for_conversion",
                            "auditEventType": "idea.conversion.outcome_recorded",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the conversion outcome request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to record idea conversion outcomes.",
            description="Caller lacks conversion permission.",
        ),
        **not_found_metadata(
            code="conversion_resource_not_found",
            title="Conversion resource not found",
            detail="The requested idea conversion resource was not found.",
            description="Conversion intent was not found.",
        ),
        **merged_problem_response_metadata(
            status_code=status.HTTP_409_CONFLICT,
            description="Conversion outcome mutation conflict.",
            responses=(
                _CONVERSION_IDEMPOTENCY_CONFLICT,
                _CONVERSION_OUTCOME_CONFLICT,
            ),
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_conversion_governance_routes(app: FastAPI) -> None:
    app.post(
        path=CONVERSION_INTENT_ROUTE["path"],
        operation_id=CONVERSION_INTENT_ROUTE["operation_id"],
        summary=CONVERSION_INTENT_ROUTE["summary"],
        description=CONVERSION_INTENT_ROUTE["description"],
        status_code=CONVERSION_INTENT_ROUTE["status_code"],
        response_model=CONVERSION_INTENT_ROUTE["response_model"],
        tags=CONVERSION_INTENT_ROUTE["tags"],
        responses=CONVERSION_INTENT_ROUTE["responses"],
    )(record_conversion_intent)
    app.post(
        path=CONVERSION_OUTCOME_ROUTE["path"],
        operation_id=CONVERSION_OUTCOME_ROUTE["operation_id"],
        summary=CONVERSION_OUTCOME_ROUTE["summary"],
        description=CONVERSION_OUTCOME_ROUTE["description"],
        status_code=CONVERSION_OUTCOME_ROUTE["status_code"],
        response_model=CONVERSION_OUTCOME_ROUTE["response_model"],
        tags=CONVERSION_OUTCOME_ROUTE["tags"],
        responses=CONVERSION_OUTCOME_ROUTE["responses"],
    )(record_conversion_outcome)
