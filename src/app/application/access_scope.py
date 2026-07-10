from __future__ import annotations

from app.domain.access_scope import ReviewAccessScope

UNKNOWN_SCOPE_VALUE = "unknown"


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
