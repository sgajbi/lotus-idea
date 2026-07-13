from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Header, Query

from app.api.caller_headers import TRUSTED_CALLER_CONTEXT_HEADER
from app.application.review_queue import (
    DEFAULT_REVIEW_QUEUE_PAGE_LIMIT,
    MAX_REVIEW_QUEUE_PAGE_LIMIT,
)


@dataclass(frozen=True)
class ReviewQueueScopeRequest:
    evaluated_at_utc: datetime | None
    tenant_id: str | None
    book_id: str | None
    portfolio_id: str | None
    client_id: str | None
    caller_subject: str | None
    caller_roles: str | None
    caller_capabilities: str | None
    caller_tenant_ids: str | None
    caller_book_ids: str | None
    caller_portfolio_ids: str | None
    caller_client_ids: str | None
    trusted_caller_context: str | None


@dataclass(frozen=True)
class ReviewQueueRequest(ReviewQueueScopeRequest):
    limit: int
    offset: int
    snapshot_token: str | None


def review_queue_scope_request_from_http(
    evaluated_at_utc: datetime | None = Query(default=None, alias="evaluatedAtUtc"),
    tenant_id: str | None = Query(default=None, alias="tenantId"),
    book_id: str | None = Query(default=None, alias="bookId"),
    portfolio_id: str | None = Query(default=None, alias="portfolioId"),
    client_id: str | None = Query(default=None, alias="clientId"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
    x_caller_tenant_ids: str | None = Header(default=None, alias="X-Caller-Tenant-Ids"),
    x_caller_book_ids: str | None = Header(default=None, alias="X-Caller-Book-Ids"),
    x_caller_portfolio_ids: str | None = Header(default=None, alias="X-Caller-Portfolio-Ids"),
    x_caller_client_ids: str | None = Header(default=None, alias="X-Caller-Client-Ids"),
    x_lotus_trusted_caller_context: str | None = Header(
        default=None,
        alias=TRUSTED_CALLER_CONTEXT_HEADER,
    ),
) -> ReviewQueueScopeRequest:
    return ReviewQueueScopeRequest(
        evaluated_at_utc=evaluated_at_utc,
        tenant_id=tenant_id,
        book_id=book_id,
        portfolio_id=portfolio_id,
        client_id=client_id,
        caller_subject=x_caller_subject,
        caller_roles=x_caller_roles,
        caller_capabilities=x_caller_capabilities,
        caller_tenant_ids=x_caller_tenant_ids,
        caller_book_ids=x_caller_book_ids,
        caller_portfolio_ids=x_caller_portfolio_ids,
        caller_client_ids=x_caller_client_ids,
        trusted_caller_context=x_lotus_trusted_caller_context,
    )


def review_queue_request_from_http(
    request: Annotated[ReviewQueueScopeRequest, Depends(review_queue_scope_request_from_http)],
    limit: int = Query(
        default=DEFAULT_REVIEW_QUEUE_PAGE_LIMIT,
        ge=1,
        le=MAX_REVIEW_QUEUE_PAGE_LIMIT,
    ),
    offset: int = Query(default=0, ge=0),
    snapshot_token: str | None = Query(default=None, alias="snapshotToken", max_length=69),
) -> ReviewQueueRequest:
    return ReviewQueueRequest(
        **asdict(request),
        limit=limit,
        offset=offset,
        snapshot_token=snapshot_token,
    )


__all__ = [
    "ReviewQueueRequest",
    "ReviewQueueScopeRequest",
    "review_queue_request_from_http",
    "review_queue_scope_request_from_http",
]
