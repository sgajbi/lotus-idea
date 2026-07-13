from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from app.application.review_queue import (
    BuildReviewQueueFromRepositoryCommand,
    build_review_queue_readiness_snapshot,
)
from app.domain import QueueAccessScopeFilter, QueueExclusionReason, ReviewQueueAudience
from app.ports.idea_repository import CandidateSnapshotRepository


OPERATOR_EXCEPTION_REASONS = (
    QueueExclusionReason.INVALID_STATE,
    QueueExclusionReason.UNSUPPORTED_EVIDENCE,
    QueueExclusionReason.UNSCORED,
    QueueExclusionReason.UNRANKABLE_SCORE_POLICY,
    QueueExclusionReason.NON_REVIEWABLE_STATUS,
)


@dataclass(frozen=True)
class ReviewQueueAudienceExceptionSummary:
    audience: ReviewQueueAudience
    candidate_snapshot_count: int
    exception_count: int
    exception_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "exception_counts", MappingProxyType(dict(self.exception_counts)))


@dataclass(frozen=True)
class ReviewQueueExceptionSnapshot:
    policy_version: str
    evaluated_at_utc: datetime
    audiences: tuple[ReviewQueueAudienceExceptionSummary, ...]
    total_exception_count: int
    durable_storage_backed: bool
    supportability_status: str = "not_certified"
    supported_feature_promoted: bool = False


def build_review_queue_exception_snapshot(
    *,
    evaluated_at_utc: datetime,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    access_scope_filter: QueueAccessScopeFilter | None = None,
) -> ReviewQueueExceptionSnapshot:
    summaries = tuple(
        build_review_queue_readiness_snapshot(
            BuildReviewQueueFromRepositoryCommand(
                evaluated_at_utc=evaluated_at_utc,
                audience=audience,
                access_scope_filter=access_scope_filter,
            ),
            repository=repository,
            durable_storage_backed=durable_storage_backed,
        )
        for audience in ReviewQueueAudience
    )
    audience_summaries = tuple(
        ReviewQueueAudienceExceptionSummary(
            audience=audience,
            candidate_snapshot_count=summary.candidate_snapshot_count,
            exception_count=sum(
                summary.exclusion_counts[reason.value] for reason in OPERATOR_EXCEPTION_REASONS
            ),
            exception_counts={
                reason.value: summary.exclusion_counts[reason.value]
                for reason in OPERATOR_EXCEPTION_REASONS
            },
        )
        for audience, summary in zip(ReviewQueueAudience, summaries, strict=True)
    )
    return ReviewQueueExceptionSnapshot(
        policy_version=summaries[0].policy_version,
        evaluated_at_utc=evaluated_at_utc,
        audiences=audience_summaries,
        total_exception_count=sum(summary.exception_count for summary in audience_summaries),
        durable_storage_backed=durable_storage_backed,
    )


__all__ = [
    "OPERATOR_EXCEPTION_REASONS",
    "ReviewQueueAudienceExceptionSummary",
    "ReviewQueueExceptionSnapshot",
    "build_review_queue_exception_snapshot",
]
