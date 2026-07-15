from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .receipts import require_aware


@dataclass(frozen=True)
class RuntimeEvidenceScope:
    tenant_id: str
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id.strip() or not self.portfolio_id.strip():
            raise ValueError("tenant_id and portfolio_id are required")
        require_aware(self.evaluated_at_utc, "evaluated_at_utc")
        if self.correlation_id is not None and not self.correlation_id.strip():
            raise ValueError("correlation_id must not be blank")
