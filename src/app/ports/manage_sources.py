from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from app.domain import SourceRef


class ManageSourceUnavailable(Exception):
    def __init__(self, *, code: str = "manage_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class ManageSourceEntitlementDenied(Exception):
    pass


@dataclass(frozen=True)
class ManageMandateHealthEvidenceRequest:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip():
            raise ValueError("portfolio_id is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class ManageMandateHealthEvidence:
    workflow_decision_count: int | None
    lineage_edge_count: int | None
    supportability_state: str | None
    supportability_reason: str | None
    freshness_bucket: str | None
    portfolio_scope_confirmed: bool
    action_register_ref: SourceRef | None
    manage_diagnostic: str | None = None
    entitlement_allowed: bool = True


class ManageOpportunitySourcePort(Protocol):
    def fetch_mandate_health_evidence(
        self, request: ManageMandateHealthEvidenceRequest
    ) -> ManageMandateHealthEvidence:
        """Fetch source-owned Lotus Manage action-register posture for idea evaluation."""
