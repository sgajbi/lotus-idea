from __future__ import annotations

from typing import Any

from tests.support.http import ManagedTestClient, managed_test_client

from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_candidate_detail_api import detail_headers
from tests.integration.test_review_workflow_api import (
    approve_candidate_for_conversion,
    conversion_intent_headers,
    conversion_intent_payload,
    conversion_outcome_headers,
    persisted_candidate_id,
)


def setup_conversion_intent(client: ManagedTestClient, seed: str) -> tuple[str, str]:
    candidate_id = persisted_candidate_id(client, idempotency_key=f"seed-{seed}")
    approve_candidate_for_conversion(client, candidate_id)
    intent_id = f"intent-{seed}"
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=intent_id),
        headers=conversion_intent_headers(f"intent-{seed}"),
    )
    assert response.status_code == 200
    return candidate_id, intent_id


def outcome_payload(
    *,
    outcome_id: str,
    status: str,
    version: int,
    minute: int,
    supersedes: str | None = None,
    correction_reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "conversionOutcomeId": outcome_id,
        "status": status,
        "sourceSystem": "lotus-report",
        "sourceEventVersion": version,
        "recordedAtUtc": f"2026-06-21T10:{minute:02d}:00Z",
    }
    if status in {"accepted", "completed"}:
        payload["downstreamReference"] = "report-evidence-pack-001"
    if supersedes is not None:
        payload["supersedesConversionOutcomeId"] = supersedes
        payload["correctionReason"] = correction_reason
    return payload


def test_conversion_outcome_api_replays_identity_and_rejects_changed_source_fact() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    _, intent_id = setup_conversion_intent(client, "outcome-identity")
    route = f"/api/v1/conversion-intents/{intent_id}/outcomes"
    request = outcome_payload(
        outcome_id="source-event-identity-001",
        status="accepted",
        version=1,
        minute=20,
    )

    first = client.post(
        route,
        json=request,
        headers=conversion_outcome_headers("outcome-identity-first"),
    )
    before_retry = get_idea_repository().snapshot()
    replayed = client.post(
        route,
        json=request,
        headers=conversion_outcome_headers("outcome-identity-retry"),
    )
    changed = dict(request)
    changed["status"] = "rejected"
    changed.pop("downstreamReference")
    conflict = client.post(
        route,
        json=changed,
        headers=conversion_outcome_headers("outcome-identity-changed"),
    )
    after_retry = get_idea_repository().snapshot()

    assert first.status_code == 200
    assert first.json()["conversionOutcome"]["sourceEventVersion"] == 1
    assert replayed.status_code == 200
    assert replayed.json()["conversionOutcome"] is None
    assert replayed.json()["persistence"]["decision"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "conversion_outcome_conflict"
    assert after_retry.candidate_records == before_retry.candidate_records
    assert after_retry.outbox_events == before_retry.outbox_events


def test_conversion_outcome_api_enforces_progression_and_append_only_correction() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id, intent_id = setup_conversion_intent(client, "outcome-lifecycle")
    route = f"/api/v1/conversion-intents/{intent_id}/outcomes"

    rejected_id = "source-event-rejected-001"
    rejected = client.post(
        route,
        json=outcome_payload(
            outcome_id=rejected_id,
            status="rejected",
            version=1,
            minute=20,
        ),
        headers=conversion_outcome_headers("outcome-lifecycle-rejected"),
    )
    contradiction = client.post(
        route,
        json=outcome_payload(
            outcome_id="source-event-unlinked-002",
            status="accepted",
            version=2,
            minute=21,
        ),
        headers=conversion_outcome_headers("outcome-lifecycle-unlinked"),
    )
    corrected = client.post(
        route,
        json=outcome_payload(
            outcome_id="source-event-correction-002",
            status="accepted",
            version=2,
            minute=21,
            supersedes=rejected_id,
            correction_reason="Source corrected an erroneous rejection",
        ),
        headers=conversion_outcome_headers("outcome-lifecycle-corrected"),
    )
    completed = client.post(
        route,
        json=outcome_payload(
            outcome_id="source-event-completed-003",
            status="completed",
            version=3,
            minute=22,
        ),
        headers=conversion_outcome_headers("outcome-lifecycle-completed"),
    )
    detail = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=detail_headers(portfolio_ids="PB_SG_GLOBAL_BAL_001"),
    )

    assert rejected.status_code == 200
    assert contradiction.status_code == 409
    assert contradiction.json()["code"] == "conversion_outcome_conflict"
    assert corrected.status_code == 200
    assert corrected.json()["conversionOutcome"]["supersedesConversionOutcomeId"] == rejected_id
    assert completed.status_code == 200
    assert [item["status"] for item in detail.json()["conversionOutcomes"]] == [
        "rejected",
        "accepted",
        "completed",
    ]
    assert detail.json()["currentConversionOutcomes"] == [
        {
            **detail.json()["conversionOutcomes"][-1],
        }
    ]


def test_conversion_outcome_openapi_separates_conflicts_and_current_posture() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/conversion-intents/{conversionIntentId}/outcomes"]["post"]
    problem_examples = operation["responses"]["409"]["content"]["application/problem+json"][
        "examples"
    ]
    candidate_detail = schema["components"]["schemas"]["CandidateDetailResponse"]

    assert set(problem_examples) == {
        "idempotency_conflict",
        "conversion_outcome_conflict",
    }
    assert problem_examples["conversion_outcome_conflict"]["value"]["status"] == 409
    assert "currentConversionOutcomes" in candidate_detail["required"]
