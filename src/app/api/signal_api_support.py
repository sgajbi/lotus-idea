from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeVar, cast

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


class _SourceRuntimeBlocker(Protocol):
    code: str


@dataclass(frozen=True)
class SignalSourceRefContract:
    source_ref: _SourceRefLike | None
    expected_source_system: SourceSystem
    expected_product_ids: tuple[str, ...]


CommandT = TypeVar("CommandT")
ResponseT = TypeVar("ResponseT")
RuntimeT = TypeVar("RuntimeT", bound=_RuntimeWithClose)

TENANT_SCOPE_PROVENANCE_ATTRIBUTE = "tenant_scope_provenance"
TRUSTED_SINGLE_TENANT_PROVENANCE = "trusted_single_tenant"
MISSING_OR_AMBIGUOUS_TENANT_PROVENANCE = "missing_or_ambiguous"


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
                source_authority=_contract_mismatch_source_authority(
                    contract,
                    fallback=source_authority,
                ),
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


def _contract_mismatch_source_authority(
    contract: SignalSourceRefContract,
    *,
    fallback: str,
) -> str:
    expected_source_system = contract.expected_source_system
    return str(expected_source_system.value) if expected_source_system is not None else fallback


def signal_source_ref_one_of_contract_problem_or_none(
    *,
    contracts: Iterable[SignalSourceRefContract],
    source_authority: str,
    emit_event: Callable[..., None],
) -> JSONResponse | None:
    contract_tuple = tuple(contracts)
    if not contract_tuple:
        return None
    source_ref = contract_tuple[0].source_ref
    if source_ref is None:
        return None
    if any(
        source_ref.source_system == contract.expected_source_system
        and source_ref.product_id in contract.expected_product_ids
        for contract in contract_tuple
    ):
        return None
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
        detail="Source refs must match the certified source contract for this signal family.",
    )


def evaluate_caller_supplied_signal(
    *,
    caller: CallerContext,
    source_authority: str,
    source_contracts: Iterable[SignalSourceRefContract],
    requested_access_scope: ReviewAccessScope | None,
    command_factory: Callable[[], CommandT],
    evaluator: Callable[[CommandT], SignalEvaluationResult],
    response_factory: Callable[..., ResponseT],
    emit_event: Callable[..., None],
    contract_mode: Literal["all", "one_of"] = "all",
) -> ResponseT | JSONResponse:
    """Run the shared caller-supplied signal boundary in one ordered path.

    The route owns transport details and DTO mapping; this helper owns the
    repeated boundary sequence before an application evaluator is called.
    Source runtime construction remains supplied by each route because source
    adapters have different configuration and port types.
    """
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=requested_access_scope,
        emit_event=emit_event,
    )
    if permission_problem is not None:
        return permission_problem

    contract_problem = (
        signal_source_ref_one_of_contract_problem_or_none(
            contracts=source_contracts,
            source_authority=source_authority,
            emit_event=emit_event,
        )
        if contract_mode == "one_of"
        else signal_source_ref_contract_problem_or_none(
            contracts=source_contracts,
            source_authority=source_authority,
            emit_event=emit_event,
        )
    )
    if contract_problem is not None:
        return contract_problem

    result = evaluator(command_factory())
    emit_signal_evaluation_event(
        result=result,
        source_authority=source_authority,
        emit_event=emit_event,
    )
    return response_factory(result, source_authority=source_authority)


