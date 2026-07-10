from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class IdeaLifecycleStatus(StrEnum):
    DETECTED = "detected"
    GENERATED = "generated"
    ENRICHED = "enriched"
    SCORED = "scored"
    GOVERNANCE_CHECKED = "governance_checked"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED_BY_ADVISOR = "reviewed_by_advisor"
    APPROVED = "approved"
    CONVERTED_TO_PROPOSAL = "converted_to_proposal"
    CONVERTED_TO_MANAGE_REVIEW = "converted_to_manage_review"
    CONVERTED_TO_REPORT = "converted_to_report"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"
    CLOSED = "closed"


class ReviewPosture(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    ADVISOR_REVIEW_REQUIRED = "advisor_review_required"
    ADVISOR_REVIEWED = "advisor_reviewed"
    APPROVED_FOR_CONVERSION = "approved_for_conversion"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"
    NO_ACTION = "no_action"
    PM_REVIEW_REQUIRED = "pm_review_required"
    COMPLIANCE_REVIEW_REQUIRED = "compliance_review_required"


CANDIDATE_STATE_POLICY_VERSION = "idea-candidate-state-v1"

_DISCOVERY_POSTURES = frozenset(
    {
        ReviewPosture.NOT_REVIEWED,
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    }
)

REVIEWABLE_LIFECYCLE_STATUSES = frozenset(
    {
        IdeaLifecycleStatus.GENERATED,
        IdeaLifecycleStatus.ENRICHED,
        IdeaLifecycleStatus.SCORED,
        IdeaLifecycleStatus.GOVERNANCE_CHECKED,
        IdeaLifecycleStatus.READY_FOR_REVIEW,
    }
)

_ALLOWED_POSTURES_BY_LIFECYCLE: dict[IdeaLifecycleStatus, frozenset[ReviewPosture]] = {
    IdeaLifecycleStatus.DETECTED: _DISCOVERY_POSTURES,
    IdeaLifecycleStatus.GENERATED: _DISCOVERY_POSTURES,
    IdeaLifecycleStatus.ENRICHED: _DISCOVERY_POSTURES,
    IdeaLifecycleStatus.SCORED: _DISCOVERY_POSTURES,
    IdeaLifecycleStatus.GOVERNANCE_CHECKED: _DISCOVERY_POSTURES,
    IdeaLifecycleStatus.READY_FOR_REVIEW: frozenset(
        {
            ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            ReviewPosture.PM_REVIEW_REQUIRED,
            ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
            ReviewPosture.SUPPRESSED,
        }
    ),
    IdeaLifecycleStatus.REVIEWED_BY_ADVISOR: frozenset(
        {
            ReviewPosture.ADVISOR_REVIEWED,
            ReviewPosture.PM_REVIEW_REQUIRED,
            ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
            ReviewPosture.SUPPRESSED,
        }
    ),
    IdeaLifecycleStatus.APPROVED: frozenset({ReviewPosture.APPROVED_FOR_CONVERSION}),
    IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL: frozenset({ReviewPosture.APPROVED_FOR_CONVERSION}),
    IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW: frozenset(
        {ReviewPosture.APPROVED_FOR_CONVERSION}
    ),
    IdeaLifecycleStatus.CONVERTED_TO_REPORT: frozenset({ReviewPosture.APPROVED_FOR_CONVERSION}),
    IdeaLifecycleStatus.ACCEPTED: frozenset({ReviewPosture.APPROVED_FOR_CONVERSION}),
    IdeaLifecycleStatus.REJECTED: frozenset({ReviewPosture.REJECTED}),
    IdeaLifecycleStatus.EXPIRED: frozenset({ReviewPosture.NO_ACTION}),
    IdeaLifecycleStatus.EXECUTED: frozenset({ReviewPosture.APPROVED_FOR_CONVERSION}),
    IdeaLifecycleStatus.CLOSED: frozenset({ReviewPosture.NO_ACTION}),
}

ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE: Mapping[IdeaLifecycleStatus, frozenset[ReviewPosture]] = (
    MappingProxyType(_ALLOWED_POSTURES_BY_LIFECYCLE)
)

_NORMALIZED_TRANSITION_POSTURES: Mapping[IdeaLifecycleStatus, ReviewPosture] = MappingProxyType(
    {
        IdeaLifecycleStatus.REVIEWED_BY_ADVISOR: ReviewPosture.ADVISOR_REVIEWED,
        IdeaLifecycleStatus.APPROVED: ReviewPosture.APPROVED_FOR_CONVERSION,
        IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL: ReviewPosture.APPROVED_FOR_CONVERSION,
        IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW: ReviewPosture.APPROVED_FOR_CONVERSION,
        IdeaLifecycleStatus.CONVERTED_TO_REPORT: ReviewPosture.APPROVED_FOR_CONVERSION,
        IdeaLifecycleStatus.ACCEPTED: ReviewPosture.APPROVED_FOR_CONVERSION,
        IdeaLifecycleStatus.REJECTED: ReviewPosture.REJECTED,
        IdeaLifecycleStatus.EXPIRED: ReviewPosture.NO_ACTION,
        IdeaLifecycleStatus.EXECUTED: ReviewPosture.APPROVED_FOR_CONVERSION,
        IdeaLifecycleStatus.CLOSED: ReviewPosture.NO_ACTION,
    }
)

_DEFAULT_TRANSITION_POSTURES: Mapping[IdeaLifecycleStatus, ReviewPosture] = MappingProxyType(
    {IdeaLifecycleStatus.READY_FOR_REVIEW: ReviewPosture.ADVISOR_REVIEW_REQUIRED}
)


class InvalidCandidateState(ValueError):
    code = "candidate_state_conflict"

    def __init__(
        self,
        *,
        candidate_id: str,
        lifecycle_status: IdeaLifecycleStatus,
        review_posture: ReviewPosture,
    ) -> None:
        super().__init__(
            "Idea candidate lifecycle and review posture are incompatible under "
            f"{CANDIDATE_STATE_POLICY_VERSION}: "
            f"{lifecycle_status.value}/{review_posture.value}"
        )
        self.candidate_id = candidate_id
        self.lifecycle_status = lifecycle_status
        self.review_posture = review_posture
        self.policy_version = CANDIDATE_STATE_POLICY_VERSION


def candidate_state_is_compatible(
    lifecycle_status: IdeaLifecycleStatus,
    review_posture: ReviewPosture,
) -> bool:
    return review_posture in ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE[lifecycle_status]


def validate_candidate_state(
    *,
    candidate_id: str,
    lifecycle_status: IdeaLifecycleStatus,
    review_posture: ReviewPosture,
) -> None:
    if not candidate_state_is_compatible(lifecycle_status, review_posture):
        raise InvalidCandidateState(
            candidate_id=candidate_id,
            lifecycle_status=lifecycle_status,
            review_posture=review_posture,
        )


def review_posture_for_transition(
    *,
    candidate_id: str,
    current_posture: ReviewPosture,
    target_status: IdeaLifecycleStatus,
) -> ReviewPosture:
    normalized = _NORMALIZED_TRANSITION_POSTURES.get(target_status)
    if normalized is not None:
        return normalized
    if current_posture in ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE[target_status]:
        return current_posture
    default_posture = _DEFAULT_TRANSITION_POSTURES.get(target_status)
    if default_posture is not None:
        return default_posture
    raise InvalidCandidateState(
        candidate_id=candidate_id,
        lifecycle_status=target_status,
        review_posture=current_posture,
    )
