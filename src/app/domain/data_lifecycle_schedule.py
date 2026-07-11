from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.data_lifecycle import DataLifecycleBlocker, DataLifecycleState


MAX_SCHEDULED_LIFECYCLE_REVIEW_BATCH = 100


class ScheduledLifecycleReviewDecision(StrEnum):
    READY_FOR_AUTHORIZED_PURGE = "ready_for_authorized_purge"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ScheduledLifecycleControlSnapshot:
    candidate_id: str
    tenant_id: str
    policy_ref: str
    state: DataLifecycleState
    retention_expires_at_utc: datetime
    control_version: int
    active_outbox_count: int
    active_downstream_count: int
    held_from_state: DataLifecycleState | None = None

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "tenant_id", "policy_ref"):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")
        _require_utc(self.retention_expires_at_utc, "retention_expires_at_utc")
        if self.control_version <= 0:
            raise ValueError("control_version must be positive")
        for field_name in ("active_outbox_count", "active_downstream_count"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.state is DataLifecycleState.HELD and self.held_from_state is None:
            raise ValueError("held lifecycle snapshot requires held_from_state")
        if self.state is not DataLifecycleState.HELD and self.held_from_state is not None:
            raise ValueError("non-held lifecycle snapshot must not carry held_from_state")


@dataclass(frozen=True)
class ScheduledLifecycleReviewItem:
    snapshot: ScheduledLifecycleControlSnapshot
    decision: ScheduledLifecycleReviewDecision
    blockers: tuple[DataLifecycleBlocker, ...]


@dataclass(frozen=True)
class ScheduledLifecycleReview:
    evaluated_at_utc: datetime
    requested_limit: int
    truncated: bool
    items: tuple[ScheduledLifecycleReviewItem, ...]

    def __post_init__(self) -> None:
        _require_utc(self.evaluated_at_utc, "evaluated_at_utc")
        validate_scheduled_lifecycle_review_limit(self.requested_limit)
        if len(self.items) > self.requested_limit:
            raise ValueError("scheduled lifecycle review exceeds requested_limit")

    @property
    def ready_count(self) -> int:
        return sum(
            item.decision is ScheduledLifecycleReviewDecision.READY_FOR_AUTHORIZED_PURGE
            for item in self.items
        )


@dataclass(frozen=True)
class ScheduledLifecycleBlockerCount:
    blocker: DataLifecycleBlocker
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("scheduled lifecycle blocker count must be positive")


@dataclass(frozen=True)
class ScheduledLifecycleReviewEvidence:
    schema_version: str
    generated_at_utc: datetime
    repository: str
    git_commit: str
    git_ref: str
    ci_run_id: str
    execution_profile: str
    requested_limit: int
    scanned_count: int
    ready_for_authorized_purge_count: int
    blocked_count: int
    blocker_counts: tuple[ScheduledLifecycleBlockerCount, ...]
    truncated: bool
    review_only: bool = True
    privacy_review_required: bool = True
    production_authority_verified: bool = False
    source_safe: bool = True
    certification_status: str = "not_certified"
    supported_feature_promoted: bool = False

    def __post_init__(self) -> None:
        _require_utc(self.generated_at_utc, "generated_at_utc")
        validate_scheduled_lifecycle_review_limit(self.requested_limit)
        for field_name in (
            "schema_version",
            "repository",
            "git_commit",
            "git_ref",
            "ci_run_id",
            "execution_profile",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} is required")
        for field_name in (
            "scanned_count",
            "ready_for_authorized_purge_count",
            "blocked_count",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.scanned_count != self.ready_for_authorized_purge_count + self.blocked_count:
            raise ValueError("scheduled lifecycle evidence counts must reconcile")
        if self.scanned_count > self.requested_limit:
            raise ValueError("scheduled lifecycle evidence exceeds requested_limit")
        if not self.review_only or not self.privacy_review_required:
            raise ValueError("scheduled lifecycle evidence must remain review-only")
        if self.production_authority_verified:
            raise ValueError("scheduled lifecycle review cannot assert production authority")
        if not self.source_safe:
            raise ValueError("scheduled lifecycle evidence must remain source-safe")
        if self.certification_status != "not_certified":
            raise ValueError("scheduled lifecycle evidence must remain not_certified")
        if self.supported_feature_promoted:
            raise ValueError("scheduled lifecycle evidence must not promote a feature")


def validate_scheduled_lifecycle_review_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("scheduled lifecycle review limit must be an integer")
    if limit < 1 or limit > MAX_SCHEDULED_LIFECYCLE_REVIEW_BATCH:
        raise ValueError(
            "scheduled lifecycle review limit must be between 1 and "
            f"{MAX_SCHEDULED_LIFECYCLE_REVIEW_BATCH}"
        )


def evaluate_scheduled_lifecycle_control(
    snapshot: ScheduledLifecycleControlSnapshot,
    *,
    evaluated_at_utc: datetime,
) -> ScheduledLifecycleReviewItem:
    _require_utc(evaluated_at_utc, "evaluated_at_utc")
    blockers: list[DataLifecycleBlocker] = []
    if evaluated_at_utc < snapshot.retention_expires_at_utc:
        blockers.append(DataLifecycleBlocker.RETENTION_NOT_EXPIRED)
    if snapshot.state is DataLifecycleState.HELD:
        blockers.append(DataLifecycleBlocker.LEGAL_HOLD_ACTIVE)
    elif snapshot.state is not DataLifecycleState.ERASED:
        blockers.append(DataLifecycleBlocker.INVALID_STATE)
    if snapshot.active_outbox_count or snapshot.active_downstream_count:
        blockers.append(DataLifecycleBlocker.ACTIVE_DELIVERY_WORK)
    return ScheduledLifecycleReviewItem(
        snapshot=snapshot,
        decision=(
            ScheduledLifecycleReviewDecision.BLOCKED
            if blockers
            else ScheduledLifecycleReviewDecision.READY_FOR_AUTHORIZED_PURGE
        ),
        blockers=tuple(blockers),
    )


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
