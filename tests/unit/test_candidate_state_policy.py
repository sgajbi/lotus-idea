from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain import (
    ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE,
    CANDIDATE_STATE_POLICY_VERSION,
    IdeaLifecycleStatus,
    InvalidCandidateState,
    ReviewPosture,
    candidate_state_is_compatible,
    transition_candidate,
)
from app.infrastructure.candidate_state_sql import candidate_record_state_compatibility_sql
from app.infrastructure.postgres_codecs import idea_candidate_from_json, idea_candidate_to_json
from tests.unit.test_postgres_repository import high_cash_candidate


EXPECTED_GOLDEN_MATRIX = {
    IdeaLifecycleStatus.DETECTED: {
        ReviewPosture.NOT_REVIEWED,
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.GENERATED: {
        ReviewPosture.NOT_REVIEWED,
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.ENRICHED: {
        ReviewPosture.NOT_REVIEWED,
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.SCORED: {
        ReviewPosture.NOT_REVIEWED,
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.GOVERNANCE_CHECKED: {
        ReviewPosture.NOT_REVIEWED,
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.READY_FOR_REVIEW: {
        ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.REVIEWED_BY_ADVISOR: {
        ReviewPosture.ADVISOR_REVIEWED,
        ReviewPosture.PM_REVIEW_REQUIRED,
        ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        ReviewPosture.SUPPRESSED,
    },
    IdeaLifecycleStatus.APPROVED: {ReviewPosture.APPROVED_FOR_CONVERSION},
    IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL: {ReviewPosture.APPROVED_FOR_CONVERSION},
    IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW: {ReviewPosture.APPROVED_FOR_CONVERSION},
    IdeaLifecycleStatus.CONVERTED_TO_REPORT: {ReviewPosture.APPROVED_FOR_CONVERSION},
    IdeaLifecycleStatus.ACCEPTED: {ReviewPosture.APPROVED_FOR_CONVERSION},
    IdeaLifecycleStatus.REJECTED: {ReviewPosture.REJECTED},
    IdeaLifecycleStatus.EXPIRED: {ReviewPosture.NO_ACTION},
    IdeaLifecycleStatus.EXECUTED: {ReviewPosture.APPROVED_FOR_CONVERSION},
    IdeaLifecycleStatus.CLOSED: {ReviewPosture.NO_ACTION},
}


def test_candidate_state_policy_is_exhaustive_and_matches_golden_matrix() -> None:
    assert CANDIDATE_STATE_POLICY_VERSION == "idea-candidate-state-v1"
    assert set(ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE) == set(IdeaLifecycleStatus)
    assert {
        lifecycle: set(postures)
        for lifecycle, postures in ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE.items()
    } == EXPECTED_GOLDEN_MATRIX

    for lifecycle in IdeaLifecycleStatus:
        for posture in ReviewPosture:
            assert candidate_state_is_compatible(lifecycle, posture) is (
                posture in EXPECTED_GOLDEN_MATRIX[lifecycle]
            )


def test_candidate_construction_and_rehydration_reject_contradictory_state() -> None:
    valid_candidate = high_cash_candidate()
    with pytest.raises(InvalidCandidateState) as construction_error:
        replace(
            valid_candidate,
            lifecycle_status=IdeaLifecycleStatus.CLOSED,
            review_posture=ReviewPosture.PM_REVIEW_REQUIRED,
        )

    payload = idea_candidate_to_json(valid_candidate)
    payload["lifecycle_status"] = IdeaLifecycleStatus.CLOSED.value
    payload["review_posture"] = ReviewPosture.PM_REVIEW_REQUIRED.value
    with pytest.raises(InvalidCandidateState) as rehydration_error:
        idea_candidate_from_json(payload)

    for error in (construction_error.value, rehydration_error.value):
        assert error.code == "candidate_state_conflict"
        assert error.policy_version == CANDIDATE_STATE_POLICY_VERSION
        assert error.lifecycle_status is IdeaLifecycleStatus.CLOSED
        assert error.review_posture is ReviewPosture.PM_REVIEW_REQUIRED


def test_terminal_transitions_normalize_review_posture_to_non_actionable_state() -> None:
    candidate = high_cash_candidate()

    expired = transition_candidate(candidate, IdeaLifecycleStatus.EXPIRED)
    closed = transition_candidate(candidate, IdeaLifecycleStatus.CLOSED)

    assert expired.review_posture is ReviewPosture.NO_ACTION
    assert closed.review_posture is ReviewPosture.NO_ACTION
    assert expired.ready_for_conversion is False
    assert closed.ready_for_conversion is False


def test_postgres_compatibility_predicate_is_derived_from_every_domain_pair() -> None:
    predicate = candidate_record_state_compatibility_sql()

    assert "candidate_json->>'lifecycle_status'" in predicate
    assert "candidate_json->>'review_posture'" in predicate
    for lifecycle, postures in EXPECTED_GOLDEN_MATRIX.items():
        assert f"lifecycle_status = '{lifecycle.value}'" in predicate
        for posture in postures:
            assert f"'{posture.value}'" in predicate
