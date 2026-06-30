from __future__ import annotations

import os
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.api.runtime_dependencies import load_runtime_settings
from app.domain.access_scope import QueueAccessScopeFilter
from app.security.caller_context import CallerContext, CallerEntitlementScope

TRUSTED_CALLER_CONTEXT_TOKEN_ENV = "LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN"
TRUSTED_CALLER_CONTEXT_HEADER = "X-Lotus-Trusted-Caller-Context"


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
    trusted_caller_context: str | None = None,
) -> CallerContext:
    _require_trusted_caller_context_provenance(
        subject=subject,
        roles=roles,
        capabilities=capabilities,
        tenant_ids=tenant_ids,
        book_ids=book_ids,
        portfolio_ids=portfolio_ids,
        client_ids=client_ids,
        trusted_caller_context=trusted_caller_context,
    )
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


def caller_context_from_standard_headers(
    x_caller_subject: Annotated[str | None, Header(alias="X-Caller-Subject")] = None,
    x_caller_roles: Annotated[str | None, Header(alias="X-Caller-Roles")] = None,
    x_caller_capabilities: Annotated[str | None, Header(alias="X-Caller-Capabilities")] = None,
    x_caller_tenant_ids: Annotated[str | None, Header(alias="X-Caller-Tenant-Ids")] = None,
    x_caller_book_ids: Annotated[str | None, Header(alias="X-Caller-Book-Ids")] = None,
    x_caller_portfolio_ids: Annotated[str | None, Header(alias="X-Caller-Portfolio-Ids")] = None,
    x_caller_client_ids: Annotated[str | None, Header(alias="X-Caller-Client-Ids")] = None,
    x_lotus_trusted_caller_context: Annotated[
        str | None, Header(alias=TRUSTED_CALLER_CONTEXT_HEADER)
    ] = None,
) -> CallerContext:
    try:
        return caller_context_from_headers(
            subject=x_caller_subject,
            roles=x_caller_roles,
            capabilities=x_caller_capabilities,
            tenant_ids=x_caller_tenant_ids,
            book_ids=x_caller_book_ids,
            portfolio_ids=x_caller_portfolio_ids,
            client_ids=x_caller_client_ids,
            trusted_caller_context=x_lotus_trusted_caller_context,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="caller entitlement scope headers cannot contain blank values",
        ) from exc


CallerContextHeaders = Annotated[CallerContext, Depends(caller_context_from_standard_headers)]


def _require_trusted_caller_context_provenance(
    *,
    subject: str | None,
    roles: str | None,
    capabilities: str | None,
    tenant_ids: str | None,
    book_ids: str | None,
    portfolio_ids: str | None,
    client_ids: str | None,
    trusted_caller_context: str | None,
) -> None:
    settings = load_runtime_settings()
    if settings.process_local_repository_allowed:
        return
    if not _caller_authorization_headers_present(
        subject=subject,
        roles=roles,
        capabilities=capabilities,
        tenant_ids=tenant_ids,
        book_ids=book_ids,
        portfolio_ids=portfolio_ids,
        client_ids=client_ids,
    ):
        return
    expected_token = os.getenv(TRUSTED_CALLER_CONTEXT_TOKEN_ENV, "").strip()
    supplied_token = (trusted_caller_context or "").strip()
    if expected_token and supplied_token and secrets.compare_digest(supplied_token, expected_token):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="trusted caller context provenance is required",
    )


def _caller_authorization_headers_present(
    *,
    subject: str | None,
    roles: str | None,
    capabilities: str | None,
    tenant_ids: str | None,
    book_ids: str | None,
    portfolio_ids: str | None,
    client_ids: str | None,
) -> bool:
    return any(
        bool(value and value.strip())
        for value in (
            subject,
            roles,
            capabilities,
            tenant_ids,
            book_ids,
            portfolio_ids,
            client_ids,
        )
    )


def caller_access_scope_filter(caller: CallerContext) -> QueueAccessScopeFilter | None:
    scope = caller.entitlement_scope
    if scope.is_empty:
        return None
    return QueueAccessScopeFilter(
        tenant_id=scope.tenant_ids,
        book_id=scope.book_ids,
        portfolio_id=scope.portfolio_ids,
        client_id=scope.client_ids,
    )
