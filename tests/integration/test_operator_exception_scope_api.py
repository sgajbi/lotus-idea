from __future__ import annotations

from datetime import UTC, datetime

import pytest

import app.api.review_queue.operator_exceptions as review_queue_exceptions_api
from app.main import app
from app.runtime import trusted_clock_state
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_api_operation_events import capture_operation_events
from tests.integration.test_review_queue_api import operator_exception_headers, persist_candidate
from tests.support.fixed_utc_clock import FixedUtcClock
from tests.support.http import managed_test_client


@pytest.fixture(autouse=True)
def _review_queue_snapshot_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trusted_clock_state,
        "_TRUSTED_CLOCK",
        FixedUtcClock(datetime(2026, 6, 21, 10, 10, tzinfo=UTC)),
    )


def test_operator_exception_queue_counts_only_candidates_within_caller_scope() -> None:
    """A fully scoped operator for another portfolio must not learn the estate-wide count."""

    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    persist_candidate(
        client,
        cash_weight="0.18",
        suffix="-exception-scope",
        idempotency_key="seed-exception-scope-001",
    )

    in_scope = client.get(
        "/api/v1/review-queues/operator/exceptions?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=operator_exception_headers(),
    )
    foreign_scope = client.get(
        "/api/v1/review-queues/operator/exceptions?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=operator_exception_headers(portfolio_ids="PB_SG_OTHER_002"),
    )

    assert in_scope.status_code == 200
    assert foreign_scope.status_code == 200
    assert _advisor_count(in_scope.json()) == 1
    assert _advisor_count(foreign_scope.json()) == 0
    assert foreign_scope.json()["totalExceptionCount"] == 0


@pytest.mark.parametrize(
    "missing_header",
    ("X-Caller-Tenant-Ids", "X-Caller-Book-Ids", "X-Caller-Portfolio-Ids", "X-Caller-Client-Ids"),
)
def test_operator_exception_queue_requires_complete_caller_scope(missing_header: str) -> None:
    """Operator exception counts are scoped reads: an absent dimension is refused, never widened.

    Before this guard an absent caller dimension acted as a wildcard, so a query value for
    that dimension was accepted against nothing and the aggregate spanned every tenant.
    """

    reset_idea_repository_for_tests()
    headers = operator_exception_headers()
    headers.pop(missing_header)

    unscoped = managed_test_client(app).get(
        "/api/v1/review-queues/operator/exceptions",
        headers=headers,
    )
    widened = managed_test_client(app).get(
        "/api/v1/review-queues/operator/exceptions?portfolioId=PB_SG_OTHER_002",
        headers=headers,
    )

    assert unscoped.status_code == 403
    assert unscoped.json()["code"] == "permission_denied"
    assert widened.status_code == 403
    assert widened.json()["code"] == "permission_denied"


def test_operator_exception_queue_without_scope_emits_permission_denied_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generic operator role without complete scope is refused before any repository read."""

    reset_idea_repository_for_tests()
    events = capture_operation_events(monkeypatch, review_queue_exceptions_api)

    response = managed_test_client(app).get(
        "/api/v1/review-queues/operator/exceptions",
        headers={
            "X-Caller-Subject": "platform-operator",
            "X-Caller-Roles": "operator",
            "X-Caller-Capabilities": "idea.review.queue.exceptions.read",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert events == [
        (
            "review_queue_exception_read",
            "permission_denied",
            "lotus-idea",
            False,
            "permission_denied",
        ),
    ]


def _advisor_count(payload: dict[str, object]) -> int:
    audiences = payload["audiences"]
    assert isinstance(audiences, list)
    return int(
        next(audience for audience in audiences if audience["audience"] == "advisor")[
            "candidateSnapshotCount"
        ]
    )
