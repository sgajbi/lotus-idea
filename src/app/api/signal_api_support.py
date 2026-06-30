from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol

from fastapi import status
from fastapi.responses import JSONResponse

from app.api.route_metadata import RouteMetadata as RouteMetadata
from app.domain.access_scope import QueueAccessScopeFilter, ReviewAccessScope
from app.domain import SignalEvaluationResult
from app.api.problem_details import ProblemDetails, problem_details_response as problem_response
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import (
    CallerContext,
    CapabilityPolicy,
    PermissionDeniedError,
    require_capability,
)


class _SourceRefLike(Protocol):
    source_system: Any


SignalRouteMetadata = RouteMetadata


SIGNAL_EVALUATION_POLICY = CapabilityPolicy.for_roles(
    required_capability="idea.signal.evaluate",
    allowed_roles=("advisor",),
)


def source_authority_from_refs(source_refs: Iterable[_SourceRefLike | None]) -> str:
    source_systems = {
        str(source_ref.source_system.value) for source_ref in source_refs if source_ref is not None
    }
    if len(source_systems) == 1:
        return next(iter(source_systems))
    return "source-owned"


def signal_problem_responses() -> dict[int | str, dict[str, Any]]:
    return {
        status.HTTP_400_BAD_REQUEST: {
            "model": ProblemDetails,
            "description": "Request validation failed.",
            "content": {
                "application/json": {
                    "example": {
                        "type": "about:blank",
                        "status": status.HTTP_400_BAD_REQUEST,
                        "code": "invalid_request",
                        "title": "Invalid request",
                        "detail": "Request validation failed. Correct the request fields and retry.",
                    }
                }
            },
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ProblemDetails,
            "description": "Caller lacks the required signal-evaluation capability.",
            "content": {
                "application/json": {
                    "example": {
                        "type": "about:blank",
                        "status": status.HTTP_403_FORBIDDEN,
                        "code": "permission_denied",
                        "title": "Permission denied",
                        "detail": "The caller is not permitted to evaluate idea signals.",
                    }
                }
            },
        },
    }


def operation_outcome_from_signal_evaluation(
    result: SignalEvaluationResult,
) -> OperationOutcome:
    outcome = result.outcome.value
    if outcome == "candidate_created":
        return OperationOutcome.ACCEPTED
    if outcome == "suppressed":
        return OperationOutcome.SUPPRESSED
    if outcome == "not_eligible":
        return OperationOutcome.NOT_ELIGIBLE
    return OperationOutcome.BLOCKED


def signal_permission_problem_or_none(
    *,
    caller: CallerContext,
    source_authority: str,
    emit_event: Callable[..., None],
    requested_access_scope: ReviewAccessScope | None = None,
) -> JSONResponse | None:
    try:
        require_capability(caller, SIGNAL_EVALUATION_POLICY)
    except PermissionDeniedError:
        emit_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.PERMISSION_DENIED,
            source_authority=source_authority,
            error_code="permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to evaluate idea signals.",
        )
    if not _caller_scope_allows_requested_scope(caller, requested_access_scope):
        emit_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.PERMISSION_DENIED,
            source_authority=source_authority,
            error_code="permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to evaluate idea signals for the requested scope.",
        )
    return None


def _caller_scope_allows_requested_scope(
    caller: CallerContext,
    requested_access_scope: ReviewAccessScope | None,
) -> bool:
    if requested_access_scope is None:
        return True
    caller_scope = caller.entitlement_scope
    if caller_scope.is_empty:
        return False
    requested_scope_filter = QueueAccessScopeFilter(
        tenant_id=requested_access_scope.tenant_id,
        book_id=requested_access_scope.book_id,
        portfolio_id=requested_access_scope.portfolio_id,
        client_id=requested_access_scope.client_id,
    )
    caller_scope_filter = QueueAccessScopeFilter(
        tenant_id=caller_scope.tenant_ids,
        book_id=caller_scope.book_ids,
        portfolio_id=caller_scope.portfolio_ids,
        client_id=caller_scope.client_ids,
    )
    return requested_scope_filter.is_subset_of(caller_scope_filter)


def emit_signal_evaluation_event(
    *,
    result: SignalEvaluationResult,
    source_authority: str,
    emit_event: Callable[..., None],
) -> None:
    emit_event(
        IdeaOperation.SIGNAL_EVALUATION,
        operation_outcome_from_signal_evaluation(result),
        source_authority=source_authority,
    )
