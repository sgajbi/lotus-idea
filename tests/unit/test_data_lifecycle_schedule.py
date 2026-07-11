from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.application.data_lifecycle import ReviewScheduledDataLifecycle
from app.domain.data_lifecycle import DataLifecycleBlocker, DataLifecycleState
from app.domain.data_lifecycle_schedule import (
    ScheduledLifecycleControlSnapshot,
    ScheduledLifecycleReviewDecision,
    evaluate_scheduled_lifecycle_control,
)


NOW = datetime(2026, 7, 12, 1, 0, tzinfo=UTC)


class ScheduledRepository:
    def __init__(self, snapshots: tuple[ScheduledLifecycleControlSnapshot, ...]) -> None:
        self.snapshots = snapshots
        self.calls: list[tuple[datetime, int]] = []

    def scan_data_lifecycle_controls(
        self,
        *,
        evaluated_at_utc: datetime,
        limit: int,
    ) -> tuple[ScheduledLifecycleControlSnapshot, ...]:
        self.calls.append((evaluated_at_utc, limit))
        return self.snapshots[:limit]


def expired_erased_snapshot(
    *, candidate_id: str = "candidate-expired-001"
) -> ScheduledLifecycleControlSnapshot:
    return ScheduledLifecycleControlSnapshot(
        candidate_id=candidate_id,
        tenant_id="tenant-private-bank-sg",
        policy_ref="lotus-idea:regulated-advisory-evidence:seven-year:v1",
        state=DataLifecycleState.ERASED,
        retention_expires_at_utc=NOW - timedelta(days=1),
        control_version=2,
        active_outbox_count=0,
        active_downstream_count=0,
    )


def test_scheduled_review_is_bounded_and_reports_truncation() -> None:
    snapshots = tuple(
        expired_erased_snapshot(candidate_id=f"candidate-{index}") for index in range(3)
    )
    repository = ScheduledRepository(snapshots)

    review = ReviewScheduledDataLifecycle(repository, now=lambda: NOW).execute(limit=2)

    assert repository.calls == [(NOW, 3)]
    assert review.truncated is True
    assert review.ready_count == 2
    assert [item.snapshot.candidate_id for item in review.items] == [
        "candidate-0",
        "candidate-1",
    ]


@pytest.mark.parametrize(
    ("snapshot", "expected_blockers"),
    [
        (
            replace(
                expired_erased_snapshot(),
                state=DataLifecycleState.HELD,
                held_from_state=DataLifecycleState.ERASED,
            ),
            (DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,),
        ),
        (
            replace(expired_erased_snapshot(), state=DataLifecycleState.ACTIVE),
            (DataLifecycleBlocker.INVALID_STATE,),
        ),
        (
            replace(expired_erased_snapshot(), active_outbox_count=1),
            (DataLifecycleBlocker.ACTIVE_DELIVERY_WORK,),
        ),
        (
            replace(expired_erased_snapshot(), retention_expires_at_utc=NOW + timedelta(days=1)),
            (DataLifecycleBlocker.RETENTION_NOT_EXPIRED,),
        ),
    ],
)
def test_scheduled_review_blocks_unsafe_purge_candidates(
    snapshot: ScheduledLifecycleControlSnapshot,
    expected_blockers: tuple[DataLifecycleBlocker, ...],
) -> None:
    item = evaluate_scheduled_lifecycle_control(snapshot, evaluated_at_utc=NOW)

    assert item.decision is ScheduledLifecycleReviewDecision.BLOCKED
    assert item.blockers == expected_blockers


@pytest.mark.parametrize("limit", [0, 101, True, 1.5])
def test_scheduled_review_rejects_invalid_batch_limits(limit: object) -> None:
    repository = ScheduledRepository(())

    with pytest.raises(ValueError, match="scheduled lifecycle review limit"):
        ReviewScheduledDataLifecycle(repository, now=lambda: NOW).execute(limit=limit)  # type: ignore[arg-type]
