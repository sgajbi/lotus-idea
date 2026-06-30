from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.caller_headers import caller_context_from_headers
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    permission_denied_metadata,
    permission_denied_problem,
    not_found_metadata,
)
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.application.candidate_lifecycle import (
    ApplyCandidateLifecycleTransitionCommand,
    apply_candidate_lifecycle_transition_to_repository,
)
from app.domain import (
    IdeaLifecycleStatus,
    InvalidLifecycleTransition,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    ReasonCode,
)
from app.errors import problem_response
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.security.caller_context import CallerContext, PermissionDeniedError


class RouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]


_LIFECYCLE_TRANSITION_CAPABILITY = "idea.candidate.lifecycle.transition"


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CandidateLifecycleTransitionRequest(CamelModel):
    transition_id: str = Field(..., alias="transitionId")
    target_lifecycle_status: IdeaLifecycleStatus = Field(..., alias="targetLifecycleStatus")
    changed_at_utc: datetime = Field(..., alias="changedAtUtc")
    reason_codes: tuple[ReasonCode, ...] = Field(..., alias="reasonCodes")

    @field_validator("transition_id")
    @classmethod
    def _transition_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("transitionId is required")
        return value

    @field_validator("reason_codes")
    @classmethod
    def _reason_codes_must_not_be_empty(
        cls, value: tuple[ReasonCode, ...]
    ) -> tuple[ReasonCode, ...]:
        if not value:
            raise ValueError("reasonCodes is required")
        return tuple(value)

    @field_validator("changed_at_utc")
    @classmethod
    def _changed_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("changedAtUtc must be timezone-aware")
        return value

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        idempotency_key: str,
    ) -> ApplyCandidateLifecycleTransitionCommand:
        return ApplyCandidateLifecycleTransitionCommand(
            candidate_id=candidate_id,
            transition_id=self.transition_id,
            target_status=self.target_lifecycle_status,
            changed_at_utc=self.changed_at_utc,
            reason_codes=tuple(reason.value for reason in self.reason_codes),
            actor_subject=caller.subject,
            idempotency_key=idempotency_key,
        )


class CandidateLifecycleTransitionSummaryResponse(CamelModel):
    transition_id: str = Field(..., alias="transitionId")
    candidate_id: str = Field(..., alias="candidateId")
    lifecycle_status: IdeaLifecycleStatus = Field(..., alias="lifecycleStatus")
    changed_at_utc: datetime = Field(..., alias="changedAtUtc")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")


class LifecyclePersistenceSummaryResponse(CamelModel):
    decision: LifecyclePersistenceDecision
    candidate_id: str | None = Field(default=None, alias="candidateId")
    lifecycle_status: str | None = Field(default=None, alias="lifecycleStatus")
    audit_event_type: str | None = Field(default=None, alias="auditEventType")

    @classmethod
    def from_result(
        cls,
        result: LifecyclePersistenceResult,
    ) -> "LifecyclePersistenceSummaryResponse":
        record = result.record
        audit_event = result.audit_event or (
            record.audit_events[-1] if record is not None and record.audit_events else None
        )
        return cls(
            decision=result.decision,
            candidateId=record.candidate.candidate_id if record is not None else None,
            lifecycleStatus=record.candidate.lifecycle_status.value if record is not None else None,
            auditEventType=audit_event.event_type if audit_event is not None else None,
        )


class CandidateLifecycleTransitionResponse(CamelModel):
    transition: CandidateLifecycleTransitionSummaryResponse | None = None
    persistence: LifecyclePersistenceSummaryResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")


