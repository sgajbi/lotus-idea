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
        if not self.event_type.strip():
            raise ValueError("event_type is required")
        if not self.actor_subject.strip():
            raise ValueError("actor_subject is required")
        if not self.outcome.strip():
            raise ValueError("outcome is required")
        if self.occurred_at_utc.tzinfo is None or self.occurred_at_utc.utcoffset() is None:
            raise ValueError("occurred_at_utc must be timezone-aware")
        leaked = FORBIDDEN_ATTRIBUTE_KEYS.intersection(self.attributes)
        if leaked:
            raise ValueError(
                f"Audit event attributes contain sensitive keys: {', '.join(sorted(leaked))}"
            )
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))
