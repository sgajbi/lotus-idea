import pytest

from app.security.caller_context import (
    CallerContext,
    CapabilityPolicy,
    PermissionDeniedError,
    permission_denied_response,
    require_capability,
)


def test_capability_policy_allows_capability() -> None:
    caller = CallerContext.from_iterables(
        subject="operator",
        capabilities=("portfolio:read",),
    )
    policy = CapabilityPolicy.for_roles(required_capability="portfolio:read")
    require_capability(caller, policy)


def test_capability_policy_allows_role() -> None:
    caller = CallerContext.from_iterables(subject="operator", roles=("ops-admin",))
    policy = CapabilityPolicy.for_roles(
        required_capability="portfolio:write",
        allowed_roles=("ops-admin",),
    )
    require_capability(caller, policy)


def test_permission_denied_response_is_product_safe() -> None:
    with pytest.raises(PermissionDeniedError) as exc_info:
        require_capability(
            CallerContext.from_iterables(subject="operator"),
            CapabilityPolicy.for_roles(required_capability="portfolio:write"),
        )

    response = permission_denied_response(exc_info.value)
    body = bytes(response.body).decode("utf-8").lower()
    assert response.status_code == 403
    assert "permission_denied" in body
    assert "raw entitlement" not in body
    assert "client" not in body
    assert "portfolio" not in body
    assert "portfolio:write" not in body
