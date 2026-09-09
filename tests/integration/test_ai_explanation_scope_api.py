from __future__ import annotations

import pytest

import app.api.ai_explanation_generation as ai_explanation_generation_api
from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_ai_governance_api import (
    _FakeGenerationRuntime,
    ai_headers,
    ai_request_payload,
    generation_headers,
    generation_payload,
    persisted_candidate_id,
    transition_candidate_to_review_ready,
)
from tests.support.http import managed_test_client


_SCOPE_VARIANTS = (
    ("X-Caller-Tenant-Ids", "tenant-other"),
    ("X-Caller-Book-Ids", "book-other"),
    ("X-Caller-Portfolio-Ids", "PORTFOLIO_OTHER"),
    ("X-Caller-Client-Ids", "client-other"),
    ("X-Caller-Tenant-Ids", None),
    ("X-Caller-Book-Ids", None),
    ("X-Caller-Portfolio-Ids", None),
    ("X-Caller-Client-Ids", None),
)


def _change_scope_header(
    headers: dict[str, str],
    scope_header: str,
    scope_value: str | None,
) -> None:
    if scope_value is None:
        headers.pop(scope_header)
    else:
        headers[scope_header] = scope_value


@pytest.mark.parametrize(("scope_header", "scope_value"), _SCOPE_VARIANTS)
def test_ai_explanation_api_rejects_incomplete_or_mismatched_candidate_scope_before_write(
    scope_header: str,
    scope_value: str | None,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-ai-scope-{scope_header}-{scope_value}",
    )
    headers = ai_headers(idempotency_key=f"ai-scope-{scope_header}-{scope_value}")
    _change_scope_header(headers, scope_header, scope_value)

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate",
        json=ai_request_payload(request_id=f"ai-scope-{scope_header}-{scope_value}"),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.ai_explanation_lineage_records == ()


@pytest.mark.parametrize("route", ("evaluate", "generate"))
def test_ai_explanation_api_rejects_malformed_scope_as_invalid_request(route: str) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key=f"seed-ai-malformed-{route}")
    headers = ai_headers() if route == "evaluate" else generation_headers()
    headers["X-Caller-Book-Ids"] = "book-advisor-001, "
    endpoint = (
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations/evaluate"
        if route == "evaluate"
        else f"/api/v1/idea-candidates/{candidate_id}/ai-explanations"
    )
    payload = ai_request_payload() if route == "evaluate" else generation_payload()

    response = client.post(endpoint, json=payload, headers=headers)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.ai_explanation_lineage_records == ()


@pytest.mark.parametrize(("scope_header", "scope_value"), _SCOPE_VARIANTS)
def test_ai_generation_api_rejects_incomplete_or_mismatched_scope_before_owner_io(
    monkeypatch: pytest.MonkeyPatch,
    scope_header: str,
    scope_value: str | None,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-generation-scope-{scope_header}-{scope_value}",
    )
    transition_candidate_to_review_ready(client, candidate_id)
    runtime = _FakeGenerationRuntime()
    monkeypatch.setattr(
        ai_explanation_generation_api,
        "get_lotus_ai_workflow_runtime",
        lambda: runtime,
    )
    headers = generation_headers(idempotency_key=f"generation-scope-{scope_header}-{scope_value}")
    _change_scope_header(headers, scope_header, scope_value)

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/ai-explanations",
        json=generation_payload(request_id=f"generation-scope-{scope_header}-{scope_value}"),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert runtime.requests == []
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.ai_explanation_lineage_records == ()
