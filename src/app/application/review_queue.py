from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from types import MappingProxyType
from typing import Mapping, cast

from app.domain import (
    DEFAULT_REVIEW_QUEUE_POLICY,
    IdeaRepositorySnapshot,
    QueueExclusion,
    QueueExclusionReason,
    QueueAccessScopeFilter,
    QueueSnooze,
    ReviewQueueSnapshotTokenRequiredError,
    ReviewQueueItem,
    ReviewQueueAudience,
    ReviewQueueProjection,
    ReviewQueuePolicy,
    build_review_queue_snapshot_identity,
    build_review_queue,
    require_matching_review_queue_snapshot,
    review_queue_candidate_fingerprint,
    validate_review_queue_snapshot_token,
    visible_review_queue_candidate_records,
)
from app.ports.idea_repository import (
    CandidateSnapshotRepository,
    ReviewQueueReadinessProjectionRepository,
    ReviewQueueReadinessRepositorySummary,
    ReviewQueueProjectionRepository,
    ReviewQueueRepositoryPage,
)


DEFAULT_REVIEW_QUEUE_PAGE_LIMIT = 25
MAX_REVIEW_QUEUE_PAGE_LIMIT = 100


@dataclass(frozen=True)
class BuildReviewQueueFromRepositoryCommand:
    evaluated_at_utc: datetime
    audience: ReviewQueueAudience = ReviewQueueAudience.ADVISOR
    snoozes: tuple[QueueSnooze, ...] = ()
    access_scope_filter: QueueAccessScopeFilter | None = None
    limit: int = DEFAULT_REVIEW_QUEUE_PAGE_LIMIT
    offset: int = 0
    snapshot_token: str | None = None

    def __post_init__(self) -> None:
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        if self.limit < 1 or self.limit > MAX_REVIEW_QUEUE_PAGE_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_REVIEW_QUEUE_PAGE_LIMIT}")
        if self.offset < 0:
            raise ValueError("offset must be greater than or equal to zero")
        if self.snapshot_token is not None:
            object.__setattr__(
                self,
                "snapshot_token",
                validate_review_queue_snapshot_token(self.snapshot_token),
            )
        if self.offset > 0 and self.snapshot_token is None:
            raise ReviewQueueSnapshotTokenRequiredError(
                "snapshot_token is required when offset is greater than zero"
            )
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
    snapshot_token: str


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
    policy: ReviewQueuePolicy = DEFAULT_REVIEW_QUEUE_POLICY,
) -> ReviewQueuePage:
    if not command.snoozes and isinstance(repository, ReviewQueueProjectionRepository):
        repository_page = repository.review_queue_candidate_page(
            evaluated_at_utc=command.evaluated_at_utc,
            audience=command.audience,
            expected_snapshot_token=command.snapshot_token,
            queue_policy_version=policy.policy_version,
            rankable_score_policy_versions=policy.rankable_score_policy_versions,
            access_scope_filter=command.access_scope_filter,
            limit=command.limit,
            offset=command.offset,
        )
        return _page_repository_review_queue(repository_page, command=command, policy=policy)
    snapshot = repository.snapshot()
    queue, snapshot_token = _build_review_queue_from_snapshot(
        command,
        snapshot=snapshot,
        policy=policy,
    )
    return _page_review_queue(queue, command=command, snapshot_token=snapshot_token)


def build_review_queue_readiness_snapshot(
    command: BuildReviewQueueFromRepositoryCommand,
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    policy: ReviewQueuePolicy = DEFAULT_REVIEW_QUEUE_POLICY,
) -> ReviewQueueReadinessSnapshot:
    repository_side_pagination_certified = durable_storage_backed and isinstance(
        repository,
        ReviewQueueReadinessProjectionRepository,
    )
    if repository_side_pagination_certified and not command.snoozes:
        readiness_repository = cast(ReviewQueueReadinessProjectionRepository, repository)
        readiness_summary = readiness_repository.review_queue_readiness_summary(
            evaluated_at_utc=command.evaluated_at_utc,
            audience=command.audience,
            rankable_score_policy_versions=policy.rankable_score_policy_versions,
            access_scope_filter=command.access_scope_filter,
        )
        return _review_queue_readiness_snapshot_from_summary(
            command=command,
            readiness_summary=readiness_summary,
            durable_storage_backed=durable_storage_backed,
            repository_side_pagination_certified=repository_side_pagination_certified,
            policy=policy,
        )

    snapshot = repository.snapshot()
    queue, _ = _build_review_queue_from_snapshot(command, snapshot=snapshot, policy=policy)
    exclusion_counts = {
        reason.value: sum(1 for exclusion in queue.exclusions if exclusion.reason is reason)
        for reason in QueueExclusionReason
    }
    candidates = tuple(
        record.candidate
        for record in visible_review_queue_candidate_records(
            tuple(snapshot.candidate_records.values()),
            evaluated_at_utc=command.evaluated_at_utc,
        )
    )
    certification_blockers = _review_queue_certification_blockers(
        durable_storage_backed=durable_storage_backed,
        repository_side_pagination_certified=repository_side_pagination_certified,
        unrankable_score_policy_count=exclusion_counts[
            QueueExclusionReason.UNRANKABLE_SCORE_POLICY.value
        ],
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
        repository_side_pagination_certified=repository_side_pagination_certified,
        readiness_status=("ready" if not certification_blockers else "blocked"),
        supportability_status="not_certified",
        certification_blockers=certification_blockers,
        supported_feature_promoted=False,
    )


