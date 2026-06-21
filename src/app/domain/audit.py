from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Mapping

FORBIDDEN_ATTRIBUTE_KEYS = frozenset(
    {
        "client_id",
        "client_name",
        "portfolio_id",
        "account_id",
        "holding_id",
        "request_body",
        "response_body",
    }
)


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor_subject: str
    outcome: str
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(UTC))
    attributes: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        leaked = FORBIDDEN_ATTRIBUTE_KEYS.intersection(self.attributes)
        if leaked:
            raise ValueError(
                f"Audit event attributes contain sensitive keys: {', '.join(sorted(leaked))}"
            )
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
