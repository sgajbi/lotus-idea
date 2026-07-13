from __future__ import annotations

from app.domain import QueueAccessScopeFilter


def effective_queue_scope_filter(
    *,
    requested_scope_filter: QueueAccessScopeFilter,
    caller_scope_filter: QueueAccessScopeFilter | None,
) -> QueueAccessScopeFilter | None:
    if caller_scope_filter is None:
        return requested_scope_filter
    if not requested_scope_filter.is_subset_of(caller_scope_filter):
        return None
    return QueueAccessScopeFilter(
        tenant_id=requested_scope_filter.tenant_id or caller_scope_filter.tenant_id,
        book_id=requested_scope_filter.book_id or caller_scope_filter.book_id,
        portfolio_id=requested_scope_filter.portfolio_id or caller_scope_filter.portfolio_id,
        client_id=requested_scope_filter.client_id or caller_scope_filter.client_id,
    )


__all__ = ["effective_queue_scope_filter"]
