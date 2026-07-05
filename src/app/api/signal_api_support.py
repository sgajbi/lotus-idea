from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import status
from fastapi.responses import JSONResponse

from app.api.route_metadata import RouteMetadata as RouteMetadata
from app.domain.access_scope import QueueAccessScopeFilter, ReviewAccessScope
from app.domain import SignalEvaluationResult, SourceSystem
from app.api.problem_details import (
    invalid_request_metadata,
    permission_denied_metadata,
    problem_details_response as problem_response,
)
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import (
    CallerContext,
    CapabilityPolicy,
    PermissionDeniedError,
    require_role_and_capability,
)


class _SourceRefLike(Protocol):
    product_id: str
    source_system: Any


class _RuntimeWithClose(Protocol):
    def close(self) -> None:
        """Release route-owned runtime resources."""


@dataclass(frozen=True)
class SignalSourceRefContract:
    source_ref: _SourceRefLike | None
    expected_source_system: SourceSystem
    expected_product_ids: tuple[str, ...]


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


def source_authority_from_contracts(contracts: Iterable[SignalSourceRefContract]) -> str:
    contract_tuple = tuple(contracts)
    source_systems = {
        str(contract.expected_source_system.value)
        for contract in contract_tuple
        if contract.source_ref is not None
    }
    if not source_systems:
        source_systems = {str(contract.expected_source_system.value) for contract in contract_tuple}
    if len(source_systems) == 1:
        return next(iter(source_systems))
    return "source-owned"


def signal_source_ref_contract_problem_or_none(
    *,
    contracts: Iterable[SignalSourceRefContract],
    source_authority: str,
    emit_event: Callable[..., None],
) -> JSONResponse | None:
    for contract in contracts:
        source_ref = contract.source_ref
        if source_ref is None:
            continue
        if (
            source_ref.source_system != contract.expected_source_system
            or source_ref.product_id not in contract.expected_product_ids
        ):
            emit_event(
                IdeaOperation.SIGNAL_EVALUATION,
                OperationOutcome.INVALID_REQUEST,
                source_authority=source_authority,
                error_code="source_ref_contract_mismatch",
            )
            return problem_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="invalid_request",
                title="Invalid request",
                detail=(
                    "Source refs must match the certified source contract for this signal family."
                ),
            )
    return None


def signal_problem_responses() -> dict[int | str, dict[str, Any]]:
    return {
        **invalid_request_metadata(
            detail="Request validation failed. Correct the request fields and retry.",
        ),
        **permission_denied_metadata(
            detail="The caller is not permitted to evaluate idea signals.",
            description="Caller lacks the required signal-evaluation role or capability.",
        ),
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
        require_role_and_capability(caller, SIGNAL_EVALUATION_POLICY)
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


def close_signal_source_runtime(
    *,
    runtime: _RuntimeWithClose,
    source_authority: str,
    emit_event: Callable[..., None],
) -> None:
    try:
        runtime.close()
    except Exception:
        emit_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.SUPPRESSED,
            source_authority=source_authority,
            error_code="runtime_cleanup_failed",
        )
