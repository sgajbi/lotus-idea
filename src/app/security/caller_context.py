from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from fastapi import status
from fastapi.responses import JSONResponse

from app.errors import problem_response


@dataclass(frozen=True)
class CallerContext:
    subject: str
    roles: frozenset[str] = field(default_factory=frozenset)
    capabilities: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_iterables(
        cls,
        *,
        subject: str,
        roles: Iterable[str] = (),
        capabilities: Iterable[str] = (),
    ) -> "CallerContext":
        return cls(
            subject=subject,
            roles=frozenset(role.strip() for role in roles if role.strip()),
            capabilities=frozenset(
                capability.strip() for capability in capabilities if capability.strip()
            ),
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


def permission_denied_response(_: PermissionDeniedError) -> JSONResponse:
    return problem_response(
        status_code=status.HTTP_403_FORBIDDEN,
        code="permission_denied",
        title="Permission denied",
        detail="The caller is not permitted to perform this action.",
    )
