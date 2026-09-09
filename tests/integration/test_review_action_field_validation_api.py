from __future__ import annotations

from typing import Any

import pytest
from tests.support.http import managed_test_client
from tests.support.review_authority_api import record_workbench_presentation

from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    approve_review_payload,
    persisted_candidate_id,
    review_headers,
    transition_candidate_to_review_ready,
)


@pytest.mark.parametrize(
    ("action", "action_specific_fields"),
    (
        ("approve_for_conversion", {"suppressionReason": "manual_suppression"}),
        ("reject", {"snoozedUntilUtc": "2026-06-21T11:00:00Z"}),
        ("no_action", {"suppressionReason": "manual_suppression"}),
        ("escalate_to_pm", {"snoozedUntilUtc": "2026-06-21T11:00:00Z"}),
        (
            "suppress",
            {
                "suppressionReason": "manual_suppression",
                "snoozedUntilUtc": "2026-06-21T11:00:00Z",
            },
        ),
        (
            "snooze",
            {
                "suppressionReason": "manual_suppression",
                "snoozedUntilUtc": "2026-06-21T11:00:00Z",
            },
        ),
    ),
)
def test_review_action_api_rejects_action_irrelevant_fields_without_side_effects(
    action: str,
    action_specific_fields: dict[str, str],
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-review-irrelevant-{action}",
    )
    transition_candidate_to_review_ready(client, candidate_id)
    request_payload = approve_review_payload(candidate_id)
    request_payload.update(
        {
            "reviewId": f"review-irrelevant-{action}",
            "action": action,
            **action_specific_fields,
        }
    )
    repository = get_idea_repository()
    before = repository.snapshot()

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=request_payload,
        headers=review_headers(f"review-action-irrelevant-{action}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert repository.snapshot() == before


def test_review_action_api_accepts_and_exactly_replays_valid_snooze_fields() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-snooze-001")
    request_payload = _snooze_review_payload(candidate_id)
    headers = review_headers("review-action-snooze-001")

    accepted = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=request_payload,
        headers=headers,
    )
    replayed = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=request_payload,
        headers=headers,
    )

    assert accepted.status_code == 200
    assert replayed.status_code == 200
    assert accepted.json()["reviewDecision"]["suppressionReason"] is None
    assert accepted.json()["reviewDecision"]["snoozedUntilUtc"] == "2026-06-21T11:00:00Z"
    assert replayed.json()["reviewDecision"] == accepted.json()["reviewDecision"]
    assert replayed.json()["persistence"]["decision"] == "replayed"


def _snooze_review_payload(candidate_id: str) -> dict[str, Any]:
    return {
        "reviewId": "review-snooze-001",
        "action": "snooze",
        "reasonCodes": ["review_required"],
        "decidedAtUtc": "2026-06-21T10:05:00Z",
        "snoozedUntilUtc": "2026-06-21T11:00:00Z",
        **record_workbench_presentation(candidate_id),
    }
