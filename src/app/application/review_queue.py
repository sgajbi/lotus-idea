from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

from app.domain import (
    DEFAULT_SCORING_POLICY,
    IdeaScoringPolicy,
    QueueExclusionReason,
    QueueAccessScopeFilter,
    QueueSnooze,
    ReviewQueueProjection,
    build_review_queue,
)
from app.ports.idea_repository import CandidateSnapshotRepository


@dataclass(frozen=True)
class BuildReviewQueueFromRepositoryCommand:
    evaluated_at_utc: datetime
    snoozes: tuple[QueueSnooze, ...] = ()
    access_scope_filter: QueueAccessScopeFilter | None = None

    def __post_init__(self) -> None:
        if self.evaluated_at_utc.tzinfo is None or self.evaluated_at_utc.utcoffset() is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        object.__setattr__(self, "snoozes", tuple(self.snoozes))


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
) -> ReviewQueueProjection:
    snapshot = repository.snapshot()
    candidates = tuple(record.candidate for record in snapshot.candidate_records.values())
    return build_review_queue(
        candidates,
        policy=policy,
        evaluated_at_utc=command.evaluated_at_utc,
        snoozes=command.snoozes,
        access_scope_filter=command.access_scope_filter,
    )


def build_review_queue_readiness_snapshot(
    command: BuildReviewQueueFromRepositoryCommand,
    *,
    repository: CandidateSnapshotRepository,
    durable_storage_backed: bool,
    policy: IdeaScoringPolicy = DEFAULT_SCORING_POLICY,
) -> ReviewQueueReadinessSnapshot:
    snapshot = repository.snapshot()
    queue = build_review_queue_from_repository(command, repository=repository, policy=policy)
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
            "platform_caller_context_entitlement_proof_missing",
            "workbench_product_proof_missing",
            "data_product_certification_missing",
            "certified_runtime_trust_telemetry_missing",
        )
    )
    return tuple(blockers)
