"""Shared caller and telemetry plumbing for owner-history reconciliation routes.

The Advise and Manage reconciliation endpoints are deliberately parallel
consumers of different owner contracts; what they genuinely share - the
reconcile capability, the complete-entitlement requirement, and the
operation-event emission - lives here once.
"""

from __future__ import annotations

from fastapi import Request

from app.api.operation_events import emit_api_foundation_operation_event
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import CallerContext, PermissionDeniedError

RECONCILE_CAPABILITY = "idea.downstream-realization.reconcile"


def require_reconciliation_caller(caller: CallerContext) -> None:
    if not caller.has_capability(RECONCILE_CAPABILITY):
        raise PermissionDeniedError(RECONCILE_CAPABILITY)
    scope = caller.entitlement_scope
    if not (scope.tenant_ids and scope.book_ids and scope.portfolio_ids and scope.client_ids):
        raise PermissionDeniedError("idea.downstream-realization.entitlement_scope")


def request_context_id(request: Request, attribute: str) -> str | None:
    value = getattr(request.state, attribute, None)
    return str(value) if value else None


def emit_reconciliation_event(outcome: OperationOutcome, error_code: str | None) -> None:
    emit_api_foundation_operation_event(
        IdeaOperation.DOWNSTREAM_RECONCILIATION_RESOLVE,
        outcome,
        error_code,
    )
