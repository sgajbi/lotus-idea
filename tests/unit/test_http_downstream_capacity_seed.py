from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
import json

import httpx
import pytest

from app.infrastructure.http_downstream_capacity_seed import (
    MAX_RESPONSE_BYTES,
    HttpDownstreamCapacitySeed,
)


def test_adapter_calls_governed_api_sequence_with_synthetic_scope() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("evaluate-and-persist"):
            return httpx.Response(200, json={"persistence": {"candidateId": "candidate-001"}})
        return httpx.Response(200, json={"accepted": True})

    adapter = HttpDownstreamCapacitySeed(
        base_url="https://idea.example",
        timeout_seconds=2,
        base_headers={"Authorization": "Bearer transient"},
        transport=httpx.MockTransport(handle),
    )
    seeded_at = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)

    candidate_id = adapter.persist_candidate(
        seed_key="abc123", as_of_date=date(2026, 7, 11), seeded_at_utc=seeded_at
    )
    adapter.transition_candidate(
        candidate_id=candidate_id,
        seed_key="abc123",
        target_status="enriched",
        changed_at_utc=seeded_at,
    )
    adapter.approve_candidate(
        candidate_id=candidate_id, seed_key="abc123", decided_at_utc=seeded_at
    )
    adapter.record_conversion_intent(
        candidate_id=candidate_id,
        conversion_intent_id="capacity-conversion-abc123",
        seed_key="abc123",
        requested_at_utc=seeded_at,
    )
    adapter.close()

    assert candidate_id == "candidate-001"
    assert [request.url.path for request in requests] == [
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        "/api/v1/idea-candidates/candidate-001/lifecycle-transitions",
        "/api/v1/idea-candidates/candidate-001/review-actions",
        "/api/v1/idea-candidates/candidate-001/conversion-intents",
    ]
    assert all(request.headers["authorization"] == "Bearer transient" for request in requests)
    candidate_payload = json.loads(requests[0].content)
    assert candidate_payload["accessScope"] == {
        "tenantId": "capacity-synthetic-tenant",
        "bookId": "capacity-synthetic-book",
        "portfolioId": "CAPACITY_SYNTHETIC_PORTFOLIO_001",
        "clientId": "capacity-synthetic-client",
    }
    assert candidate_payload["sourceReportedCashWeight"] == "0.18"
    expected_scope_headers = {
        "x-caller-roles": "advisor",
        "x-caller-tenant-ids": "capacity-synthetic-tenant",
        "x-caller-book-ids": "capacity-synthetic-book",
        "x-caller-portfolio-ids": "CAPACITY_SYNTHETIC_PORTFOLIO_001",
        "x-caller-client-ids": "capacity-synthetic-client",
    }
    for header_name, expected_value in expected_scope_headers.items():
        assert requests[2].headers[header_name] == expected_value
        assert requests[3].headers[header_name] == expected_value
    assert requests[3].headers["x-caller-capabilities"] == "idea.conversion.intent.record"


def test_adapter_normalizes_seed_request_timestamps_to_utc_z() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("evaluate-and-persist"):
            return httpx.Response(200, json={"persistence": {"candidateId": "candidate-001"}})
        return httpx.Response(200, json={"accepted": True})

    adapter = HttpDownstreamCapacitySeed(
        base_url="https://idea.example",
        timeout_seconds=2,
        transport=httpx.MockTransport(handle),
    )
    singapore_time = datetime(2026, 7, 11, 16, 0, tzinfo=timezone(timedelta(hours=8)))

    candidate_id = adapter.persist_candidate(
        seed_key="abc123", as_of_date=date(2026, 7, 11), seeded_at_utc=singapore_time
    )
    adapter.transition_candidate(
        candidate_id=candidate_id,
        seed_key="abc123",
        target_status="ready_for_review",
        changed_at_utc=singapore_time + timedelta(minutes=1),
    )
    adapter.approve_candidate(
        candidate_id=candidate_id,
        seed_key="abc123",
        decided_at_utc=singapore_time + timedelta(minutes=2),
    )
    adapter.record_conversion_intent(
        candidate_id=candidate_id,
        conversion_intent_id="capacity-conversion-abc123",
        seed_key="abc123",
        requested_at_utc=singapore_time + timedelta(minutes=3),
    )
    adapter.close()

    assert json.loads(requests[0].content)["evaluatedAtUtc"] == "2026-07-11T08:00:00Z"
    assert json.loads(requests[1].content)["changedAtUtc"] == "2026-07-11T08:01:00Z"
    assert json.loads(requests[2].content)["decidedAtUtc"] == "2026-07-11T08:02:00Z"
    assert json.loads(requests[3].content)["requestedAtUtc"] == "2026-07-11T08:03:00Z"


@pytest.mark.parametrize(
    "operation",
    [
        lambda adapter, timestamp: adapter.persist_candidate(
            seed_key="abc123",
            as_of_date=date(2026, 7, 11),
            seeded_at_utc=timestamp,
        ),
        lambda adapter, timestamp: adapter.transition_candidate(
            candidate_id="candidate-001",
            seed_key="abc123",
            target_status="enriched",
            changed_at_utc=timestamp,
        ),
        lambda adapter, timestamp: adapter.approve_candidate(
            candidate_id="candidate-001",
            seed_key="abc123",
            decided_at_utc=timestamp,
        ),
        lambda adapter, timestamp: adapter.record_conversion_intent(
            candidate_id="candidate-001",
            conversion_intent_id="capacity-conversion-abc123",
            seed_key="abc123",
            requested_at_utc=timestamp,
        ),
    ],
)
def test_adapter_rejects_naive_seed_request_timestamps_before_http(
    operation: Callable[[HttpDownstreamCapacitySeed, datetime], object],
) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    adapter = HttpDownstreamCapacitySeed(
        base_url="https://idea.example",
        timeout_seconds=2,
        transport=httpx.MockTransport(handle),
    )

    with pytest.raises(ValueError, match="timestamp must be timezone-aware"):
        operation(adapter, datetime(2026, 7, 11, 8, 0))

    assert requests == []
    adapter.close()


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(503, json={"detail": "sensitive"}), "status 503"),
        (httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1)), "size limit"),
        (httpx.Response(200, content=b"not-json"), "invalid JSON"),
        (httpx.Response(200, json=[]), "must be an object"),
        (httpx.Response(200, json={"persistence": {}}), "missing candidateId"),
    ],
)
def test_adapter_fails_closed_on_untrusted_api_responses(
    response: httpx.Response, message: str
) -> None:
    adapter = HttpDownstreamCapacitySeed(
        base_url="https://idea.example",
        timeout_seconds=2,
        transport=httpx.MockTransport(lambda request: response),
    )

    with pytest.raises(ValueError, match=message) as captured:
        adapter.persist_candidate(
            seed_key="abc123",
            as_of_date=date(2026, 7, 11),
            seeded_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        )

    assert "sensitive" not in str(captured.value)
    adapter.close()


def test_adapter_rejects_invalid_timeout_and_sanitizes_transport_failure() -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        HttpDownstreamCapacitySeed(base_url="https://idea.example", timeout_seconds=0)

    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sensitive endpoint detail", request=request)

    adapter = HttpDownstreamCapacitySeed(
        base_url="https://idea.example",
        timeout_seconds=2,
        transport=httpx.MockTransport(fail),
    )
    with pytest.raises(ValueError, match="API request failed") as captured:
        adapter.persist_candidate(
            seed_key="abc123",
            as_of_date=date(2026, 7, 11),
            seeded_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
        )

    assert "sensitive" not in str(captured.value)
    adapter.close()
