from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceProfile:
    name: str
    description: str


DEFAULT_SERVICE_PROFILE = ServiceProfile(
    name="domain-service",
    description="Domain-authoritative backend service. Keep business rules in domain/application modules and expose explicit source-owned APIs.",
)
