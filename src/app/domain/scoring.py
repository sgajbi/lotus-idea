from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

from app.domain.ideas import (
    IdeaCandidate,
    IdeaScore,
    ReasonCode,
    ScoreComponent,
    ScoreContribution,
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


class CandidateScorePolicyVersion(StrEnum):
    ALLOCATION_DRIFT_LEGACY = "allocation-drift-mandate-review-v1"
    ALLOCATION_DRIFT = "allocation-drift-mandate-review-v2"
    BOND_MATURITY_LEGACY = "bond-maturity-review-v1"
    BOND_MATURITY = "bond-maturity-review-v2"
    LOW_INCOME_LEGACY = "cashflow-liquidity-review-v1"
    LOW_INCOME = "cashflow-liquidity-review-v2"
    CONCENTRATION_LEGACY = "concentration-attention-v1"
    CONCENTRATION = "concentration-attention-v2"
    DRAWDOWN_REVIEW_LEGACY = "drawdown-review-attention-v1"
    DRAWDOWN_REVIEW = "drawdown-review-attention-v2"
    HIGH_VOLATILITY_LEGACY = "high-volatility-attention-v1"
    HIGH_VOLATILITY = "high-volatility-attention-v2"
    WEIGHTED_EVIDENCE = "idea-weighted-evidence-score-v1"
    HIGH_CASH_LEGACY = "idle-liquidity-v1"
    HIGH_CASH = "idle-liquidity-v2"
    MANDATE_RESTRICTION_LEGACY = "mandate-restriction-review-v1"
    MANDATE_RESTRICTION = "mandate-restriction-review-v2"
    MISSING_BENCHMARK_LEGACY = "missing-benchmark-review-v1"
    MISSING_BENCHMARK = "missing-benchmark-review-v2"
    MISSING_RISK_PROFILE_LEGACY = "missing-risk-profile-review-v1"
    MISSING_RISK_PROFILE = "missing-risk-profile-review-v2"
    MISSING_SUITABILITY_LEGACY = "missing-suitability-context-review-v1"
    MISSING_SUITABILITY = "missing-suitability-context-review-v2"
    UNDERPERFORMANCE_LEGACY = "underperformance-review-v1"
    UNDERPERFORMANCE = "underperformance-review-v2"


DEFAULT_RANKABLE_SCORE_POLICY_VERSIONS: tuple[str, ...] = tuple(
    version.value for version in CandidateScorePolicyVersion
)


@dataclass(frozen=True)
class IdeaScoringInput:
    component: ScoreComponent
    input_score: Decimal
    weight: Decimal

    def __post_init__(self) -> None:
        _require_score(self.input_score, "input_score")
        if self.weight < Decimal("0") or self.weight > Decimal("1"):
            raise ValueError("weight must be between 0 and 1")
        if self.component is ScoreComponent.LEGACY_FIXED_POLICY:
            raise ValueError("legacy_fixed_policy is not a source-evidence scoring input")


@dataclass(frozen=True)
class IdeaScoringPolicy:
    policy_version: str
    conflict_penalty: Decimal = Decimal("15")

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        _require_score(self.conflict_penalty, "conflict_penalty")


DEFAULT_SCORING_POLICY = IdeaScoringPolicy(
    policy_version=CandidateScorePolicyVersion.WEIGHTED_EVIDENCE.value
)

_SCORE_REASON_CODE_BY_COMPONENT: dict[ScoreComponent, ReasonCode] = {
    ScoreComponent.MATERIALITY: ReasonCode.MATERIALITY_SCORE,
    ScoreComponent.URGENCY: ReasonCode.URGENCY_SCORE,
    ScoreComponent.CONFIDENCE: ReasonCode.CONFIDENCE_SCORE,
    ScoreComponent.EVIDENCE_QUALITY: ReasonCode.EVIDENCE_QUALITY_SCORE,
    ScoreComponent.FRESHNESS: ReasonCode.FRESHNESS_SCORE,
    ScoreComponent.RELEVANCE: ReasonCode.RELEVANCE_SCORE,
    ScoreComponent.DOWNSTREAM_FIT: ReasonCode.DOWNSTREAM_FIT_SCORE,
}


def score_candidate(
    candidate: IdeaCandidate,
    inputs: tuple[IdeaScoringInput, ...],
    *,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
    has_conflict_flags: bool = False,
    reason_codes: tuple[ReasonCode, ...] = (),
    scored_at_utc: datetime | None = None,
) -> tuple[IdeaCandidate, IdeaScore]:
    scored_at = scored_at_utc or datetime.now(UTC)
    _require_aware_utc(scored_at, "scored_at_utc")
    score = score_inputs(
        inputs,
        policy=policy,
        has_conflict_flags=has_conflict_flags,
        reason_codes=reason_codes,
    )
    scored_candidate = replace(
        candidate,
        score=score,
        updated_at_utc=scored_at,
    )
    return scored_candidate, score


def score_inputs(
    inputs: tuple[IdeaScoringInput, ...],
    *,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
    has_conflict_flags: bool = False,
    reason_codes: tuple[ReasonCode, ...] = (),
) -> IdeaScore:
    contributions = tuple(
        ScoreContribution(
            component=scoring_input.component,
            input_score=scoring_input.input_score,
            weight=scoring_input.weight,
            contribution=_quantize(scoring_input.input_score * scoring_input.weight),
        )
        for scoring_input in inputs
    )
    total = sum((contribution.contribution for contribution in contributions), Decimal("0"))
    penalty = policy.conflict_penalty if has_conflict_flags else Decimal("0")
    final_score = min(Decimal("100"), max(Decimal("0"), _quantize(total - penalty)))
    score_reason_codes = (
        reason_codes
        + tuple(
            _SCORE_REASON_CODE_BY_COMPONENT[contribution.component]
            for contribution in contributions
        )
        + ((ReasonCode.CONFLICT_PENALTY,) if has_conflict_flags else ())
    )
    return IdeaScore(
        policy_version=policy.policy_version,
        score=final_score,
        reason_codes=score_reason_codes,
        contributions=contributions,
        conflict_penalty_applied=penalty,
    )


def relative_threshold_score(value: Decimal, threshold: Decimal) -> Decimal:
    """Map threshold attainment to 50 and twice-threshold severity to 100."""
    if threshold <= Decimal("0"):
        raise ValueError("threshold must be positive")
    if value < threshold:
        raise ValueError("value must meet or exceed threshold")
    relative_excess = (value - threshold) / threshold
    return min(Decimal("100"), _quantize(Decimal("50") + Decimal("50") * relative_excess))


def current_complete_materiality_inputs(
    materiality_score: Decimal,
) -> tuple[IdeaScoringInput, ...]:
    """Build the shared inputs for eligible current, complete quantitative evidence."""
    return (
        IdeaScoringInput(
            component=ScoreComponent.MATERIALITY,
            input_score=materiality_score,
            weight=Decimal("0.70"),
        ),
        IdeaScoringInput(
            component=ScoreComponent.EVIDENCE_QUALITY,
            input_score=Decimal("100"),
            weight=Decimal("0.15"),
        ),
        IdeaScoringInput(
            component=ScoreComponent.FRESHNESS,
            input_score=Decimal("100"),
            weight=Decimal("0.15"),
        ),
    )
