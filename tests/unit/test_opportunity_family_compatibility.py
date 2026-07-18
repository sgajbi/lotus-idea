from __future__ import annotations

from app.domain import (
    DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY,
    HIGH_VOLATILITY_FAMILY_COMPATIBILITY,
    OpportunityArchetype,
    OpportunityEvidenceLane,
    OpportunityFamily,
    ReasonCode,
    SourceSystem,
)


def test_drawdown_review_keeps_high_volatility_family_for_compatibility() -> None:
    assert DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family is OpportunityFamily.HIGH_VOLATILITY
    assert (
        DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.archetype
        is OpportunityArchetype.HIGH_VOLATILITY_DRAWDOWN_REVIEW
    )
    assert (
        DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.evidence_lane
        is OpportunityEvidenceLane.LOTUS_RISK_DRAWDOWN_REVIEW
    )
    assert DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.reason_code is ReasonCode.DRAWDOWN_ATTENTION
    assert DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_system is SourceSystem.LOTUS_RISK
    assert (
        DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_product_id
        == "lotus-risk:DrawdownAnalyticsReport:v1"
    )
    assert DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_route == "/analytics/risk/drawdown"


def test_high_volatility_and_drawdown_share_archetype_but_not_evidence_lane() -> None:
    assert HIGH_VOLATILITY_FAMILY_COMPATIBILITY.family is OpportunityFamily.HIGH_VOLATILITY
    assert (
        HIGH_VOLATILITY_FAMILY_COMPATIBILITY.archetype
        is DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.archetype
    )
    assert (
        HIGH_VOLATILITY_FAMILY_COMPATIBILITY.evidence_lane
        is not DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.evidence_lane
    )
    assert (
        HIGH_VOLATILITY_FAMILY_COMPATIBILITY.source_product_id
        != DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_product_id
    )
    assert (
        HIGH_VOLATILITY_FAMILY_COMPATIBILITY.reason_code
        is not DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.reason_code
    )
