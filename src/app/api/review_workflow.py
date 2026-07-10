from __future__ import annotations

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER
from app.api.durable_write_guard import durable_repository_write_unavailable_metadata
from app.api.problem_details import (
    conflict_metadata,
    invalid_request_metadata,
    merged_problem_response_metadata,
    not_found_metadata,
    permission_denied_metadata,
)
from app.api.review_workflow_models import (
    FeedbackEventResponse,
    FeedbackRequest,
    FeedbackResponse,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewActorScopeRequest,
    ReviewDecisionResponse,
    ReviewPersistenceSummaryResponse,
)
from app.api.review_workflow_operations import (
    ReviewWorkflowCallerHeaders,
    emit_review_workflow_operation_event as _emit_review_operation_event,
    error_code_from_review_decision,
    operation_outcome_from_review_decision as _operation_outcome_from_review_decision,
    permission_denied as _permission_denied,
    prepare_review_workflow_mutation,
    problem_for_review_persistence as _problem_for_review_persistence,
)
from app.api.route_metadata import RouteMetadata
from app.application.review_workflow import (
    apply_review_action_to_repository,
    record_feedback_to_repository,
)
from app.domain import (
    InvalidCandidateState,
    InvalidReviewAction,
    ReviewEntitlementDenied,
    ReviewPersistenceDecision,
)
from app.api.problem_details import problem_details_response as problem_response
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import PermissionDeniedError

_REVIEW_ACTION_CAPABILITY = "idea.review.record"
_FEEDBACK_CAPABILITY = "idea.feedback.record"

_REVIEW_ACTION_CONFLICT = conflict_metadata(
    code="review_action_conflict",
    title="Review action conflict",
    detail="The review action is not valid for the current idea candidate state.",
    description="The requested action is incompatible with the governed candidate state.",
)
_CANDIDATE_STATE_CONFLICT = conflict_metadata(
    code="candidate_state_conflict",
    title="Candidate state conflict",
    detail="The persisted candidate lifecycle and review posture are incompatible.",
    description="A contradictory persisted candidate was rejected by the state policy.",
)
_REVIEW_IDEMPOTENCY_CONFLICT = conflict_metadata(
    code="idempotency_conflict",
    title="Idempotency conflict",
    detail="The idempotency key was already used with a different request payload.",
    description="The idempotency key conflicts with an earlier review request.",
)

__all__ = [
    "FeedbackEventResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "ReviewActionRequest",
    "ReviewActionResponse",
    "ReviewActorScopeRequest",
    "ReviewDecisionResponse",
    "ReviewPersistenceSummaryResponse",
    "register_review_workflow_routes",
]


async def record_review_action(
    request: ReviewActionRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_caller_book_ids: str | None = Header(default=None, alias="X-Caller-Book-Ids"),
    x_caller_portfolio_ids: str | None = Header(default=None, alias="X-Caller-Portfolio-Ids"),
    x_caller_client_ids: str | None = Header(default=None, alias="X-Caller-Client-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ReviewActionResponse | JSONResponse:
    try:
        context = prepare_review_workflow_mutation(
            headers=ReviewWorkflowCallerHeaders(
                subject=x_caller_subject,
                roles=x_caller_roles,
                capabilities=x_caller_capabilities,
                tenant_ids=x_caller_tenant_ids,
                book_ids=x_caller_book_ids,
                portfolio_ids=x_caller_portfolio_ids,
                client_ids=x_caller_client_ids,
                trusted_caller_context=x_lotus_trusted_caller_context,
            ),
            authorized_scope=request.authorized_scope,
            capability=_REVIEW_ACTION_CAPABILITY,
            idempotency_key=idempotency_key,
            operation=IdeaOperation.REVIEW_ACTION,
        )
        if isinstance(context, JSONResponse):
            return context
        result = apply_review_action_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=context.caller,
                role=context.role,
                idempotency_key=idempotency_key,
            ),
            repository=context.repository,
        )
    except PermissionDeniedError:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to record idea reviews.")
    except ReviewEntitlementDenied:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to review this idea candidate.")
    except (InvalidCandidateState, InvalidReviewAction) as exc:
        error_code = exc.code
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.INVALID_STATE,
            error_code,
            attributes={
                "candidate_id": exc.candidate_id
                if isinstance(exc, InvalidCandidateState)
                else candidate_id,
                "lifecycle_status": exc.lifecycle_status.value,
                "policy_version": exc.policy_version,
                "requested_action": request.action.value,
                "review_posture": exc.review_posture.value,
            },
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code=error_code,
            title=(
                "Candidate state conflict"
                if isinstance(exc, InvalidCandidateState)
                else "Review action conflict"
            ),
            detail=(
                "The persisted candidate lifecycle and review posture are incompatible."
                if isinstance(exc, InvalidCandidateState)
                else "The review action is not valid for the current idea candidate state."
            ),
        )
    except ValueError:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the review request and retry.",
        )

    problem = _problem_for_review_persistence(result.persistence)
    if problem is not None:
        _emit_review_operation_event(
            IdeaOperation.REVIEW_ACTION,
            _operation_outcome_from_review_decision(result.persistence.decision),
            _error_code_from_review_decision(result.persistence.decision),
            context.durable_storage_backed,
        )
        return problem
    _emit_review_operation_event(
        IdeaOperation.REVIEW_ACTION,
        _operation_outcome_from_review_decision(result.persistence.decision),
        durable_storage_backed=context.durable_storage_backed,
    )
    return ReviewActionResponse(
        reviewDecision=(
            ReviewDecisionResponse.from_domain(result.review_result.decision)
            if result.review_result is not None
            else None
        ),
        persistence=ReviewPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=context.durable_storage_backed,
        supportedFeaturePromoted=False,
    )


