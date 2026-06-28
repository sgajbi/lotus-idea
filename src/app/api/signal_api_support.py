from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import Enum
from typing import Any, Protocol, TypedDict

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain import SignalEvaluationResult
from app.errors import problem_response
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import (
    CallerContext,
    CapabilityPolicy,
    PermissionDeniedError,
    require_capability,
)


class _SourceRefLike(Protocol):
    source_system: Any


class SignalRouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]


RouteMetadata = SignalRouteMetadata


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
    return None


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
