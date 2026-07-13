from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse

from app.api.caller_headers import (
    INVALID_CALLER_SCOPE_DETAIL,
    caller_access_scope_filter,
    caller_context_from_headers,
)
from app.api.problem_details import (
    invalid_request_metadata,
    permission_denied_metadata,
    problem_details_response,
)
from app.api.review_queue.access import effective_queue_scope_filter
from app.api.review_queue.constants import ACTIVE_REVIEW_QUEUE_EVALUATED_AT_UTC
from app.api.review_queue.exception_models import ReviewQueueExceptionResponse
from app.api.review_queue.requests import (
    ReviewQueueScopeRequest,
    review_queue_scope_request_from_http,
)
from app.api.route_metadata import RouteMetadata
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.temporal_validation import is_timezone_aware
from app.application.review_queue_exceptions import build_review_queue_exception_snapshot
from app.domain import QueueAccessScopeFilter
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_operation_event,
)
from app.security.caller_context import (
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)


_READ_OPERATOR_EXCEPTIONS_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.review.queue.exceptions.read",
    allowed_roles=("operator",),
)


async def get_review_queue_exceptions(
    request: Annotated[ReviewQueueScopeRequest, Depends(review_queue_scope_request_from_http)],
) -> ReviewQueueExceptionResponse | JSONResponse:
    try:
        caller = caller_context_from_headers(
            subject=request.caller_subject,
            roles=request.caller_roles,
            capabilities=request.caller_capabilities,
            tenant_ids=request.caller_tenant_ids,
            book_ids=request.caller_book_ids,
            portfolio_ids=request.caller_portfolio_ids,
            client_ids=request.caller_client_ids,
            trusted_caller_context=request.trusted_caller_context,
        )
    except ValueError:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            outcome=OperationOutcome.INVALID_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail=INVALID_CALLER_SCOPE_DETAIL,
        )
    try:
        require_role_and_capability(caller, _READ_OPERATOR_EXCEPTIONS_POLICY)
    except PermissionDeniedError:
        return _problem(
            status_code=status.HTTP_403_FORBIDDEN,
            outcome=OperationOutcome.PERMISSION_DENIED,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea review queue exceptions.",
        )

    evaluated_at_utc = request.evaluated_at_utc or ACTIVE_REVIEW_QUEUE_EVALUATED_AT_UTC
    if not is_timezone_aware(evaluated_at_utc):
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            outcome=OperationOutcome.INVALID_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="evaluatedAtUtc must be timezone-aware.",
        )
    try:
        requested_scope_filter = QueueAccessScopeFilter(
            tenant_id=request.tenant_id,
            book_id=request.book_id,
            portfolio_id=request.portfolio_id,
            client_id=request.client_id,
        )
    except ValueError:
        return _problem(
            status_code=status.HTTP_400_BAD_REQUEST,
            outcome=OperationOutcome.INVALID_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Scope query fields cannot be blank.",
        )
    effective_scope_filter = effective_queue_scope_filter(
        requested_scope_filter=requested_scope_filter,
        caller_scope_filter=caller_access_scope_filter(caller),
    )
    if effective_scope_filter is None:
        return _problem(
            status_code=status.HTTP_403_FORBIDDEN,
            outcome=OperationOutcome.PERMISSION_DENIED,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read the requested review queue exception scope.",
        )

    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    snapshot = build_review_queue_exception_snapshot(
        evaluated_at_utc=evaluated_at_utc,
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        access_scope_filter=(None if effective_scope_filter.is_empty else effective_scope_filter),
    )
    _emit_event(OperationOutcome.ACCEPTED, durable_storage_backed=durable_storage_backed)
    return ReviewQueueExceptionResponse.from_domain(snapshot)


def _problem(
    *,
    status_code: int,
    outcome: OperationOutcome,
    code: str,
    title: str,
    detail: str,
) -> JSONResponse:
    _emit_event(outcome, error_code=code)
    return problem_details_response(
        status_code=status_code,
        code=code,
        title=title,
        detail=detail,
    )


def _emit_event(
    outcome: OperationOutcome,
    *,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.REVIEW_QUEUE_EXCEPTION_READ,
            outcome=outcome,
            source_authority="lotus-idea",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=durable_storage_backed,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE: RouteMetadata = {
    "path": "/api/v1/review-queues/operator/exceptions",
    "operation_id": "getIdeaReviewQueueExceptions",
    "summary": "Get review queue support exceptions",
    "description": (
        "Returns a bounded, source-safe operator projection of review queue support exceptions "
        "grouped by advisor, portfolio-manager, and compliance audience. Exception counts cover "
        "invalid lifecycle/posture state, unsupported evidence, missing score, unrankable score "
        "policy, and non-reviewable state. The projection does not expose candidate identifiers, "
        "rank business work, or grant review, compliance, suitability, mandate, or execution "
        "authority. Tenant, book, portfolio, and client scope is intersected with trusted caller "
        "entitlements. This internal operational foundation is not a supported product feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": ReviewQueueExceptionResponse,
    "tags": ["Operations"],
    "responses": {
        200: {
            "description": "Review queue exception posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "policyVersion": "idea-deterministic-ranking-v1",
                        "evaluatedAtUtc": "2026-06-21T10:10:00Z",
                        "audiences": [
                            {
                                "audience": "advisor",
                                "candidateSnapshotCount": 2,
                                "exceptionCount": 1,
                                "exceptionCounts": {
                                    "invalid_state": 0,
                                    "unsupported_evidence": 1,
                                    "unscored": 0,
                                    "unrankable_score_policy": 0,
                                    "non_reviewable_status": 0,
                                },
                            }
                        ],
                        "totalExceptionCount": 1,
                        "durableStorageBacked": True,
                        "supportabilityStatus": "not_certified",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **invalid_request_metadata(
            detail="Correct the review queue exception request and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to read review queue exceptions.",
            description="Caller lacks the operator exception permission or entitlement scope.",
        ),
    },
}


def register_review_queue_exception_route(app: FastAPI) -> None:
    app.get(
        path=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["path"],
        operation_id=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["operation_id"],
        summary=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["summary"],
        description=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["description"],
        status_code=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["status_code"],
        response_model=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["response_model"],
        tags=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["tags"],
        responses=OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE["responses"],
    )(get_review_queue_exceptions)


__all__ = [
    "OPERATOR_REVIEW_QUEUE_EXCEPTIONS_ROUTE",
    "get_review_queue_exceptions",
    "register_review_queue_exception_route",
]
