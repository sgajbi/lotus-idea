from __future__ import annotations

from app.security.caller_context import CallerContext


def caller_context_from_headers(
    *,
    subject: str | None,
    roles: str | None,
    capabilities: str | None,
) -> CallerContext:
    return CallerContext.from_iterables(
        subject=subject or "anonymous",
        roles=(role.strip() for role in (roles or "").split(",")),
        capabilities=(capability.strip() for capability in (capabilities or "").split(",")),
    )
