from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain import (
    DEFAULT_SCORING_POLICY,
    IdeaScoringPolicy,
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
