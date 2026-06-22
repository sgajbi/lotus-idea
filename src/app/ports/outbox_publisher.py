from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain import OutboxEventRecord


@dataclass(frozen=True)
class OutboxPublishOutcome:
    accepted: bool
    failure_reason: str | None = None

    @classmethod
    def accepted_by_publisher(cls) -> OutboxPublishOutcome:
        return cls(accepted=True)

    @classmethod
    def rejected_by_publisher(cls, failure_reason: str) -> OutboxPublishOutcome:
        return cls(accepted=False, failure_reason=failure_reason)


class OutboxEventPublisher(Protocol):
    def publish(self, event: OutboxEventRecord) -> OutboxPublishOutcome: ...
