import pytest
from fastapi import HTTPException

from app.api.caller_headers import (
    caller_access_scope_filter,
    caller_context_from_headers,
    caller_context_from_standard_headers,
)
from app.security.caller_context import (
    CallerContext,
    CallerEntitlementScope,
    CapabilityPolicy,
    PermissionDeniedError,
    permission_denied_response,
    require_capability,
    require_role_and_capability,
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


def test_role_and_capability_requirement_requires_both() -> None:
    policy = CapabilityPolicy.for_roles(
        required_capability="portfolio:operate",
        allowed_roles=("operator",),
    )
    require_role_and_capability(
        CallerContext.from_iterables(
            subject="operator",
            roles=("operator",),
            capabilities=("portfolio:operate",),
        ),
        policy,
    )

    with pytest.raises(PermissionDeniedError):
        require_role_and_capability(
            CallerContext.from_iterables(
                subject="capability-only",
                capabilities=("portfolio:operate",),
            ),
            policy,
        )
    with pytest.raises(PermissionDeniedError):
        require_role_and_capability(
            CallerContext.from_iterables(subject="role-only", roles=("operator",)),
            policy,
        )


def test_caller_context_carries_deduplicated_entitlement_scope() -> None:
    caller = CallerContext.from_iterables(
        subject="advisor-001",
        roles=("advisor",),
        capabilities=("idea.review.queue.read",),
        entitlement_scope=CallerEntitlementScope.from_iterables(
            tenant_ids=("tenant-private-bank-sg", "tenant-private-bank-sg"),
            book_ids=("book-advisor-001",),
            portfolio_ids=("PB_SG_GLOBAL_BAL_001", "PB_SG_ALT_BAL_002"),
            client_ids=("client-001",),
        ),
    )

    assert caller.entitlement_scope.tenant_ids == ("tenant-private-bank-sg",)
    assert caller.entitlement_scope.book_ids == ("book-advisor-001",)
    assert caller.entitlement_scope.portfolio_ids == (
        "PB_SG_GLOBAL_BAL_001",
        "PB_SG_ALT_BAL_002",
    )
    assert caller.entitlement_scope.client_ids == ("client-001",)


def test_caller_entitlement_scope_rejects_blank_values() -> None:
    with pytest.raises(ValueError, match="caller entitlement scope values cannot be blank"):
        CallerEntitlementScope.from_iterables(portfolio_ids=("PB_SG_GLOBAL_BAL_001", " "))


def test_caller_context_from_headers_parses_entitlement_scope_headers() -> None:
    caller = caller_context_from_headers(
        subject="advisor-001",
        roles="advisor",
        capabilities="idea.review.queue.read",
        tenant_ids="tenant-private-bank-sg",
        book_ids="book-advisor-001",
        portfolio_ids="PB_SG_GLOBAL_BAL_001,PB_SG_ALT_BAL_002",
        client_ids="client-001",
    )

    assert caller.entitlement_scope.tenant_ids == ("tenant-private-bank-sg",)
    assert caller.entitlement_scope.book_ids == ("book-advisor-001",)
    assert caller.entitlement_scope.portfolio_ids == (
        "PB_SG_GLOBAL_BAL_001",
        "PB_SG_ALT_BAL_002",
    )
    assert caller.entitlement_scope.client_ids == ("client-001",)


def test_caller_context_from_standard_headers_parses_common_api_headers() -> None:
    caller = caller_context_from_standard_headers(
        x_caller_subject="advisor-001",
        x_caller_roles="advisor",
        x_caller_capabilities="idea.signal.evaluate",
        x_caller_tenant_ids="tenant-private-bank-sg",
        x_caller_book_ids="book-advisor-001",
        x_caller_portfolio_ids="PB_SG_GLOBAL_BAL_001,PB_SG_ALT_BAL_002",
        x_caller_client_ids="client-001",
    )

    assert caller.subject == "advisor-001"
    assert caller.roles == frozenset({"advisor"})
    assert caller.capabilities == frozenset({"idea.signal.evaluate"})
    assert caller.entitlement_scope.tenant_ids == ("tenant-private-bank-sg",)
    assert caller.entitlement_scope.book_ids == ("book-advisor-001",)
    assert caller.entitlement_scope.portfolio_ids == (
        "PB_SG_GLOBAL_BAL_001",
        "PB_SG_ALT_BAL_002",
    )
    assert caller.entitlement_scope.client_ids == ("client-001",)


def test_caller_context_from_standard_headers_rejects_blank_entitlement_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        caller_context_from_standard_headers(
            x_caller_subject="advisor-001",
            x_caller_roles="advisor",
            x_caller_capabilities="idea.signal.evaluate",
            x_caller_portfolio_ids="PB_SG_GLOBAL_BAL_001, ",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "caller entitlement scope headers cannot contain blank values"


def test_caller_access_scope_filter_matches_entitlement_headers() -> None:
    caller = caller_context_from_headers(
        subject="advisor-001",
        roles="advisor",
        capabilities="idea.candidate.detail.read",
        tenant_ids="tenant-private-bank-sg",
        book_ids="book-advisor-001",
        portfolio_ids="PB_SG_GLOBAL_BAL_001,PB_SG_ALT_BAL_002",
        client_ids="client-001",
    )

    scope_filter = caller_access_scope_filter(caller)

    assert scope_filter is not None
    assert scope_filter.tenant_id == ("tenant-private-bank-sg",)
    assert scope_filter.book_id == ("book-advisor-001",)
    assert scope_filter.portfolio_id == ("PB_SG_GLOBAL_BAL_001", "PB_SG_ALT_BAL_002")
    assert scope_filter.client_id == ("client-001",)


def test_caller_access_scope_filter_is_none_without_entitlement_scope() -> None:
    caller = CallerContext.from_iterables(subject="advisor-001", roles=("advisor",))

    assert caller_access_scope_filter(caller) is None


def test_caller_context_from_headers_rejects_blank_entitlement_scope_header_values() -> None:
    with pytest.raises(
        ValueError,
        match="caller entitlement scope headers cannot contain blank values",
    ):
        caller_context_from_headers(
            subject="advisor-001",
            roles="advisor",
            capabilities="idea.review.queue.read",
            portfolio_ids="PB_SG_GLOBAL_BAL_001, ",
        )


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
