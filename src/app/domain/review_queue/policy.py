from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.candidate_state import (
    REVIEWABLE_LIFECYCLE_STATUSES,
    candidate_state_is_compatible,
)
from app.domain.ideas import (
    EvidenceSupportability,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReasonCode,
    ReviewPosture,
)
from app.domain.scoring import DEFAULT_RANKABLE_SCORE_POLICY_VERSIONS


def _require_score(value: Decimal, field_name: str) -> None:
    if value < Decimal("0") or value > Decimal("100"):
        raise ValueError(f"{field_name} must be between 0 and 100")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class QueuePriorityBucket(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"
    WATCHLIST = "watchlist"


class ReviewQueueAudience(StrEnum):
    ADVISOR = "advisor"
    PORTFOLIO_MANAGER = "portfolio_manager"
    COMPLIANCE = "compliance"

    @property
    def required_posture(self) -> ReviewPosture:
        return {
            ReviewQueueAudience.ADVISOR: ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            ReviewQueueAudience.PORTFOLIO_MANAGER: ReviewPosture.PM_REVIEW_REQUIRED,
            ReviewQueueAudience.COMPLIANCE: ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        }[self]


class QueueExclusionReason(StrEnum):
    INVALID_STATE = "invalid_state"
    SUPPRESSED = "suppressed"
    DUPLICATE = "duplicate"
    EXPIRED = "expired"
    CLOSED = "closed"
    REJECTED = "rejected"
    UNSUPPORTED_EVIDENCE = "unsupported_evidence"
    SNOOZED = "snoozed"
    UNSCORED = "unscored"
    UNRANKABLE_SCORE_POLICY = "unrankable_score_policy"
    NON_REVIEWABLE_STATUS = "non_reviewable_status"
    ACCESS_SCOPE_MISMATCH = "access_scope_mismatch"


@dataclass(frozen=True)
class ReviewQueuePolicy:
    policy_version: str
    rankable_score_policy_versions: tuple[str, ...]
    critical_threshold: Decimal = Decimal("85")
    high_threshold: Decimal = Decimal("70")
    standard_threshold: Decimal = Decimal("50")

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        normalized_versions = tuple(
            sorted(version.strip() for version in self.rankable_score_policy_versions)
        )
        if not normalized_versions:
            raise ValueError("rankable_score_policy_versions is required")
        if any(not version for version in normalized_versions):
            raise ValueError("rankable_score_policy_versions cannot contain blank values")
        if len(set(normalized_versions)) != len(normalized_versions):
            raise ValueError("rankable_score_policy_versions must be unique")
        object.__setattr__(self, "rankable_score_policy_versions", normalized_versions)
        for field_name, value in (
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

    def accepts_score_policy(self, policy_version: str) -> bool:
        return policy_version in self.rankable_score_policy_versions


@dataclass(frozen=True)
class QueueSnooze:
    candidate_id: str
    snoozed_until_utc: datetime
    reason_codes: tuple[ReasonCode, ...]

    def __post_init__(self) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_aware_datetime(self.snoozed_until_utc, "snoozed_until_utc")
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
    audience: ReviewQueueAudience
    policy_version: str
    evaluated_at_utc: datetime
    items: tuple[ReviewQueueItem, ...]
    exclusions: tuple[QueueExclusion, ...]

    def __post_init__(self) -> None:
        _require_text(self.policy_version, "policy_version")
        _require_aware_datetime(self.evaluated_at_utc, "evaluated_at_utc")
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))


DEFAULT_REVIEW_QUEUE_POLICY = ReviewQueuePolicy(
    policy_version="idea-deterministic-ranking-v1",
    rankable_score_policy_versions=DEFAULT_RANKABLE_SCORE_POLICY_VERSIONS,
)


def build_review_queue(
    candidates: tuple[IdeaCandidate, ...],
    *,
    audience: ReviewQueueAudience = ReviewQueueAudience.ADVISOR,
    policy: ReviewQueuePolicy = DEFAULT_REVIEW_QUEUE_POLICY,
    evaluated_at_utc: datetime | None = None,
    snoozes: tuple[QueueSnooze, ...] = (),
    access_scope_filter: QueueAccessScopeFilter | None = None,
) -> ReviewQueueProjection:
    evaluated_at = evaluated_at_utc or datetime.now(UTC)
    _require_aware_datetime(evaluated_at, "evaluated_at_utc")
    active_snoozes = {
        snooze.candidate_id: snooze for snooze in snoozes if snooze.snoozed_until_utc > evaluated_at
    }
    exclusions: list[QueueExclusion] = []
    eligible_candidates: list[IdeaCandidate] = []
    for candidate in candidates:
        if candidate.review_posture is not audience.required_posture:
            continue
        exclusion = _queue_exclusion_for_candidate(
            candidate,
            active_snoozes,
            access_scope_filter,
            policy,
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
            policy_version=policy.policy_version,
            reason_codes=(
                candidate.score.reason_codes if candidate.score else (ReasonCode.QUEUE_PRIORITY,)
            ),
        )
        for index, candidate in enumerate(ranked_candidates)
    )
    return ReviewQueueProjection(
        audience=audience,
        policy_version=policy.policy_version,
        evaluated_at_utc=evaluated_at,
        items=items,
        exclusions=tuple(exclusions),
    )


def priority_bucket_for_score(
    score: Decimal,
    *,
    policy: ReviewQueuePolicy = DEFAULT_REVIEW_QUEUE_POLICY,
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
    policy: ReviewQueuePolicy,
) -> QueueExclusion | None:
    if access_scope_filter is not None and not access_scope_filter.matches(candidate.access_scope):
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.ACCESS_SCOPE_MISMATCH,
            detail="candidate is outside the requested advisor access scope",
        )
    if not candidate_state_is_compatible(candidate.lifecycle_status, candidate.review_posture):
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.INVALID_STATE,
            detail="candidate lifecycle and review posture are incompatible",
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
    terminal_reason = {
        IdeaLifecycleStatus.EXPIRED: QueueExclusionReason.EXPIRED,
        IdeaLifecycleStatus.CLOSED: QueueExclusionReason.CLOSED,
        IdeaLifecycleStatus.REJECTED: QueueExclusionReason.REJECTED,
    }.get(candidate.lifecycle_status)
    if terminal_reason is not None:
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=terminal_reason,
            detail=f"candidate lifecycle is {candidate.lifecycle_status.value}",
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
    if not policy.accepts_score_policy(candidate.score.policy_version):
        return QueueExclusion(
            candidate_id=candidate.candidate_id,
            reason=QueueExclusionReason.UNRANKABLE_SCORE_POLICY,
            detail="candidate score policy is not rankable under the active queue policy",
        )
    if candidate.lifecycle_status not in REVIEWABLE_LIFECYCLE_STATUSES:
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
