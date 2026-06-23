from __future__ import annotations

from app.security.caller_context import CallerContext, CallerEntitlementScope


def _split_header_values(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    values = tuple(item.strip() for item in value.split(","))
    if any(not item for item in values):
        raise ValueError("caller entitlement scope headers cannot contain blank values")
    return tuple(dict.fromkeys(values))


def caller_context_from_headers(
    *,
    subject: str | None,
    roles: str | None,
    capabilities: str | None,
    tenant_ids: str | None = None,
    book_ids: str | None = None,
    portfolio_ids: str | None = None,
    client_ids: str | None = None,
) -> CallerContext:
    return CallerContext.from_iterables(
        subject=subject or "anonymous",
        roles=(role.strip() for role in (roles or "").split(",")),
        capabilities=(capability.strip() for capability in (capabilities or "").split(",")),
        entitlement_scope=CallerEntitlementScope.from_iterables(
            tenant_ids=_split_header_values(tenant_ids),
            book_ids=_split_header_values(book_ids),
            portfolio_ids=_split_header_values(portfolio_ids),
            client_ids=_split_header_values(client_ids),
        ),
    )
