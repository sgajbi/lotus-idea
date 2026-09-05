from __future__ import annotations

import pytest
from tests.integration.test_api_operation_events import (
    ai_headers,
    capture_operation_events,
    persist_candidate,
    transition_candidate,
)
from tests.support.http import managed_test_client

import app.api.ai_explanation_generation as ai_explanation_generation_api
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests


def test_ai_explanation_generation_api_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    events = capture_operation_events(monkeypatch, ai_explanation_generation_api)
    candidate_id = persist_candidate(
        client,
        suffix="-ai-explanation-generation",
        idempotency_key="operation-persist-ai-generation-001",
    )
    for index, target_status in enumerate(
        ("enriched", "scored", "governance_checked", "ready_for_review"),
        start=1,
    ):
        transition_candidate(
            client,
            candidate_id,
            target_status=target_status,
            idempotency_key=f"operation-ai-generation-{target_status}-001",
            transition_id=f"operation-ai-generation-{target_status}-001",
            minute=index,
        )

    def runtime_not_configured() -> None:
        raise RuntimeError("runtime unavailable in bounded operation-event test")

    monkeypatch.setattr(
        ai_explanation_generation_api,
        "get_lotus_ai_workflow_runtime",
        runtime_not_configured,
    )
    headers = ai_headers("operation-ai-explanation-generation-001")
    headers["X-Caller-Capabilities"] = "idea.ai-explanation.generate"
    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations",
        json={
            "requestId": "operation-ai-explanation-generation-001",
            "purpose": "advisor_rationale_draft",
            "requestedAtUtc": "2026-06-21T10:12:00Z",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "EXPLANATION_UNAVAILABLE"
    assert events == [("ai_explanation", "fallback", "lotus-idea", False, None)]
