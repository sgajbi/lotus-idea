from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture
from tests.support.http import ManagedTestClient, managed_test_client

import app.api.candidate_detail as candidate_detail_api
import app.api.idea_signals as idea_signals_api
import app.api.review_queue.routes as review_queues_api
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.support.source_revision import lotus_core_source_ref

RequestContextEventCall = tuple[str, str | None, str | None]


def _high_cash_payload(*, suffix: str) -> dict[str, Any]:
    def source_ref(product_id: str) -> dict[str, Any]:
        return lotus_core_source_ref(product_id, suffix=suffix)

    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1"),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1"),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            "cashflowProjectionRef": source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        },
        "accessScope": {
            "tenantId": "tenant-private-bank-sg",
            "bookId": "book-advisor-001",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "clientId": "client-001",
        },
        "entitlementAllowed": True,
    }


def _persistence_headers(idempotency_key: str) -> dict[str, str]:
    return {
        "X-Caller-Subject": "signal-ingestion-worker",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "X-Correlation-Id": "corr-operation-persist-api",
        "X-Trace-Id": "trace-operation-persist-api",
        "Idempotency-Key": idempotency_key,
    }


def _detail_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.candidate.detail.read",
        "X-Correlation-Id": "corr-operation-detail-api",
        "X-Trace-Id": "trace-operation-detail-api",
    }


def _queue_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.review.queue.read",
        "X-Correlation-Id": "corr-operation-queue-api",
        "X-Trace-Id": "trace-operation-queue-api",
    }


def _capture_request_context_events(
    monkeypatch: pytest.MonkeyPatch,
    module: Any,
) -> list[RequestContextEventCall]:
    events: list[RequestContextEventCall] = []

    def capture_foundation_event(
        operation: Any,
        _outcome: Any,
        **fields: Any,
    ) -> None:
        events.append(
            (
                operation.value,
                fields.get("correlation_id"),
                fields.get("trace_id"),
            )
        )

    monkeypatch.setattr(module, "emit_foundation_operation_event", capture_foundation_event)
    return events


def _persist_candidate(
    client: ManagedTestClient,
    *,
    suffix: str,
    idempotency_key: str,
) -> str:
    response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(suffix=suffix),
        headers=_persistence_headers(idempotency_key),
    )
    assert response.status_code == 200
    return str(response.json()["persistence"]["candidateId"])


def test_candidate_persistence_detail_and_queue_events_retain_request_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    persistence_events = _capture_request_context_events(monkeypatch, idea_signals_api)

    persistence_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_high_cash_payload(suffix="-request-context"),
        headers=_persistence_headers("operation-persist-request-context-001"),
    )

    assert persistence_response.status_code == 200
    candidate_id = persistence_response.json()["persistence"]["candidateId"]
    assert persistence_response.headers["X-Correlation-Id"] == "corr-operation-persist-api"
    assert persistence_response.headers["X-Trace-Id"] == "trace-operation-persist-api"
    assert persistence_events == [
        (
            "candidate_persistence",
            "corr-operation-persist-api",
            "trace-operation-persist-api",
        )
    ]

    detail_events = _capture_request_context_events(monkeypatch, candidate_detail_api)
    detail_response = client.get(
        f"/api/v1/idea-candidates/{candidate_id}",
        headers=_detail_headers(),
    )

    assert detail_response.status_code == 200
    assert detail_response.headers["X-Correlation-Id"] == "corr-operation-detail-api"
    assert detail_response.headers["X-Trace-Id"] == "trace-operation-detail-api"
    assert detail_events == [
        (
            "candidate_detail_read",
            "corr-operation-detail-api",
            "trace-operation-detail-api",
        )
    ]

    queue_events = _capture_request_context_events(monkeypatch, review_queues_api)
    queue_response = client.get(
        "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
        headers=_queue_headers(),
    )

    assert queue_response.status_code == 200
    assert queue_response.headers["X-Correlation-Id"] == "corr-operation-queue-api"
    assert queue_response.headers["X-Trace-Id"] == "trace-operation-queue-api"
    assert queue_events == [
        (
            "review_queue_read",
            "corr-operation-queue-api",
            "trace-operation-queue-api",
        )
    ]


def test_structured_operation_logs_join_to_request_response_context(
    caplog: LogCaptureFixture,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        persistence_response = client.post(
            "/api/v1/idea-signals/high-cash/evaluate-and-persist",
            json=_high_cash_payload(suffix="-structured-request-context"),
            headers=_persistence_headers("operation-persist-structured-context-001"),
        )
        candidate_id = persistence_response.json()["persistence"]["candidateId"]
        detail_response = client.get(
            f"/api/v1/idea-candidates/{candidate_id}",
            headers=_detail_headers(),
        )
        queue_response = client.get(
            "/api/v1/review-queues/advisor?evaluatedAtUtc=2026-06-21T10:10:00Z",
            headers=_queue_headers(),
        )

    expected_context_by_operation = {
        "candidate_persistence": (
            persistence_response.headers["X-Correlation-Id"],
            persistence_response.headers["X-Trace-Id"],
        ),
        "candidate_detail_read": (
            detail_response.headers["X-Correlation-Id"],
            detail_response.headers["X-Trace-Id"],
        ),
        "review_queue_read": (
            queue_response.headers["X-Correlation-Id"],
            queue_response.headers["X-Trace-Id"],
        ),
    }
    operation_payloads = {
        payload["operation"]: payload
        for record in caplog.records
        if record.name == "lotus-idea"
        for payload in [json.loads(record.message)]
        if payload.get("operation") in expected_context_by_operation
    }

    assert operation_payloads.keys() == expected_context_by_operation.keys()
    for operation, (correlation_id, trace_id) in expected_context_by_operation.items():
        assert operation_payloads[operation]["correlation_id"] == correlation_id
        assert operation_payloads[operation]["trace_id"] == trace_id
        assert candidate_id not in str(operation_payloads[operation])


@pytest.mark.parametrize(
    ("request_headers", "unsafe_values"),
    [
        ({}, ()),
        (
            {
                "X-Correlation-Id": "PB_SG_GLOBAL_BAL_001",
                "X-Trace-Id": "client_secret:abc123",
            },
            ("PB_SG_GLOBAL_BAL_001", "client_secret:abc123"),
        ),
    ],
)
def test_candidate_detail_log_uses_generated_sanitized_request_context(
    monkeypatch: pytest.MonkeyPatch,
    request_headers: dict[str, str],
    unsafe_values: tuple[str, ...],
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = _persist_candidate(
        client,
        suffix="-generated-request-context",
        idempotency_key="operation-persist-generated-context-001",
    )
    events = _capture_request_context_events(monkeypatch, candidate_detail_api)
    headers = _detail_headers()
    headers.pop("X-Correlation-Id")
    headers.pop("X-Trace-Id")
    headers.update(request_headers)

    response = client.get(f"/api/v1/idea-candidates/{candidate_id}", headers=headers)

    assert response.status_code == 200
    correlation_id = response.headers["X-Correlation-Id"]
    trace_id = response.headers["X-Trace-Id"]
    assert correlation_id.startswith("corr-")
    assert trace_id.startswith("trace-")
    assert events == [("candidate_detail_read", correlation_id, trace_id)]
    for unsafe_value in unsafe_values:
        assert unsafe_value not in repr(events)
