from __future__ import annotations

import pytest
from tests.integration.test_api_operation_events import (
    capture_operation_events,
    queue_headers,
)
from tests.support.http import managed_test_client

import app.api.review_queue.routes as review_queues_api
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests


def test_role_specific_review_queues_emit_operation_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    events = capture_operation_events(monkeypatch, review_queues_api)

    portfolio_manager_response = client.get(
        "/api/v1/review-queues/portfolio-manager",
        headers=queue_headers(
            subject="portfolio-manager-001",
            role="portfolio_manager",
            capability="idea.review.queue.portfolio-manager.read",
        ),
    )
    compliance_response = client.get(
        "/api/v1/review-queues/compliance",
        headers=queue_headers(
            subject="compliance-001",
            role="compliance",
            capability="idea.review.queue.compliance.read",
        ),
    )

    assert portfolio_manager_response.status_code == 200
    assert compliance_response.status_code == 200
    assert events == [
        ("review_queue_read", "accepted", "lotus-idea", False, None),
        ("review_queue_read", "accepted", "lotus-idea", False, None),
    ]
