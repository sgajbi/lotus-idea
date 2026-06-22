from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum

from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.ideas import (
    EvidenceSupportability,
    IdeaCandidate,
    IdeaLifecycleStatus,
    IdeaScore,
    ReasonCode,
    ReviewPosture,
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


class QueuePriorityBucket(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"
    WATCHLIST = "watchlist"


class QueueExclusionReason(StrEnum):
    SUPPRESSED = "suppressed"
    DUPLICATE = "duplicate"
    EXPIRED = "expired"
    CLOSED = "closed"
    REJECTED = "rejected"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    SNOOZED = "snoozed"
    UNSCORED = "unscored"
    NON_REVIEWABLE_STATUS = "non_reviewable_status"
    ACCESS_SCOPE_MISMATCH = "access_scope_mismatch"


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
    critical_threshold: Decimal = Decimal("85")
    high_threshold: Decimal = Decimal("70")
    standard_threshold: Decimal = Decimal("50")

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
        for field_name, value in (
            ("conflict_penalty", self.conflict_penalty),
            ("critical_threshold", self.critical_threshold),
            ("high_threshold", self.high_threshold),
            ("standard_threshold", self.standard_threshold),
        ):
            _require_score(value, field_name)
        if not (
            self.critical_threshold
            >= self.high_threshold
            >= self.standard_threshold
            >= Decimal("0")
        ):
            raise ValueError("priority thresholds must be descending")


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


@dataclass(frozen=True)
class QueueSnooze:
    candidate_id: str
    snoozed_until_utc: datetime
    reason_codes: tuple[ReasonCode, ...]

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_aware_utc(self.snoozed_until_utc, "snoozed_until_utc")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class QueueExclusion:
    candidate_id: str
    reason: QueueExclusionReason
    detail: str

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.detail, "detail")


@dataclass(frozen=True)
class ReviewQueueItem:
    rank: int
    candidate: IdeaCandidate
    score: Decimal
    priority_bucket: QueuePriorityBucket
    policy_version: str
    reason_codes: tuple[ReasonCode, ...]

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be greater than zero")
        _require_text(self.policy_version, "policy_version")
        _require_score(self.score, "score")
        if not self.reason_codes:
            raise ValueError("reason_codes is required")
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class ReviewQueueProjection:
    policy_version: str
    evaluated_at_utc: datetime
    items: tuple[ReviewQueueItem, ...]
    exclusions: tuple[QueueExclusion, ...]

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        _require_aware_utc(self.evaluated_at_utc, "evaluated_at_utc")
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))


DEFAULT_SCORING_POLICY = IdeaScoringPolicy(policy_version="idea-deterministic-ranking-v1")

_SCORE_REASON_CODES: tuple[ReasonCode, ...] = (
    ReasonCode.MATERIALITY_SCORE,
    ReasonCode.URGENCY_SCORE,
    ReasonCode.CONFIDENCE_SCORE,
    ReasonCode.EVIDENCE_QUALITY_SCORE,
    ReasonCode.FRESHNESS_SCORE,
    ReasonCode.RELEVANCE_SCORE,
    ReasonCode.DOWNSTREAM_FIT_SCORE,
)

