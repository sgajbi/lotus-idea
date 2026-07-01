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
from app.application.conversion_workflow import (
    RecordConversionOutcomeToRepositoryCommand,
    RequestConversionIntentToRepositoryCommand,
    record_conversion_outcome_to_repository,
    request_conversion_intent_to_repository,
)
from app.domain import (
    ConversionIntentCommand,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    ConversionTarget,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    InvalidConversionIntent,
    InvalidConversionOutcome,
    ReasonCode,
    SourceSystem,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationEvent, OperationOutcome, emit_operation_event
from app.security.caller_context import CallerContext, PermissionDeniedError

_CONVERSION_INTENT_CAPABILITY = "idea.conversion.intent.record"
_CONVERSION_OUTCOME_CAPABILITY = "idea.conversion.outcome.record"


class ConversionIntentRequest(CamelModel):
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: ConversionTarget
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")

    @field_validator("conversion_intent_id")
    @classmethod
    def _intent_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("conversionIntentId is required")
        return value

    _reason_codes_must_not_be_empty = field_validator("reason_codes")(
        require_non_empty_reason_codes
    )

    @field_validator("requested_at_utc")
    @classmethod
    def _requested_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="requestedAtUtc")

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        idempotency_key: str,
    ) -> RequestConversionIntentToRepositoryCommand:
        return RequestConversionIntentToRepositoryCommand(
            candidate_id=candidate_id,
            conversion=ConversionIntentCommand(
                conversion_intent_id=self.conversion_intent_id,
                target=self.target,
                actor_subject=caller.subject,
                idempotency_key=idempotency_key,
                reason_codes=self.reason_codes,
                requested_at_utc=self.requested_at_utc,
            ),
            idempotency_key=idempotency_key,
        )


class ConversionOutcomeRequest(CamelModel):
    conversion_outcome_id: str = Field(..., alias="conversionOutcomeId")
    status: ConversionOutcomeStatus
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    downstream_reference: str | None = Field(default=None, alias="downstreamReference")
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")

    @field_validator("conversion_outcome_id")
    @classmethod
    def _outcome_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("conversionOutcomeId is required")
        return value

    @field_validator("downstream_reference")
    @classmethod
    def _downstream_reference_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("downstreamReference cannot be blank")
        return value

    @field_validator("recorded_at_utc")
    @classmethod
    def _recorded_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="recordedAtUtc")

    def to_command(
        self,
        *,
        conversion_intent_id: str,
        caller: CallerContext,
        idempotency_key: str,
    ) -> RecordConversionOutcomeToRepositoryCommand:
        return RecordConversionOutcomeToRepositoryCommand(
            conversion_intent_id=conversion_intent_id,
            outcome=ConversionOutcomeCommand(
                conversion_outcome_id=self.conversion_outcome_id,
                status=self.status,
                source_system=self.source_system,
                downstream_reference=self.downstream_reference,
                recorded_at_utc=self.recorded_at_utc,
                actor_subject=caller.subject,
            ),
            idempotency_key=idempotency_key,
        )


class ConversionIntentResponse(CamelModel):
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    candidate_id: str = Field(..., alias="candidateId")
    target: ConversionTarget
    source_status: str = Field(..., alias="sourceStatus")
    target_source_authority: SourceSystem = Field(..., alias="targetSourceAuthority")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    boundary: str
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")

    @classmethod
    def from_domain(cls, intent: GovernedConversionIntent) -> "ConversionIntentResponse":
        return cls(
            conversionIntentId=intent.intent.conversion_intent_id,
            candidateId=intent.intent.candidate_id,
            target=intent.intent.target,
            sourceStatus=intent.intent.source_status.value,
            targetSourceAuthority=intent.target_source_authority,
            evidencePacketId=intent.evidence_packet_id,
            evidenceContentHash=intent.evidence_content_hash,
            sourceSignalIds=intent.source_signal_ids,
            boundary=intent.boundary.value,
            reasonCodes=tuple(reason.value for reason in intent.reason_codes),
            requestedAtUtc=intent.intent.requested_at_utc,
            grantsDownstreamAuthority=intent.grants_downstream_authority,
        )


