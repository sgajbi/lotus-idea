from __future__ import annotations

from app.domain.access_scope import ReviewAccessScope, UNKNOWN_SCOPE_VALUE as UNKNOWN_SCOPE_VALUE
from app.domain.persistence import UnscopedCandidatePersistenceError


def require_authoritative_scope(scope: ReviewAccessScope | None) -> None:
    """Reject placeholder authority before a durable workflow performs source I/O."""
    if scope is None or not scope.is_authoritative:
        raise UnscopedCandidatePersistenceError(
            "candidate access scope must be authoritative for persistence"
        )


def portfolio_only_scope(portfolio_id: str) -> ReviewAccessScope:
    return tenant_portfolio_scope(
        tenant_id=UNKNOWN_SCOPE_VALUE,
        portfolio_id=portfolio_id,
    )


def tenant_portfolio_scope(*, tenant_id: str, portfolio_id: str) -> ReviewAccessScope:
    if not tenant_id.strip():
        raise ValueError("tenant_id is required")
    if not portfolio_id.strip():
        raise ValueError("portfolio_id is required")
    return ReviewAccessScope(
        tenant_id=tenant_id,
        book_id=UNKNOWN_SCOPE_VALUE,
        portfolio_id=portfolio_id,
        client_id=UNKNOWN_SCOPE_VALUE,
    )