def evaluate_source_signal(
    *,
    caller: CallerContext,
    source_authority: str,
    requested_access_scope: ReviewAccessScope | None,
    runtime_factory: Callable[[], object],
    is_runtime_blocked: Callable[[object], bool],
    blocked_detail: str,
    command_factory: Callable[[RuntimeT, str | None], CommandT],
    evaluator: Callable[[CommandT, RuntimeT], SignalEvaluationResult],
    response_factory: Callable[..., ResponseT],
    emit_event: Callable[..., None],
    require_tenant_context: bool = False,
) -> ResponseT | JSONResponse:
    """Run the shared source-backed signal boundary in a fixed order.

    Routes retain transport DTO mapping and source-specific runtime factories.
    This helper centralizes the security, blocked-runtime, evaluation, event,
    projection, and cleanup sequence so new source adapters cannot drift from
    the governed API boundary.
    """
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=requested_access_scope,
        emit_event=emit_event,
    )
    if permission_problem is not None:
        return permission_problem

    tenant_id: str | None = None
    event_attributes: dict[str, str] | None = None
    if require_tenant_context:
        tenant_id, tenant_problem = required_tenant_context_or_problem(
            caller=caller,
            source_authority=source_authority,
            emit_event=emit_event,
        )
        if tenant_problem is not None:
            return tenant_problem
        event_attributes = {
            TENANT_SCOPE_PROVENANCE_ATTRIBUTE: TRUSTED_SINGLE_TENANT_PROVENANCE,
        }

    runtime_or_blocker = runtime_factory()
    if is_runtime_blocked(runtime_or_blocker):
        blocker = cast(_SourceRuntimeBlocker, runtime_or_blocker)
        event_fields: dict[str, object] = {
            "source_authority": source_authority,
            "error_code": blocker.code,
        }
        if event_attributes is not None:
            event_fields["attributes"] = event_attributes
        emit_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.BLOCKED,
            **event_fields,
        )
        return problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail=blocked_detail,
        )

    runtime = cast(RuntimeT, runtime_or_blocker)
    try:
        result = evaluator(command_factory(runtime, tenant_id), runtime)
        emit_signal_evaluation_event(
            result=result,
            source_authority=source_authority,
            emit_event=emit_event,
            attributes=event_attributes,
        )
        return response_factory(result, source_authority=source_authority)
    finally:
        close_signal_source_runtime(
            runtime=runtime,
            source_authority=source_authority,
            emit_event=emit_event,
        )


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


def required_tenant_context_or_problem(
    *,
    caller: CallerContext,
    source_authority: str,
    emit_event: Callable[..., None],
) -> tuple[str | None, JSONResponse | None]:
    tenant_ids = caller.entitlement_scope.tenant_ids
    if len(tenant_ids) == 1:
        return tenant_ids[0], None
    emit_event(
        IdeaOperation.SIGNAL_EVALUATION,
        OperationOutcome.PERMISSION_DENIED,
        source_authority=source_authority,
        error_code="tenant_context_required",
        attributes={
            TENANT_SCOPE_PROVENANCE_ATTRIBUTE: MISSING_OR_AMBIGUOUS_TENANT_PROVENANCE,
        },
    )
    return None, problem_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail="A single trusted tenant context is required for this source evaluation.",
    )


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
        tenant_id=_known_scope_value(requested_access_scope.tenant_id),
        book_id=_known_scope_value(requested_access_scope.book_id),
        portfolio_id=_known_scope_value(requested_access_scope.portfolio_id),
        client_id=_known_scope_value(requested_access_scope.client_id),
    )
    caller_scope_filter = QueueAccessScopeFilter(
        tenant_id=caller_scope.tenant_ids,
        book_id=caller_scope.book_ids,
        portfolio_id=caller_scope.portfolio_ids,
        client_id=caller_scope.client_ids,
    )
    return requested_scope_filter.is_subset_of(caller_scope_filter)


def _known_scope_value(value: str) -> str | None:
    return None if value == "unknown" else value


def emit_signal_evaluation_event(
    *,
    result: SignalEvaluationResult,
    source_authority: str,
    emit_event: Callable[..., None],
    attributes: dict[str, str] | None = None,
) -> None:
    event_fields: dict[str, object] = {"source_authority": source_authority}
    if attributes is not None:
        event_fields["attributes"] = attributes
    emit_event(
        IdeaOperation.SIGNAL_EVALUATION,
        operation_outcome_from_signal_evaluation(result),
        **event_fields,
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