class ConversionOutcomeResponse(CamelModel):
    conversion_outcome_id: str = Field(..., alias="conversionOutcomeId")
    conversion_intent_id: str = Field(..., alias="conversionIntentId")
    target: ConversionTarget
    status: ConversionOutcomeStatus
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    downstream_reference: str | None = Field(default=None, alias="downstreamReference")
    boundary: str
    recorded_at_utc: datetime = Field(..., alias="recordedAtUtc")
    grants_execution_authority: bool = Field(False, alias="grantsExecutionAuthority")
    grants_client_communication_authority: bool = Field(
        False,
        alias="grantsClientCommunicationAuthority",
    )
    grants_suitability_authority: bool = Field(False, alias="grantsSuitabilityAuthority")

    @classmethod
    def from_domain(cls, outcome: GovernedConversionOutcome) -> "ConversionOutcomeResponse":
        return cls(
            conversionOutcomeId=outcome.outcome.conversion_outcome_id,
            conversionIntentId=outcome.conversion_intent_id,
            target=outcome.target,
            status=outcome.outcome.status,
            sourceSystem=outcome.source_system,
            downstreamReference=outcome.outcome.downstream_reference,
            boundary=outcome.boundary.value,
            recordedAtUtc=outcome.outcome.recorded_at_utc,
            grantsExecutionAuthority=outcome.grants_execution_authority,
            grantsClientCommunicationAuthority=outcome.grants_client_communication_authority,
            grantsSuitabilityAuthority=outcome.grants_suitability_authority,
        )


class ConversionPersistenceSummaryResponse(CamelModel):
    decision: ConversionPersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    review_posture: str | None = Field(default=None, alias="reviewPosture")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_result(
        cls,
        result: ConversionPersistenceResult,
    ) -> "ConversionPersistenceSummaryResponse":
        return cls(**persistence_summary_payload(result))


class ConversionIntentApiResponse(CamelModel):
    conversion_intent: ConversionIntentResponse | None = Field(
        default=None,
        alias="conversionIntent",
    )
    persistence: ConversionPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


