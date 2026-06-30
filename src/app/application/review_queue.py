from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from app.domain import (
    DEFAULT_SCORING_POLICY,
    IdeaScoringPolicy,
    IdeaRepositorySnapshot,
    QueueExclusion,
    QueueExclusionReason,
    QueueAccessScopeFilter,
    QueueSnooze,
    ReviewQueueItem,
    ReviewQueueProjection,
    build_review_queue,
)
from app.ports.idea_repository import CandidateSnapshotRepository


DEFAULT_REVIEW_QUEUE_PAGE_LIMIT = 25
MAX_REVIEW_QUEUE_PAGE_LIMIT = 100


@dataclass(frozen=True)
class BuildReviewQueueFromRepositoryCommand:
    evaluated_at_utc: datetime
    snoozes: tuple[QueueSnooze, ...] = ()
    access_scope_filter: QueueAccessScopeFilter | None = None
    limit: int = DEFAULT_REVIEW_QUEUE_PAGE_LIMIT
    offset: int = 0

    def __post_init__(self) -> None:
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if self.limit < 1 or self.limit > MAX_REVIEW_QUEUE_PAGE_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_REVIEW_QUEUE_PAGE_LIMIT}")
        if self.offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        object.__setattr__(self, "snoozes", tuple(self.snoozes))


@dataclass(frozen=True)
class ReviewQueuePageMetadata:
    limit: int
    offset: int
    returned_item_count: int
    total_reviewable_item_count: int
    returned_exclusion_count: int
    total_excluded_candidate_count: int
    next_offset: int | None
    has_next_page: bool


@dataclass(frozen=True)
class ReviewQueuePage:
    projection: ReviewQueueProjection
    page: ReviewQueuePageMetadata

    @property
    def policy_version(self) -> str:
        return self.projection.policy_version

    @property
    def evaluated_at_utc(self) -> datetime:
        return self.projection.evaluated_at_utc

    @property
    def items(self) -> tuple[ReviewQueueItem, ...]:
        return self.projection.items

    @property
    def exclusions(self) -> tuple[QueueExclusion, ...]:
        return self.projection.exclusions


@dataclass(frozen=True)
class ReviewQueueReadinessSnapshot:
    repository: str
    policy_version: str
    evaluated_at_utc: datetime
    queue_projection_available: bool
    candidate_snapshot_count: int
    reviewable_item_count: int
    excluded_candidate_count: int
    exclusion_counts: Mapping[str, int]
    scored_candidate_count: int
    unscored_candidate_count: int
    durable_storage_backed: bool
    repository_side_pagination_certified: bool
    readiness_status: str
    supportability_status: str
    certification_blockers: tuple[str, ...]
    supported_feature_promoted: bool

    @property
    def certification_ready(self) -> bool:
        return not self.certification_blockers

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "exclusion_counts",
            MappingProxyType(dict(self.exclusion_counts)),
        )
        object.__setattr__(
            self,
            "certification_blockers",
            tuple(self.certification_blockers),
        )


def build_review_queue_from_repository(
    command: BuildReviewQueueFromRepositoryCommand,
    *,
    repository: CandidateSnapshotRepository,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
) -> ReviewQueuePage:
    snapshot = repository.snapshot()
    queue = _build_review_queue_from_snapshot(command, snapshot=snapshot, policy=policy)
    return _page_review_queue(queue, command=command)


def build_review_queue_readiness_snapshot(
    command: BuildReviewQueueFromRepositoryCommand,
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
) -> ReviewQueueReadinessSnapshot:
    snapshot = repository.snapshot()
    queue = _build_review_queue_from_snapshot(command, snapshot=snapshot, policy=policy)
    exclusion_counts = {
        reason.value: sum(1 for exclusion in queue.exclusions if exclusion.reason is reason)
        for reason in QueueExclusionReason
    }
    candidates = tuple(record.candidate for record in snapshot.candidate_records.values())
    certification_blockers = _review_queue_certification_blockers(
        durable_storage_backed=durable_storage_backed,
    )
    return ReviewQueueReadinessSnapshot(
        repository="lotus-idea",
        policy_version=queue.policy_version,
        evaluated_at_utc=queue.evaluated_at_utc,
        queue_projection_available=True,
        candidate_snapshot_count=len(candidates),
        reviewable_item_count=len(queue.items),
        excluded_candidate_count=len(queue.exclusions),
        exclusion_counts=exclusion_counts,
        scored_candidate_count=sum(1 for candidate in candidates if candidate.score is not None),
        unscored_candidate_count=sum(1 for candidate in candidates if candidate.score is None),
        durable_storage_backed=durable_storage_backed,
        repository_side_pagination_certified=False,
        readiness_status=("ready" if not certification_blockers else "blocked"),
        supportability_status="not_certified",
        certification_blockers=certification_blockers,
        supported_feature_promoted=False,
    )


def _review_queue_certification_blockers(*, durable_storage_backed: bool) -> tuple[str, ...]:
    blockers: list[str] = []
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    blockers.extend(
        (
            "repository_side_queue_pagination_not_certified",
            "workbench_product_proof_missing",
            "data_product_certification_missing",
            "certified_runtime_trust_telemetry_missing",
        )
    )
    return tuple(blockers)


def _build_review_queue_from_snapshot(
    command: BuildReviewQueueFromRepositoryCommand,
    *,
    snapshot: IdeaRepositorySnapshot,
    policy: IdeaScoringPolicy,
) -> ReviewQueueProjection:
    candidates = tuple(
        record.candidate
        for record in sorted(
            snapshot.candidate_records.values(),
            key=lambda record: record.candidate.candidate_id,
        )
    )
    return build_review_queue(
        candidates,
        policy=policy,
        evaluated_at_utc=command.evaluated_at_utc,
        snoozes=command.snoozes,
        access_scope_filter=command.access_scope_filter,
    )


def _page_review_queue(
    queue: ReviewQueueProjection,
    *,
    command: BuildReviewQueueFromRepositoryCommand,
) -> ReviewQueuePage:
    item_window = queue.items[command.offset : command.offset + command.limit]
    exclusion_window = queue.exclusions[command.offset : command.offset + command.limit]
    total_window_count = max(len(queue.items), len(queue.exclusions))
    next_offset = command.offset + command.limit
    has_next_page = next_offset < total_window_count
    return ReviewQueuePage(
        projection=ReviewQueueProjection(
            policy_version=queue.policy_version,
            evaluated_at_utc=queue.evaluated_at_utc,
            items=item_window,
            exclusions=exclusion_window,
        ),
        page=ReviewQueuePageMetadata(
            limit=command.limit,
            offset=command.offset,
            returned_item_count=len(item_window),
            total_reviewable_item_count=len(queue.items),
            returned_exclusion_count=len(exclusion_window),
            total_excluded_candidate_count=len(queue.exclusions),
            next_offset=(next_offset if has_next_page else None),
            has_next_page=has_next_page,
        ),
    )
