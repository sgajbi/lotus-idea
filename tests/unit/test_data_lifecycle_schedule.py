from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.application.data_lifecycle import ReviewScheduledDataLifecycle
from app.domain.data_lifecycle import DataLifecycleBlocker, DataLifecycleState
from app.domain.data_lifecycle_schedule import (
    ScheduledLifecycleBlockerCount,
    ScheduledLifecycleControlSnapshot,
    ScheduledLifecycleReview,
    ScheduledLifecycleReviewDecision,
    ScheduledLifecycleReviewEvidence,
    ScheduledLifecycleReviewItem,
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


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"candidate_id": ""}, "candidate_id is required"),
        ({"control_version": 0}, "control_version must be positive"),
        ({"active_outbox_count": -1}, "active_outbox_count must be a non-negative integer"),
        (
            {"state": DataLifecycleState.HELD},
            "held lifecycle snapshot requires held_from_state",
        ),
        (
            {"held_from_state": DataLifecycleState.ACTIVE},
            "non-held lifecycle snapshot must not carry held_from_state",
        ),
        (
            {"retention_expires_at_utc": datetime(2026, 7, 12)},
            "retention_expires_at_utc must be timezone-aware UTC",
        ),
    ],
)
def test_scheduled_snapshot_rejects_invalid_persisted_state(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(expired_erased_snapshot(), **changes)


def test_scheduled_review_rejects_more_items_than_requested() -> None:
    item = ScheduledLifecycleReviewItem(
        snapshot=expired_erased_snapshot(),
        decision=ScheduledLifecycleReviewDecision.READY_FOR_AUTHORIZED_PURGE,
        blockers=(),
    )

    with pytest.raises(ValueError, match="exceeds requested_limit"):
        ScheduledLifecycleReview(
            evaluated_at_utc=NOW,
            requested_limit=1,
            truncated=True,
            items=(item, item),
        )


def valid_review_evidence() -> ScheduledLifecycleReviewEvidence:
    return ScheduledLifecycleReviewEvidence(
        schema_version="lotus-idea.scheduled-lifecycle-review-evidence.v1",
        generated_at_utc=NOW,
        repository="sgajbi/lotus-idea",
        git_commit="a" * 40,
        git_ref="refs/heads/main",
        ci_run_id="12345",
        execution_profile="synthetic_disposable_postgres",
        requested_limit=100,
        scanned_count=2,
        ready_for_authorized_purge_count=1,
        blocked_count=1,
        blocker_counts=(
            ScheduledLifecycleBlockerCount(
                blocker=DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,
                count=1,
            ),
        ),
        truncated=False,
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"repository": ""}, "repository is required"),
        ({"scanned_count": -1}, "scanned_count must be a non-negative integer"),
        ({"blocked_count": 2}, "counts must reconcile"),
        ({"requested_limit": 1}, "exceeds requested_limit"),
        ({"review_only": False}, "must remain review-only"),
        ({"production_authority_verified": True}, "cannot assert production authority"),
        ({"source_safe": False}, "must remain source-safe"),
        ({"certification_status": "certified"}, "must remain not_certified"),
        ({"supported_feature_promoted": True}, "must not promote a feature"),
    ],
)
def test_scheduled_review_evidence_rejects_inconsistent_or_overclaimed_posture(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(valid_review_evidence(), **changes)


def test_scheduled_blocker_count_must_be_positive() -> None:
    with pytest.raises(ValueError, match="blocker count must be positive"):
        ScheduledLifecycleBlockerCount(
            blocker=DataLifecycleBlocker.LEGAL_HOLD_ACTIVE,
            count=0,
        )


def test_scheduled_evaluation_requires_utc_clock() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware UTC"):
        evaluate_scheduled_lifecycle_control(
            expired_erased_snapshot(),
            evaluated_at_utc=datetime(2026, 7, 12),
        )
