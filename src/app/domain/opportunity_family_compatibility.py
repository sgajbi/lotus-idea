from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.ideas import OpportunityFamily, ReasonCode, SourceSystem


class OpportunityArchetype(StrEnum):
    HIGH_VOLATILITY_DRAWDOWN_REVIEW = "high_volatility_drawdown_review"


class OpportunityEvidenceLane(StrEnum):
    LOTUS_RISK_VOLATILITY = "lotus_risk_volatility"
    LOTUS_RISK_DRAWDOWN_REVIEW = "lotus_risk_drawdown_review"


@dataclass(frozen=True)
class OpportunityFamilyCompatibility:
    family: OpportunityFamily
    archetype: OpportunityArchetype
    evidence_lane: OpportunityEvidenceLane
    source_system: SourceSystem
    source_product_id: str
    source_route: str
    reason_code: ReasonCode


HIGH_VOLATILITY_FAMILY_COMPATIBILITY = OpportunityFamilyCompatibility(
    family=OpportunityFamily.HIGH_VOLATILITY,
    archetype=OpportunityArchetype.HIGH_VOLATILITY_DRAWDOWN_REVIEW,
    evidence_lane=OpportunityEvidenceLane.LOTUS_RISK_VOLATILITY,
    source_system=SourceSystem.LOTUS_RISK,
    source_product_id="lotus-risk:RiskMetricsReport:v1",
    source_route="/analytics/risk/metrics",
    reason_code=ReasonCode.VOLATILITY_ATTENTION,
)

DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY = OpportunityFamilyCompatibility(
    family=OpportunityFamily.HIGH_VOLATILITY,
    archetype=OpportunityArchetype.HIGH_VOLATILITY_DRAWDOWN_REVIEW,
    evidence_lane=OpportunityEvidenceLane.LOTUS_RISK_DRAWDOWN_REVIEW,
    source_system=SourceSystem.LOTUS_RISK,
    source_product_id="lotus-risk:DrawdownAnalyticsReport:v1",
    source_route="/analytics/risk/drawdown",
    reason_code=ReasonCode.DRAWDOWN_ATTENTION,
)