_REVIEWABLE_STATUSES: frozenset[IdeaLifecycleStatus] = frozenset(
    {
        IdeaLifecycleStatus.GENERATED,
        IdeaLifecycleStatus.ENRICHED,
        IdeaLifecycleStatus.SCORED,
        IdeaLifecycleStatus.GOVERNANCE_CHECKED,
        IdeaLifecycleStatus.READY_FOR_REVIEW,
    }
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


def build_review_queue(
    candidates: tuple[IdeaCandidate, ...],
    *,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
    evaluated_at_utc: datetime | None = None,
    snoozes: tuple[QueueSnooze, ...] = (),
    access_scope_filter: QueueAccessScopeFilter | None = None,
) -> ReviewQueueProjection:
    evaluated_at = evaluated_at_utc or datetime.now(UTC)
    _require_aware_utc(evaluated_at, "evaluated_at_utc")
    active_snoozes = {
        snooze.candidate_id: snooze for snooze in snoozes if snooze.snoozed_until_utc > evaluated_at
    }
    exclusions: list[QueueExclusion] = []
    eligible_candidates: list[IdeaCandidate] = []
    for candidate in candidates:
        exclusion = _queue_exclusion_for_candidate(
            candidate,
            active_snoozes,
            access_scope_filter,
        )
        if exclusion is None:
            eligible_candidates.append(candidate)
        else:
            exclusions.append(exclusion)

    winners_by_signal: dict[tuple[str, ...], IdeaCandidate] = {}
    for candidate in sorted(eligible_candidates, key=_queue_sort_key):
        signal_key = tuple(sorted(candidate.source_signal_ids))
        if signal_key in winners_by_signal:
            exclusions.append(
                QueueExclusion(
                    candidate_id=candidate.candidate_id,
                    reason=QueueExclusionReason.DUPLICATE,
                    detail=f"duplicate source signals already represented by {signal_key}",
                )
            )
            continue
        winners_by_signal[signal_key] = candidate

    ranked_candidates = sorted(winners_by_signal.values(), key=_queue_sort_key)
    items = tuple(
        ReviewQueueItem(
            rank=index + 1,
            candidate=candidate,
            score=_candidate_score(candidate),
            priority_bucket=priority_bucket_for_score(_candidate_score(candidate), policy=policy),
            policy_version=candidate.score.policy_version
            if candidate.score
            else policy.policy_version,
            reason_codes=(
                candidate.score.reason_codes if candidate.score else (ReasonCode.QUEUE_PRIORITY,)
            ),
        )
        for index, candidate in enumerate(ranked_candidates)
    )
    return ReviewQueueProjection(
        policy_version=policy.policy_version,
        evaluated_at_utc=evaluated_at,
        items=items,
        exclusions=tuple(exclusions),
    )


def priority_bucket_for_score(
    score: Decimal,
    *,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
) -> QueuePriorityBucket:
    _require_score(score, "score")
    if score >= policy.critical_threshold:
        return QueuePriorityBucket.CRITICAL
    if score >= policy.high_threshold:
        return QueuePriorityBucket.HIGH
    if score >= policy.standard_threshold:
        return QueuePriorityBucket.STANDARD
    return QueuePriorityBucket.WATCHLIST


def _queue_exclusion_for_candidate(
    candidate: IdeaCandidate,
    active_snoozes: dict[str, QueueSnooze],
    access_scope_filter: QueueAccessScopeFilter | None,
) -> QueueExclusion | None:
    if access_scope_filter is not None and not access_scope_filter.matches(candidate.access_scope):
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.ACCESS_SCOPE_MISMATCH,
            detail="candidate is outside the requested advisor access scope",
        )
    if candidate.candidate_id in active_snoozes:
        snooze = active_snoozes[candidate.candidate_id]
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.SNOOZED,
            detail=f"snoozed until {snooze.snoozed_until_utc.isoformat()}",
        )
    if (
        candidate.suppression_reason is not None
        or candidate.review_posture is ReviewPosture.SUPPRESSED
    ):
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.SUPPRESSED,
            detail="candidate is suppressed",
        )
    if candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.EXPIRED,
            detail="candidate lifecycle is expired",
        )
    if candidate.lifecycle_status is IdeaLifecycleStatus.CLOSED:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.CLOSED,
            detail="candidate lifecycle is closed",
        )
    if candidate.lifecycle_status is IdeaLifecycleStatus.REJECTED:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.REJECTED,
            detail="candidate lifecycle is rejected",
        )
    if candidate.evidence_packet.supportability is EvidenceSupportability.BLOCKED:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.UNSUPPORTED_EVIDENCE,
            detail="candidate evidence is blocked",
        )
    if candidate.score is None:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.UNSCORED,
            detail="candidate has no score",
        )
    if candidate.lifecycle_status not in _REVIEWABLE_STATUSES:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.NON_REVIEWABLE_STATUS,
            detail=f"candidate lifecycle is {candidate.lifecycle_status.value}",
        )
    return None


def _queue_sort_key(candidate: IdeaCandidate) -> tuple[Decimal, datetime, str]:
    return (-_candidate_score(candidate), candidate.created_at_utc, candidate.candidate_id)


def _candidate_score(candidate: IdeaCandidate) -> Decimal:
    if candidate.score is None:
        return Decimal("0")
    return candidate.score.score