class ConversionOutcomeApiResponse(CamelModel):
    conversion_outcome: ConversionOutcomeResponse | None = Field(
        default=None,
        alias="conversionOutcome",
    )
    persistence: ConversionPersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def record_conversion_intent(
    request: ConversionIntentRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ConversionIntentApiResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        _require_conversion_caller(caller, capability=_CONVERSION_INTENT_CAPABILITY)
        validate_idempotency_key(idempotency_key)
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        configuration_problem = durable_write_problem(repository)
        if configuration_problem is not None:
            _emit_conversion_operation_event(
                IdeaOperation.CONVERSION_INTENT,
                OperationOutcome.BLOCKED,
                DURABLE_REPOSITORY_NOT_CONFIGURED,
                durable_storage_backed,
            )
            return configuration_problem
        result = request_conversion_intent_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=caller,
                idempotency_key=idempotency_key,
            ),
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_conversion_operation_event(
            IdeaOperation.CONVERSION_INTENT,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to record idea conversion intents.")
    except InvalidConversionIntent:
        _emit_conversion_operation_event(
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
        _emit_conversion_operation_event(
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

    problem = _problem_for_conversion_persistence(result.persistence)
    if problem is not None:
        _emit_conversion_operation_event(
            IdeaOperation.CONVERSION_INTENT,
            _operation_outcome_from_conversion_decision(result.persistence.decision),
            _error_code_from_conversion_decision(result.persistence.decision),
            durable_storage_backed,
        )
        return problem
    _emit_conversion_operation_event(
        IdeaOperation.CONVERSION_INTENT,
        _operation_outcome_from_conversion_decision(result.persistence.decision),
        durable_storage_backed=durable_storage_backed,
    )
    return ConversionIntentApiResponse(
        conversionIntent=(
            ConversionIntentResponse.from_domain(result.conversion_result.conversion_intent)
            if result.conversion_result is not None
            else None
        ),
        persistence=ConversionPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


async def record_conversion_outcome(
    request: ConversionOutcomeRequest,
    conversion_intent_id: str = Path(..., alias="conversionIntentId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ConversionOutcomeApiResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )
    try:
        _require_conversion_caller(caller, capability=_CONVERSION_OUTCOME_CAPABILITY)
        validate_idempotency_key(idempotency_key)
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        configuration_problem = durable_write_problem(repository)
        if configuration_problem is not None:
            _emit_conversion_operation_event(
                IdeaOperation.CONVERSION_OUTCOME,
                OperationOutcome.BLOCKED,
                DURABLE_REPOSITORY_NOT_CONFIGURED,
                durable_storage_backed,
            )
            return configuration_problem
        result = record_conversion_outcome_to_repository(
            request.to_command(
                conversion_intent_id=conversion_intent_id,
                caller=caller,
                idempotency_key=idempotency_key,
            ),
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_conversion_operation_event(
            IdeaOperation.CONVERSION_OUTCOME,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to record idea conversion outcomes.")
    except InvalidConversionOutcome:
        _emit_conversion_operation_event(
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
        _emit_conversion_operation_event(
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

    problem = _problem_for_conversion_persistence(result.persistence)
    if problem is not None:
        _emit_conversion_operation_event(
            IdeaOperation.CONVERSION_OUTCOME,
            _operation_outcome_from_conversion_decision(result.persistence.decision),
            _error_code_from_conversion_decision(result.persistence.decision),
            durable_storage_backed,
        )
        return problem
    _emit_conversion_operation_event(
        IdeaOperation.CONVERSION_OUTCOME,
        _operation_outcome_from_conversion_decision(result.persistence.decision),
        durable_storage_backed=durable_storage_backed,
    )
    return ConversionOutcomeApiResponse(
        conversionOutcome=(
            ConversionOutcomeResponse.from_domain(result.outcome_result.conversion_outcome)
            if result.outcome_result is not None
            else None
        ),
        persistence=ConversionPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _require_conversion_caller(caller: CallerContext, *, capability: str) -> None:
    if not caller.has_capability(capability):
        raise PermissionDeniedError(capability)


def _problem_for_conversion_persistence(
    result: ConversionPersistenceResult,
) -> JSONResponse | None:
    if result.decision is ConversionPersistenceDecision.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="conversion_resource_not_found",
            title="Conversion resource not found",
            detail="The requested idea conversion resource was not found.",
        )
    if result.decision is ConversionPersistenceDecision.CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )
    return None


def _permission_denied(detail: str) -> JSONResponse:
    return permission_denied_problem(detail)


def _emit_conversion_operation_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=operation,
            outcome=outcome,
            source_authority="lotus-idea",
            error_code=error_code,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
        )
    )


def _operation_outcome_from_conversion_decision(
    decision: ConversionPersistenceDecision,
) -> OperationOutcome:
    if decision is ConversionPersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if decision is ConversionPersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if decision is ConversionPersistenceDecision.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    return OperationOutcome.CONFLICT


def _error_code_from_conversion_decision(
    decision: ConversionPersistenceDecision,
) -> str | None:
    if decision is ConversionPersistenceDecision.NOT_FOUND:
        return "conversion_resource_not_found"
    if decision is ConversionPersistenceDecision.CONFLICT:
        return "idempotency_conflict"
    return None


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
        **durable_repository_not_configured_metadata(),
    },
}


CONVERSION_OUTCOME_ROUTE: RouteMetadata = {
    "path": "/api/v1/conversion-intents/{conversionIntentId}/outcomes",
    "operation_id": "recordIdeaConversionOutcome",
    "summary": "Record an idea conversion outcome",
    "description": (
        "Records an internal downstream conversion outcome against a previously recorded "
        "idea conversion intent. The route verifies that the reporting source system "
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
                            "downstreamReference": "report-evidence-pack-001",
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
        **conflict_metadata(
            code="conversion_outcome_conflict",
            title="Conversion outcome conflict",
            detail="The conversion outcome is not valid for the recorded conversion intent.",
            description="Idempotency conflict or invalid conversion outcome source.",
        ),
        **durable_repository_not_configured_metadata(),
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
