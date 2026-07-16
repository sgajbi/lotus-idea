from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from app.domain import SourceRef

ADVISE_POLICY_EVALUATION_PRODUCT_ID = "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
ADVISE_POLICY_EVALUATION_PRODUCT_VERSION = "v1"
ADVISE_POLICY_EVALUATION_WORKFLOW_ROUTE_TEMPLATE = (
    "/advisory/policy-evaluations/{evaluation_id}/workflow"
)


class AdviseSourceUnavailable(Exception):
    def __init__(self, *, code: str = "advise_source_unavailable") -> None:
        self.code = code
        super().__init__(code)


class AdviseSourceEntitlementDenied(Exception):
    pass


@dataclass(frozen=True)
class AdvisePolicyEvaluationEvidenceRequest:
    evaluation_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    correlation_id: str | None = None
    trace_id: str | None = None

    def __post_init__(self) -> None:
        if not self.evaluation_id.strip():
            raise ValueError("evaluation_id is required")
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")


@dataclass(frozen=True)
class AdvisePolicyEvaluationRuntimeEvidence:
    product_id: str
    product_version: str
    route: str
    evaluation_id: str | None
    tenant_scope_hash: str | None
    portfolio_id: str | None
    correlation_id: str | None
    trace_id: str | None
    as_of_date: date | None
    generated_at_utc: datetime | None
    content_hash: str | None
    source_evidence_hash: str | None
    policy_content_hash: str | None
    policy_pack_id: str | None
    policy_version: str | None
    evaluation_status: str | None
    open_requirement_count: int
    blocked_requirement_count: int
    sign_off_status: str | None
    sign_off_blocker_count: int
    client_ready_publication: str | None
    data_quality_status: str
    freshness: str


@dataclass(frozen=True)
class AdvisePolicyEvaluationEvidence:
    evaluation_status: str | None
    open_requirement_count: int | None
    blocked_requirement_count: int | None
    sign_off_status: str | None
    sign_off_blocker_count: int | None
    client_ready_publication: str | None
    policy_ref: SourceRef | None
    workflow_runtime: AdvisePolicyEvaluationRuntimeEvidence | None = None
    advise_diagnostic: str | None = None
    entitlement_allowed: bool = True


class AdvisePolicyEvaluationSourcePort(Protocol):
    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        """Fetch source-owned Lotus Advise policy evaluation posture for idea evaluation."""


class AdviseOpportunitySourcePort(AdvisePolicyEvaluationSourcePort, Protocol):
    """Backward-compatible alias for Advise opportunity source adapters."""