async def record_candidate_lifecycle_transition(
    request: CandidateLifecycleTransitionRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> CandidateLifecycleTransitionResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_lifecycle_caller(caller)
        _validate_idempotency_key(idempotency_key)
        repository = get_idea_repository()
        durable_storage_backed = idea_repository_durable_storage_backed(repository)
        result = apply_candidate_lifecycle_transition_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=caller,
                idempotency_key=idempotency_key,
            ),
            repository=repository,
        )
    except PermissionDeniedError:
        _emit_lifecycle_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to transition idea candidates.")
    except InvalidLifecycleTransition:
        _emit_lifecycle_operation_event(
            OperationOutcome.INVALID_STATE,
            "lifecycle_transition_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="lifecycle_transition_conflict",
            title="Lifecycle transition conflict",
            detail="The lifecycle transition is not valid for the current idea candidate state.",
        )
    except ValueError:
        _emit_lifecycle_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the lifecycle transition request and retry.",
        )

    problem = _problem_for_lifecycle_persistence(result)
    if problem is not None:
        _emit_lifecycle_operation_event(
            _operation_outcome_from_lifecycle_decision(result.decision),
            _error_code_from_lifecycle_decision(result.decision),
            durable_storage_backed,
        )
        return problem
    _emit_lifecycle_operation_event(
        _operation_outcome_from_lifecycle_decision(result.decision),
        durable_storage_backed=durable_storage_backed,
    )
    return CandidateLifecycleTransitionResponse(
        transition=(
            CandidateLifecycleTransitionSummaryResponse(
                transitionId=request.transition_id,
                candidateId=candidate_id,
                lifecycleStatus=request.target_lifecycle_status,
                changedAtUtc=request.changed_at_utc,
                reasonCodes=tuple(reason.value for reason in request.reason_codes),
                grantsDownstreamAuthority=False,
            )
            if result.decision is LifecyclePersistenceDecision.ACCEPTED
            else None
        ),
        persistence=LifecyclePersistenceSummaryResponse.from_result(result),
        durableStorageBacked=durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _require_lifecycle_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_LIFECYCLE_TRANSITION_CAPABILITY):
        raise PermissionDeniedError(_LIFECYCLE_TRANSITION_CAPABILITY)


def _validate_idempotency_key(idempotency_key: str) -> None:
    if not idempotency_key.strip():
        raise ValueError("idempotency key is required")


def _problem_for_lifecycle_persistence(
    result: LifecyclePersistenceResult,
) -> JSONResponse | None:
    if result.decision is LifecyclePersistenceDecision.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )
    if result.decision is LifecyclePersistenceDecision.CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )
    return None


def _permission_denied(detail: str) -> JSONResponse:
    return permission_denied_problem(detail)


def _emit_lifecycle_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.LIFECYCLE_TRANSITION,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


def _operation_outcome_from_lifecycle_decision(
    decision: LifecyclePersistenceDecision,
) -> OperationOutcome:
    if decision is LifecyclePersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if decision is LifecyclePersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if decision is LifecyclePersistenceDecision.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    return OperationOutcome.CONFLICT


def _error_code_from_lifecycle_decision(
    decision: LifecyclePersistenceDecision,
) -> str | None:
    if decision is LifecyclePersistenceDecision.NOT_FOUND:
        return "candidate_not_found"
    if decision is LifecyclePersistenceDecision.CONFLICT:
        return "idempotency_conflict"
    return None


CANDIDATE_LIFECYCLE_TRANSITION_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions",
    "operation_id": "recordIdeaCandidateLifecycleTransition",
    "summary": "Record an idea candidate lifecycle transition",
    "description": (
        "Records an internal governed lifecycle transition for a persisted idea candidate "
        "through the RFC-0002 Slice 06 lifecycle and audit foundation. The route requires "
        "a lifecycle transition capability and Idempotency-Key, applies the canonical "
        "domain lifecycle transition graph, writes lifecycle history plus audit evidence, "
        "and does not grant downstream proposal, manage-review, report, suitability, "
        "execution, or client-communication authority."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": CandidateLifecycleTransitionResponse,
    "tags": ["Idea Lifecycle"],
    "responses": {
        200: {
            "description": "Lifecycle transition accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "transition": {
                            "transitionId": "lifecycle-ready-for-review-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "ready_for_review",
                            "changedAtUtc": "2026-06-21T10:04:00Z",
                            "reasonCodes": ["review_required"],
                            "grantsDownstreamAuthority": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "ready_for_review",
                            "auditEventType": "idea.lifecycle.transitioned",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the lifecycle transition request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to transition idea candidates.",
            description="Caller lacks lifecycle permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="lifecycle_transition_conflict",
            title="Lifecycle transition conflict",
            detail="The lifecycle transition is not valid for the current idea candidate state.",
            description="Idempotency conflict or invalid lifecycle transition.",
        ),
    },
}


def register_candidate_lifecycle_routes(app: FastAPI) -> None:
    app.post(
        path=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["path"],
        operation_id=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["operation_id"],
        summary=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["summary"],
        description=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["description"],
        status_code=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["status_code"],
        response_model=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["response_model"],
        tags=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["tags"],
        responses=CANDIDATE_LIFECYCLE_TRANSITION_ROUTE["responses"],
    )(record_candidate_lifecycle_transition)
