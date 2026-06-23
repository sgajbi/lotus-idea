from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.candidate_lifecycle import ApplyCandidateLifecycleTransitionCommand
from app.domain import IdeaLifecycleStatus


CHANGED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def lifecycle_command(**overrides: object) -> ApplyCandidateLifecycleTransitionCommand:
    values: dict[str, Any] = {
        "candidate_id": "idea-candidate-001",
        "transition_id": "transition-001",
        "target_status": IdeaLifecycleStatus.READY_FOR_REVIEW,
        "changed_at_utc": CHANGED_AT,
        "reason_codes": ("review_required",),
        "actor_subject": "advisor-001",
        "idempotency_key": "lifecycle-transition-001",
    }
    values.update(overrides)
    return ApplyCandidateLifecycleTransitionCommand(**values)


@pytest.mark.parametrize(
    ("field_name", "bad_value", "message"),
    [
        ("candidate_id", " ", "candidate_id is required"),
        ("transition_id", " ", "transition_id is required"),
        ("actor_subject", " ", "actor_subject is required"),
        ("idempotency_key", " ", "idempotency_key is required"),
        ("reason_codes", (), "reason_codes is required"),
        ("reason_codes", ("review_required", " "), "reason_codes cannot contain blank values"),
        (
            "changed_at_utc",
            datetime(2026, 6, 21, 10, 10),
            "changed_at_utc must be timezone-aware",
        ),
    ],
)
def test_candidate_lifecycle_transition_command_rejects_invalid_inputs(
    field_name: str,
    bad_value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        lifecycle_command(**{field_name: bad_value})
