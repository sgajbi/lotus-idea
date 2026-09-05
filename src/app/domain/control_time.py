from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class AcceptanceTimeSource(StrEnum):
    """Provenance for the service-controlled acceptance timestamp."""

    SERVER_ACCEPTED = "server_accepted"
    LEGACY_OBSERVED_TIME_ASSUMED = "legacy_observed_time_assumed"


@dataclass(frozen=True)
class ObservedTimePolicy:
    policy_id: str
    maximum_past_skew: timedelta
    maximum_future_skew: timedelta


class ObservedTimeSkewError(ValueError):
    def __init__(self, policy_id: str) -> None:
        super().__init__(f"observed time is outside {policy_id} skew bounds")
        self.policy_id = policy_id


REVIEW_DECISION_TIME_POLICY = ObservedTimePolicy(
    policy_id="idea-review-decision-observed-time-v1",
    maximum_past_skew=timedelta(hours=24),
    maximum_future_skew=timedelta(minutes=5),
)
FEEDBACK_TIME_POLICY = ObservedTimePolicy(
    policy_id="idea-feedback-observed-time-v1",
    maximum_past_skew=timedelta(hours=24),
    maximum_future_skew=timedelta(minutes=5),
)
CONVERSION_INTENT_TIME_POLICY = ObservedTimePolicy(
    policy_id="idea-conversion-intent-observed-time-v1",
    maximum_past_skew=timedelta(hours=24),
    maximum_future_skew=timedelta(minutes=5),
)
DOWNSTREAM_OUTCOME_TIME_POLICY = ObservedTimePolicy(
    policy_id="idea-downstream-outcome-observed-time-v1",
    maximum_past_skew=timedelta(days=30),
    maximum_future_skew=timedelta(minutes=5),
)
PRESENTATION_TIME_POLICY = ObservedTimePolicy(
    policy_id="idea-presentation-observed-time-v1",
    maximum_past_skew=timedelta(minutes=15),
    maximum_future_skew=timedelta(minutes=5),
)


def require_observed_time_within_policy(
    observed_at_utc: datetime,
    accepted_at_utc: datetime,
    policy: ObservedTimePolicy,
) -> None:
    _require_aware_utc(observed_at_utc, "observed_at_utc")
    _require_aware_utc(accepted_at_utc, "accepted_at_utc")
    if observed_at_utc < accepted_at_utc - policy.maximum_past_skew:
        raise ObservedTimeSkewError(policy.policy_id)
    if observed_at_utc > accepted_at_utc + policy.maximum_future_skew:
        raise ObservedTimeSkewError(policy.policy_id)


def _require_aware_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must use UTC offset +00:00")


__all__ = [
    "AcceptanceTimeSource",
    "CONVERSION_INTENT_TIME_POLICY",
    "DOWNSTREAM_OUTCOME_TIME_POLICY",
    "FEEDBACK_TIME_POLICY",
    "ObservedTimePolicy",
    "ObservedTimeSkewError",
    "PRESENTATION_TIME_POLICY",
    "REVIEW_DECISION_TIME_POLICY",
    "require_observed_time_within_policy",
]
