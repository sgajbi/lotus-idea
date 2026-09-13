"""Shared caller and telemetry plumbing for owner-history reconciliation routes.

The Advise and Manage reconciliation endpoints are deliberately parallel
consumers of different owner contracts; what they genuinely share - the
reconcile capability, the complete-entitlement requirement, and the
operation-event emission - lives here once.
"""

from __future__ import annotations

from app.api.caller_headers import require_complete_caller_access_scope_filter
from app.api.operation_events import emit_api_foundation_operation_event
from app.api.operation_events import request_context_id as request_context_id
from app.domain.access_scope import QueueAccessScopeFilter
from app.observability import IdeaOperation, OperationOutcome
from app.security.caller_context import CallerContext, PermissionDeniedError

RECONCILE_CAPABILITY = "idea.downstream-realization.reconcile"
RECONCILE_ENTITLEMENT_SCOPE_PERMISSION = "idea.downstream-realization.entitlement_scope"


def require_reconciliation_caller(caller: CallerContext) -> QueueAccessScopeFilter:
    """Return the complete trusted caller scope for reconciliation or fail closed."""

    if not caller.has_capability(RECONCILE_CAPABILITY):
        raise PermissionDeniedError(RECONCILE_CAPABILITY)
    return require_complete_caller_access_scope_filter(
        caller,
        denied_permission=RECONCILE_ENTITLEMENT_SCOPE_PERMISSION,
    )


def emit_reconciliation_event(outcome: OperationOutcome, error_code: str | None) -> None:
    emit_api_foundation_operation_event(
        IdeaOperation.DOWNSTREAM_RECONCILIATION_RESOLVE,
        outcome,
        error_code,
    )
