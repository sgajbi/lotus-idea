from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

from app.domain.ideas import (
    IdeaCandidate,
    IdeaScore,
    ReasonCode,
)


def _require_score(value: Decimal, field_name: str) -> None:
    if value < Decimal("0") or value > Decimal("100"):
        raise ValueError(f"{field_name} must be between 0 and 100")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ScoreComponent(StrEnum):
    MATERIALITY = "materiality"
    URGENCY = "urgency"
    CONFIDENCE = "confidence"
    EVIDENCE_QUALITY = "evidence_quality"
    FRESHNESS = "freshness"
    RELEVANCE = "relevance"
    DOWNSTREAM_FIT = "downstream_fit"


class CandidateScorePolicyVersion(StrEnum):
    ALLOCATION_DRIFT = "allocation-drift-mandate-review-v1"
    BOND_MATURITY = "bond-maturity-review-v1"
    LOW_INCOME = "cashflow-liquidity-review-v1"
    CONCENTRATION = "concentration-attention-v1"
    DRAWDOWN_REVIEW = "drawdown-review-attention-v1"
    HIGH_VOLATILITY = "high-volatility-attention-v1"
    WEIGHTED_EVIDENCE = "idea-weighted-evidence-score-v1"
    HIGH_CASH = "idle-liquidity-v1"
    MANDATE_RESTRICTION = "mandate-restriction-review-v1"
    MISSING_BENCHMARK = "missing-benchmark-review-v1"
    MISSING_RISK_PROFILE = "missing-risk-profile-review-v1"
    MISSING_SUITABILITY = "missing-suitability-context-review-v1"
    UNDERPERFORMANCE = "underperformance-review-v1"


DEFAULT_RANKABLE_SCORE_POLICY_VERSIONS: tuple[str, ...] = tuple(
    version.value for version in CandidateScorePolicyVersion
)


@dataclass(frozen=True)
class IdeaScoringInputs:
    materiality: Decimal
    urgency: Decimal
    confidence: Decimal
    evidence_quality: Decimal
    freshness: Decimal
    relevance: Decimal
    downstream_fit: Decimal
    has_conflict_flags: bool = False

    def __post_init__(self) -> None:
        for field_name, value in (
            ("materiality", self.materiality),
            ("urgency", self.urgency),
            ("confidence", self.confidence),
            ("evidence_quality", self.evidence_quality),
            ("freshness", self.freshness),
            ("relevance", self.relevance),
            ("downstream_fit", self.downstream_fit),
        ):
            _require_score(value, field_name)


@dataclass(frozen=True)
class IdeaScoringPolicy:
    policy_version: str
    materiality_weight: Decimal = Decimal("0.20")
    urgency_weight: Decimal = Decimal("0.15")
    confidence_weight: Decimal = Decimal("0.15")
    evidence_quality_weight: Decimal = Decimal("0.15")
    freshness_weight: Decimal = Decimal("0.10")
    relevance_weight: Decimal = Decimal("0.10")
    downstream_fit_weight: Decimal = Decimal("0.15")
    conflict_penalty: Decimal = Decimal("15")

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        weights = (
            self.materiality_weight,
            self.urgency_weight,
            self.confidence_weight,
            self.evidence_quality_weight,
            self.freshness_weight,
            self.relevance_weight,
            self.downstream_fit_weight,
        )
        if sum(weights, Decimal("0")) != Decimal("1.00"):
            raise ValueError("score weights must sum to 1.00")
        _require_score(self.conflict_penalty, "conflict_penalty")


@dataclass(frozen=True)
class ScoreContribution:
    component: ScoreComponent
    input_score: Decimal
    weight: Decimal
    contribution: Decimal


@dataclass(frozen=True)
class ScoreBreakdown:
    policy_version: str
    final_score: Decimal
    reason_codes: tuple[ReasonCode, ...]
    contributions: tuple[ScoreContribution, ...]
    conflict_penalty_applied: Decimal = Decimal("0")


DEFAULT_SCORING_POLICY = IdeaScoringPolicy(
    policy_version=CandidateScorePolicyVersion.WEIGHTED_EVIDENCE.value
)

_SCORE_REASON_CODES: tuple[ReasonCode, ...] = (
    ReasonCode.MATERIALITY_SCORE,
    ReasonCode.URGENCY_SCORE,
    ReasonCode.CONFIDENCE_SCORE,
    ReasonCode.EVIDENCE_QUALITY_SCORE,
    ReasonCode.FRESHNESS_SCORE,
    ReasonCode.RELEVANCE_SCORE,
    ReasonCode.DOWNSTREAM_FIT_SCORE,
)


def score_candidate(
    candidate: IdeaCandidate,
    inputs: IdeaScoringInputs,
    *,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
    scored_at_utc: datetime | None = None,
) -> tuple[IdeaCandidate, ScoreBreakdown]:
    scored_at = scored_at_utc or datetime.now(UTC)
    _require_aware_utc(scored_at, "scored_at_utc")
    breakdown = score_inputs(inputs, policy=policy)
    scored_candidate = replace(
        candidate,
        score=IdeaScore(
            policy_version=breakdown.policy_version,
            score=breakdown.final_score,
            reason_codes=breakdown.reason_codes,
        ),
        updated_at_utc=scored_at,
    )
    return scored_candidate, breakdown


def score_inputs(
    inputs: IdeaScoringInputs,
    *,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
) -> ScoreBreakdown:
    weighted_components = (
        (ScoreComponent.MATERIALITY, inputs.materiality, policy.materiality_weight),
        (ScoreComponent.URGENCY, inputs.urgency, policy.urgency_weight),
        (ScoreComponent.CONFIDENCE, inputs.confidence, policy.confidence_weight),
        (
            ScoreComponent.EVIDENCE_QUALITY,
            inputs.evidence_quality,
            policy.evidence_quality_weight,
        ),
        (ScoreComponent.FRESHNESS, inputs.freshness, policy.freshness_weight),
        (ScoreComponent.RELEVANCE, inputs.relevance, policy.relevance_weight),
        (ScoreComponent.DOWNSTREAM_FIT, inputs.downstream_fit, policy.downstream_fit_weight),
    )
    contributions = tuple(
        ScoreContribution(
            component=component,
            input_score=input_score,
            weight=weight,
            contribution=_quantize(input_score * weight),
        )
        for component, input_score, weight in weighted_components
    )
    total = sum((contribution.contribution for contribution in contributions), Decimal("0"))
    penalty = policy.conflict_penalty if inputs.has_conflict_flags else Decimal("0")
    final_score = max(Decimal("0"), _quantize(total - penalty))
    reason_codes = _SCORE_REASON_CODES + (
        (ReasonCode.CONFLICT_PENALTY,) if inputs.has_conflict_flags else ()
    )
    return ScoreBreakdown(
        policy_version=policy.policy_version,
        final_score=final_score,
        reason_codes=reason_codes,
        contributions=contributions,
        conflict_penalty_applied=penalty,
    )
