from __future__ import annotations

from dataclasses import dataclass

from fastapi import status
from fastapi.responses import JSONResponse

from app.api.caller_headers import caller_access_scope_filter, caller_context_from_headers
from app.api.durable_write_guard import (
    DURABLE_REPOSITORY_NOT_CONFIGURED,
    durable_write_problem,
)
from app.api.idempotency import validate_idempotency_key
from app.api.problem_details import permission_denied_problem
from app.api.problem_details import problem_details_response as problem_response
from app.api.runtime_dependencies import (
    get_idea_repository,
    idea_repository_durable_storage_backed,
)
from app.api.operation_events import (
    emit_api_foundation_operation_event as emit_conversion_operation_event,
)
from app.domain import ConversionPersistenceDecision, ConversionPersistenceResult
from app.domain.access_scope import QueueAccessScopeFilter
from app.observability import IdeaOperation, OperationOutcome
from app.ports.idea_repository import ConversionWorkflowRepository
from app.security.caller_context import CallerContext, PermissionDeniedError

__all__ = [
    "ConversionCallerHeaders",
    "ConversionMutationContext",
    "emit_conversion_operation_event",
    "error_code_from_conversion_decision",
    "operation_outcome_from_conversion_decision",
    "permission_denied",
    "prepare_conversion_mutation",
    "problem_for_conversion_persistence",
    "require_complete_conversion_entitlement_scope",
]


@dataclass(frozen=True)
class ConversionCallerHeaders:
    subject: str | None
    roles: str | None
    capabilities: str | None
    tenant_ids: str | None
    book_ids: str | None
    portfolio_ids: str | None
    client_ids: str | None
    trusted_caller_context: str | None


@dataclass(frozen=True)
class ConversionMutationContext:
    caller: CallerContext
    repository: ConversionWorkflowRepository
    durable_storage_backed: bool
    access_scope_filter: QueueAccessScopeFilter | None = None


def prepare_conversion_mutation(
    *,
    headers: ConversionCallerHeaders,
    capability: str,
    idempotency_key: str,
    operation: IdeaOperation,
    require_complete_entitlement_scope: bool = False,
) -> ConversionMutationContext | JSONResponse:
    caller = caller_context_from_headers(
        subject=headers.subject,
        roles=headers.roles,
        capabilities=headers.capabilities,
        tenant_ids=headers.tenant_ids,
        book_ids=headers.book_ids,
        portfolio_ids=headers.portfolio_ids,
        client_ids=headers.client_ids,
        trusted_caller_context=headers.trusted_caller_context,
    )
    require_conversion_caller(caller, capability=capability)
    if require_complete_entitlement_scope:
        require_complete_conversion_entitlement_scope(caller)
    validate_idempotency_key(idempotency_key)
    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        emit_conversion_operation_event(
            operation,
            OperationOutcome.BLOCKED,
            DURABLE_REPOSITORY_NOT_CONFIGURED,
            durable_storage_backed,
        )
        return configuration_problem
    return ConversionMutationContext(
        caller=caller,
        repository=repository,
        durable_storage_backed=durable_storage_backed,
        access_scope_filter=caller_access_scope_filter(caller),
    )


def require_conversion_caller(caller: CallerContext, *, capability: str) -> None:
    if not caller.has_capability(capability):
        raise PermissionDeniedError(capability)


def require_complete_conversion_entitlement_scope(caller: CallerContext) -> None:
    scope = caller.entitlement_scope
    if not (scope.tenant_ids and scope.book_ids and scope.portfolio_ids and scope.client_ids):
        raise PermissionDeniedError("idea.conversion.entitlement_scope")


def problem_for_conversion_persistence(
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
    if result.decision is ConversionPersistenceDecision.OUTCOME_CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="conversion_outcome_conflict",
            title="Conversion outcome conflict",
            detail="The conversion outcome conflicts with the governed source-event history.",
        )
    return None


def permission_denied(detail: str) -> JSONResponse:
    return permission_denied_problem(detail)


def operation_outcome_from_conversion_decision(
    decision: ConversionPersistenceDecision,
) -> OperationOutcome:
    if decision is ConversionPersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if decision is ConversionPersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if decision is ConversionPersistenceDecision.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    return OperationOutcome.CONFLICT


def error_code_from_conversion_decision(
    decision: ConversionPersistenceDecision,
) -> str | None:
    if decision is ConversionPersistenceDecision.NOT_FOUND:
        return "conversion_resource_not_found"
    if decision is ConversionPersistenceDecision.CONFLICT:
        return "idempotency_conflict"
    if decision is ConversionPersistenceDecision.OUTCOME_CONFLICT:
        return "conversion_outcome_conflict"
    return None
