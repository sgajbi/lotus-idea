from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import status
from fastapi.responses import JSONResponse

from app.api.caller_headers import caller_context_from_headers
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
from app.domain import (
    ReviewActorContext,
    ReviewActorRole,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
)
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event
from app.ports.idea_repository import ReviewWorkflowRepository
from app.security.caller_context import CallerContext, CallerEntitlementScope, PermissionDeniedError


class AuthorizedReviewScope(Protocol):
    def is_subset_of_entitlement_scope(self, scope: CallerEntitlementScope) -> bool: ...


@dataclass(frozen=True)
class ReviewWorkflowCallerHeaders:
    subject: str | None
    roles: str | None
    capabilities: str | None
    tenant_ids: str | None
    book_ids: str | None
    portfolio_ids: str | None
    client_ids: str | None
    trusted_caller_context: str | None


@dataclass(frozen=True)
class ReviewWorkflowMutationContext:
    caller: CallerContext
    role: ReviewActorRole
    repository: ReviewWorkflowRepository
    durable_storage_backed: bool


def prepare_review_workflow_mutation(
    *,
    headers: ReviewWorkflowCallerHeaders,
    authorized_scope: AuthorizedReviewScope,
    capability: str,
    idempotency_key: str,
    operation: IdeaOperation,
) -> ReviewWorkflowMutationContext | JSONResponse:
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
    role = require_mutating_review_workflow_caller(caller, capability=capability)
    require_body_scope_claim_within_caller_entitlements(
        caller=caller,
        authorized_scope=authorized_scope,
    )
    validate_idempotency_key(idempotency_key)
    repository = get_idea_repository()
    durable_storage_backed = idea_repository_durable_storage_backed(repository)
    configuration_problem = durable_write_problem(repository)
    if configuration_problem is not None:
        emit_review_workflow_operation_event(
            operation,
            OperationOutcome.BLOCKED,
            DURABLE_REPOSITORY_NOT_CONFIGURED,
            durable_storage_backed,
        )
        return configuration_problem
    return ReviewWorkflowMutationContext(
        caller=caller,
        role=role,
        repository=repository,
        durable_storage_backed=durable_storage_backed,
    )


def require_mutating_review_workflow_caller(
    caller: CallerContext,
    *,
    capability: str,
) -> ReviewActorRole:
    if not caller.has_capability(capability):
        raise PermissionDeniedError(capability)
    matching_roles = [role for role in ReviewActorRole if caller.has_role(role.value)]
    if len(matching_roles) != 1:
        raise PermissionDeniedError("idea.review.actor_role")
    return matching_roles[0]


def build_review_actor_context(
    *,
    caller: CallerContext,
    role: ReviewActorRole,
) -> ReviewActorContext:
    scope = caller.entitlement_scope
    if scope.is_empty:
        raise PermissionDeniedError("idea.review.entitlement_scope")
    return ReviewActorContext(
        actor_subject=caller.subject,
        role=role,
        tenant_ids=frozenset(scope.tenant_ids),
        book_ids=frozenset(scope.book_ids),
        portfolio_ids=frozenset(scope.portfolio_ids),
        client_ids=frozenset(scope.client_ids),
    )


def require_body_scope_claim_within_caller_entitlements(
    *,
    caller: CallerContext,
    authorized_scope: AuthorizedReviewScope,
) -> None:
    if not authorized_scope.is_subset_of_entitlement_scope(caller.entitlement_scope):
        raise PermissionDeniedError("idea.review.entitlement_scope")


def problem_for_review_persistence(
    result: ReviewPersistenceResult,
) -> JSONResponse | None:
    if result.decision is ReviewPersistenceDecision.NOT_FOUND:
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )
    if result.decision is ReviewPersistenceDecision.CONFLICT:
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="idempotency_conflict",
            title="Idempotency conflict",
            detail="The idempotency key was already used with a different request payload.",
        )
    return None


def permission_denied(detail: str) -> JSONResponse:
    return permission_denied_problem(detail)


def emit_review_workflow_operation_event(
    operation: IdeaOperation,
    outcome: OperationOutcome,
    error_code: str | None = None,
    durable_storage_backed: bool = False,
) -> None:
    emit_foundation_operation_event(
        operation,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
        durable_storage_backed=durable_storage_backed,
    )


def operation_outcome_from_review_decision(
    decision: ReviewPersistenceDecision,
) -> OperationOutcome:
    if decision is ReviewPersistenceDecision.ACCEPTED:
        return OperationOutcome.ACCEPTED
    if decision is ReviewPersistenceDecision.REPLAYED:
        return OperationOutcome.REPLAYED
    if decision is ReviewPersistenceDecision.NOT_FOUND:
        return OperationOutcome.NOT_FOUND
    return OperationOutcome.CONFLICT


def error_code_from_review_decision(
    decision: ReviewPersistenceDecision,
) -> str | None:
    if decision is ReviewPersistenceDecision.NOT_FOUND:
        return "candidate_not_found"
    if decision is ReviewPersistenceDecision.CONFLICT:
        return "idempotency_conflict"
    return None
