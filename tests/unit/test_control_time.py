from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.control_time import (
    DOWNSTREAM_OUTCOME_TIME_POLICY,
    PRESENTATION_TIME_POLICY,
    REVIEW_DECISION_TIME_POLICY,
    ObservedTimePolicy,
    ObservedTimeSkewError,
    require_observed_time_within_policy,
)


ACCEPTED_AT = datetime(2026, 9, 5, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "observed_at",
    (
        ACCEPTED_AT - REVIEW_DECISION_TIME_POLICY.maximum_past_skew,
        ACCEPTED_AT + REVIEW_DECISION_TIME_POLICY.maximum_future_skew,
    ),
)
def test_observed_time_policy_accepts_exact_boundaries(observed_at: datetime) -> None:
    require_observed_time_within_policy(
        observed_at,
        ACCEPTED_AT,
        REVIEW_DECISION_TIME_POLICY,
    )


@pytest.mark.parametrize(
    ("observed_at", "policy"),
    (
        (
            ACCEPTED_AT - REVIEW_DECISION_TIME_POLICY.maximum_past_skew - timedelta.resolution,
            REVIEW_DECISION_TIME_POLICY,
        ),
        (
            ACCEPTED_AT + PRESENTATION_TIME_POLICY.maximum_future_skew + timedelta.resolution,
            PRESENTATION_TIME_POLICY,
        ),
        (
            ACCEPTED_AT - DOWNSTREAM_OUTCOME_TIME_POLICY.maximum_past_skew - timedelta.resolution,
            DOWNSTREAM_OUTCOME_TIME_POLICY,
        ),
    ),
)
def test_observed_time_policy_fails_closed_outside_operation_bounds(
    observed_at: datetime,
    policy: ObservedTimePolicy,
) -> None:
    with pytest.raises(ObservedTimeSkewError):
        require_observed_time_within_policy(observed_at, ACCEPTED_AT, policy)


def test_observed_time_policy_rejects_naive_control_time() -> None:
    with pytest.raises(ValueError, match="accepted_at_utc must be timezone-aware"):
        require_observed_time_within_policy(
            ACCEPTED_AT,
            datetime(2026, 9, 5, 10, 0),
            REVIEW_DECISION_TIME_POLICY,
        )


@pytest.mark.parametrize(
    ("observed_at", "accepted_at", "field_name"),
    (
        (
            datetime(2026, 9, 5, 18, 0, tzinfo=timezone(timedelta(hours=8))),
            ACCEPTED_AT,
            "observed_at_utc",
        ),
        (
            ACCEPTED_AT,
            datetime(2026, 9, 5, 18, 0, tzinfo=timezone(timedelta(hours=8))),
            "accepted_at_utc",
        ),
    ),
)
def test_observed_time_policy_requires_explicit_utc_offset(
    observed_at: datetime,
    accepted_at: datetime,
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=rf"{field_name} must use UTC offset \+00:00"):
        require_observed_time_within_policy(
            observed_at,
            accepted_at,
            REVIEW_DECISION_TIME_POLICY,
        )