async def record_feedback(
    request: FeedbackRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_caller_book_ids: str | None = Header(default=None, alias="X-Caller-Book-Ids"),
    x_caller_portfolio_ids: str | None = Header(default=None, alias="X-Caller-Portfolio-Ids"),
    x_caller_client_ids: str | None = Header(default=None, alias="X-Caller-Client-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> FeedbackResponse | JSONResponse:
    try:
        context = prepare_review_workflow_mutation(
            headers=ReviewWorkflowCallerHeaders(
                subject=x_caller_subject,
                roles=x_caller_roles,
                capabilities=x_caller_capabilities,
                tenant_ids=x_caller_tenant_ids,
                book_ids=x_caller_book_ids,
                portfolio_ids=x_caller_portfolio_ids,
                client_ids=x_caller_client_ids,
                trusted_caller_context=x_lotus_trusted_caller_context,
            ),
            authorized_scope=request.authorized_scope,
            capability=_FEEDBACK_CAPABILITY,
            idempotency_key=idempotency_key,
            operation=IdeaOperation.FEEDBACK_RECORD,
        )
        if isinstance(context, JSONResponse):
            return context
        result = record_feedback_to_repository(
            request.to_command(
                candidate_id=candidate_id,
                caller=context.caller,
                role=context.role,
                idempotency_key=idempotency_key,
            ),
            repository=context.repository,
        )
    except PermissionDeniedError:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied("The caller is not permitted to record idea feedback.")
    except ReviewEntitlementDenied:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return _permission_denied(
            "The caller is not permitted to record feedback for this idea candidate."
        )
    except ValueError:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the feedback request and retry.",
        )

    problem = _problem_for_review_persistence(result.persistence)
    if problem is not None:
        _emit_review_operation_event(
            IdeaOperation.FEEDBACK_RECORD,
            _operation_outcome_from_review_decision(result.persistence.decision),
            _error_code_from_review_decision(result.persistence.decision),
            context.durable_storage_backed,
        )
        return problem
    _emit_review_operation_event(
        IdeaOperation.FEEDBACK_RECORD,
        _operation_outcome_from_review_decision(result.persistence.decision),
        durable_storage_backed=context.durable_storage_backed,
    )
    return FeedbackResponse(
        feedbackEvent=(
            FeedbackEventResponse.from_domain(result.feedback_result.feedback_event)
            if result.feedback_result is not None
            else None
        ),
        persistence=ReviewPersistenceSummaryResponse.from_result(result.persistence),
        durableStorageBacked=context.durable_storage_backed,
        supportedFeaturePromoted=False,
    )


def _error_code_from_review_decision(
    decision: ReviewPersistenceDecision,
) -> str | None:
    return error_code_from_review_decision(decision)


REVIEW_ACTION_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/review-actions",
    "operation_id": "recordIdeaCandidateReviewAction",
    "summary": "Record an idea candidate review action",
    "description": (
        "Records an internal advisor review action for a persisted idea candidate through "
        "the RFC-0002 Slice 08 review workflow foundation. The route requires a mutating "
        "review capability, caller role, upstream-authorized scope, and Idempotency-Key. "
        "It does not approve suitability, compliance, mandate, execution, or client "
        "communication, and it does not promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ReviewActionResponse,
    "tags": ["Idea Review"],
    "responses": {
        200: {
            "description": "Review action accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "reviewDecision": {
                            "reviewId": "review-suppress-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "action": "suppress",
                            "resultingPosture": "suppressed",
                            "actorRole": "advisor",
                            "reasonCodes": ["review_suppressed", "review_required"],
                            "decidedAtUtc": "2026-06-21T10:05:00Z",
                            "suppressionReason": "manual_suppression",
                            "snoozedUntilUtc": None,
                            "grantsDownstreamAuthority": False,
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "suppressed",
                            "auditEventType": "idea.review.decision_recorded",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the review request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to record idea reviews.",
            description="Caller lacks review permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
            description="Candidate was not found.",
        ),
        **merged_problem_response_metadata(
            status_code=status.HTTP_409_CONFLICT,
            description="Review mutation conflict.",
            responses=(
                _REVIEW_ACTION_CONFLICT,
                _CANDIDATE_STATE_CONFLICT,
                _REVIEW_IDEMPOTENCY_CONFLICT,
            ),
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


FEEDBACK_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/feedback",
    "operation_id": "recordIdeaCandidateFeedback",
    "summary": "Record idea candidate feedback",
    "description": (
        "Records internal advisor feedback for a persisted idea candidate through the "
        "RFC-0002 Slice 08 feedback foundation. The route requires a mutating feedback "
        "capability, caller role, upstream-authorized scope, and Idempotency-Key. "
        "Feedback is source-provenanced and audited, but remains an internal foundation. "
        "Process-local writes are allowed only for local/test profiles; "
        "production-like profiles require LOTUS_IDEA_DATABASE_URL. Data-product certification, Gateway, "
        "and Workbench proof remain separate future promotion gates."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": FeedbackResponse,
    "tags": ["Idea Review"],
    "responses": {
        200: {
            "description": "Feedback accepted or replayed through the internal repository foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "feedbackEvent": {
                            "feedbackId": "feedback-useful-001",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "outcome": "useful",
                            "actorRole": "advisor",
                            "reasonCodes": ["feedback_recorded", "review_required"],
                            "recordedAtUtc": "2026-06-21T10:06:00Z",
                        },
                        "persistence": {
                            "decision": "accepted",
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "auditEventType": "idea.feedback.recorded",
                        },
                        "durableStorageBacked": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(detail="Correct the feedback request and retry."),
        **permission_denied_metadata(
            detail="The caller is not permitted to record idea feedback.",
            description="Caller lacks feedback permission.",
        ),
        **not_found_metadata(
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
            description="Candidate was not found.",
        ),
        **conflict_metadata(
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
            description="Idempotency conflict.",
        ),
        **durable_repository_write_unavailable_metadata(),
    },
}


def register_review_workflow_routes(app: FastAPI) -> None:
    app.post(
        path=REVIEW_ACTION_ROUTE["path"],
        operation_id=REVIEW_ACTION_ROUTE["operation_id"],
        summary=REVIEW_ACTION_ROUTE["summary"],
        description=REVIEW_ACTION_ROUTE["description"],
        status_code=REVIEW_ACTION_ROUTE["status_code"],
        response_model=REVIEW_ACTION_ROUTE["response_model"],
        tags=REVIEW_ACTION_ROUTE["tags"],
        responses=REVIEW_ACTION_ROUTE["responses"],
    )(record_review_action)
    app.post(
        path=FEEDBACK_ROUTE["path"],
        operation_id=FEEDBACK_ROUTE["operation_id"],
        summary=FEEDBACK_ROUTE["summary"],
        description=FEEDBACK_ROUTE["description"],
        status_code=FEEDBACK_ROUTE["status_code"],
        response_model=FEEDBACK_ROUTE["response_model"],
        tags=FEEDBACK_ROUTE["tags"],
        responses=FEEDBACK_ROUTE["responses"],
    )(record_feedback)
