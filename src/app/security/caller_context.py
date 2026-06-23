from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from fastapi import status
from fastapi.responses import JSONResponse

from app.errors import problem_response


@dataclass(frozen=True)
class CallerEntitlementScope:
    tenant_ids: tuple[str, ...] = ()
    book_ids: tuple[str, ...] = ()
    portfolio_ids: tuple[str, ...] = ()
    client_ids: tuple[str, ...] = ()

    @classmethod
    def from_iterables(
        cls,
        *,
        tenant_ids: Iterable[str] = (),
        book_ids: Iterable[str] = (),
        portfolio_ids: Iterable[str] = (),
        client_ids: Iterable[str] = (),
    ) -> "CallerEntitlementScope":
        return cls(
            tenant_ids=_clean_unique_values(tenant_ids),
            book_ids=_clean_unique_values(book_ids),
            portfolio_ids=_clean_unique_values(portfolio_ids),
            client_ids=_clean_unique_values(client_ids),
        )

    @property
    def is_empty(self) -> bool:
        return not (self.tenant_ids or self.book_ids or self.portfolio_ids or self.client_ids)


@dataclass(frozen=True)
class CallerContext:
    subject: str
    roles: frozenset[str] = field(default_factory=frozenset)
    capabilities: frozenset[str] = field(default_factory=frozenset)
    entitlement_scope: CallerEntitlementScope = field(default_factory=CallerEntitlementScope)

    @classmethod
    def from_iterables(
        cls,
        *,
        subject: str,
        roles: Iterable[str] = (),
        capabilities: Iterable[str] = (),
        entitlement_scope: CallerEntitlementScope | None = None,
    ) -> "CallerContext":
        return cls(
            subject=subject,
            roles=frozenset(role.strip() for role in roles if role.strip()),
            capabilities=frozenset(
                capability.strip() for capability in capabilities if capability.strip()
            ),
            entitlement_scope=entitlement_scope or CallerEntitlementScope(),
        )

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_capability(self, capability: str) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True)
class CapabilityPolicy:
    required_capability: str
    allowed_roles: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def for_roles(
        cls,
        *,
        required_capability: str,
        allowed_roles: Iterable[str] = (),
    ) -> "CapabilityPolicy":
        return cls(
            required_capability=required_capability,
            allowed_roles=frozenset(role.strip() for role in allowed_roles if role.strip()),
        )

    def allows(self, caller: CallerContext) -> bool:
        if caller.has_capability(self.required_capability):
            return True
        return any(caller.has_role(role) for role in self.allowed_roles)


class PermissionDeniedError(Exception):
    def __init__(self, required_capability: str) -> None:
        self.required_capability = required_capability
        super().__init__("Permission denied")


def require_capability(caller: CallerContext, policy: CapabilityPolicy) -> None:
    if not policy.allows(caller):
        raise PermissionDeniedError(policy.required_capability)


def require_role_and_capability(caller: CallerContext, policy: CapabilityPolicy) -> None:
    has_allowed_role = not policy.allowed_roles or any(
        caller.has_role(role) for role in policy.allowed_roles
    )
    if not has_allowed_role or not caller.has_capability(policy.required_capability):
        raise PermissionDeniedError(policy.required_capability)


def permission_denied_response(_: PermissionDeniedError) -> JSONResponse:
    return problem_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail="The caller is not permitted to perform this action.",
    )


def _clean_unique_values(values: Iterable[str]) -> tuple[str, ...]:
    cleaned = tuple(value.strip() for value in values)
    if any(not value for value in cleaned):
        raise ValueError("caller entitlement scope values cannot be blank")
    return tuple(dict.fromkeys(cleaned))