def _review_queue_readiness_snapshot_from_summary(
    *,
    command: BuildReviewQueueFromRepositoryCommand,
    readiness_summary: ReviewQueueReadinessRepositorySummary,
    durable_storage_backed: bool,
    repository_side_pagination_certified: bool,
    policy: ReviewQueuePolicy,
) -> ReviewQueueReadinessSnapshot:
    certification_blockers = _review_queue_certification_blockers(
        durable_storage_backed=durable_storage_backed,
        repository_side_pagination_certified=repository_side_pagination_certified,
        unrankable_score_policy_count=readiness_summary.exclusion_counts.get(
            QueueExclusionReason.UNRANKABLE_SCORE_POLICY.value,
            0,
        ),
    )
    return ReviewQueueReadinessSnapshot(
        repository="lotus-idea",
        policy_version=policy.policy_version,
        evaluated_at_utc=command.evaluated_at_utc,
        queue_projection_available=True,
        candidate_snapshot_count=readiness_summary.candidate_snapshot_count,
        reviewable_item_count=readiness_summary.reviewable_item_count,
        excluded_candidate_count=readiness_summary.excluded_candidate_count,
        exclusion_counts=readiness_summary.exclusion_counts,
        scored_candidate_count=readiness_summary.scored_candidate_count,
        unscored_candidate_count=readiness_summary.unscored_candidate_count,
        durable_storage_backed=durable_storage_backed,
        repository_side_pagination_certified=repository_side_pagination_certified,
        readiness_status=("ready" if not certification_blockers else "blocked"),
        supportability_status="not_certified",
        certification_blockers=certification_blockers,
        supported_feature_promoted=False,
    )


def _review_queue_certification_blockers(
    *,
    durable_storage_backed: bool,
    repository_side_pagination_certified: bool,
    unrankable_score_policy_count: int,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not durable_storage_backed:
        blockers.append("durable_repository_not_configured")
    if not repository_side_pagination_certified:
        blockers.append("repository_side_queue_pagination_not_certified")
    if unrankable_score_policy_count > 0:
        blockers.append("review_queue_score_policy_coverage_incomplete")
    blockers.extend(
        (
            "workbench_product_proof_missing",
            "data_product_certification_missing",
            "certified_runtime_trust_telemetry_missing",
        )
    )
    return tuple(blockers)


def _page_repository_review_queue(
    repository_page: ReviewQueueRepositoryPage,
    *,
    command: BuildReviewQueueFromRepositoryCommand,
    policy: ReviewQueuePolicy,
) -> ReviewQueuePage:
    queue = build_review_queue(
        tuple(record.candidate for record in repository_page.candidate_records),
        audience=command.audience,
        policy=policy,
        evaluated_at_utc=command.evaluated_at_utc,
        access_scope_filter=command.access_scope_filter,
    )
    ranked_items = tuple(
        replace(item, rank=command.offset + index + 1) for index, item in enumerate(queue.items)
    )
    total_window_count = max(
        repository_page.total_reviewable_item_count,
        repository_page.total_excluded_candidate_count,
    )
    next_offset = command.offset + command.limit
    has_next_page = next_offset < total_window_count
    return ReviewQueuePage(
        projection=ReviewQueueProjection(
            audience=queue.audience,
            policy_version=queue.policy_version,
            evaluated_at_utc=queue.evaluated_at_utc,
            items=ranked_items,
            exclusions=(),
        ),
        page=ReviewQueuePageMetadata(
            limit=command.limit,
            offset=command.offset,
            returned_item_count=len(ranked_items),
            total_reviewable_item_count=repository_page.total_reviewable_item_count,
            returned_exclusion_count=0,
            total_excluded_candidate_count=repository_page.total_excluded_candidate_count,
            next_offset=(next_offset if has_next_page else None),
            has_next_page=has_next_page,
            snapshot_token=repository_page.snapshot_token,
        ),
    )


def _build_review_queue_from_snapshot(
    command: BuildReviewQueueFromRepositoryCommand,
    *,
    snapshot: IdeaRepositorySnapshot,
    policy: ReviewQueuePolicy,
) -> tuple[ReviewQueueProjection, str]:
    visible_records = visible_review_queue_candidate_records(
        tuple(snapshot.candidate_records.values()),
        audience=command.audience,
        evaluated_at_utc=command.evaluated_at_utc,
    )
    candidates = tuple(record.candidate for record in visible_records)
    queue = build_review_queue(
        candidates,
        audience=command.audience,
        policy=policy,
        evaluated_at_utc=command.evaluated_at_utc,
        snoozes=command.snoozes,
        access_scope_filter=command.access_scope_filter,
    )
    snapshot_identity = build_review_queue_snapshot_identity(
        fingerprint=review_queue_candidate_fingerprint(visible_records),
        audience=command.audience,
        evaluated_at_utc=command.evaluated_at_utc,
        policy_version=queue.policy_version,
        rankable_score_policy_versions=policy.rankable_score_policy_versions,
        access_scope_filter=command.access_scope_filter,
        snoozes=command.snoozes,
    )
    require_matching_review_queue_snapshot(
        expected_token=command.snapshot_token,
        actual_token=snapshot_identity.token,
    )
    return queue, snapshot_identity.token


def _page_review_queue(
    queue: ReviewQueueProjection,
    *,
    command: BuildReviewQueueFromRepositoryCommand,
    snapshot_token: str,
) -> ReviewQueuePage:
    item_window = queue.items[command.offset : command.offset + command.limit]
    exclusion_window = queue.exclusions[command.offset : command.offset + command.limit]
    total_window_count = max(len(queue.items), len(queue.exclusions))
    next_offset = command.offset + command.limit
    has_next_page = next_offset < total_window_count
    return ReviewQueuePage(
        projection=ReviewQueueProjection(
            audience=queue.audience,
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
            snapshot_token=snapshot_token,
        ),
    )
