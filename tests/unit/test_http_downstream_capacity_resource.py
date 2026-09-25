from __future__ import annotations

import httpx
import pytest

from app.infrastructure.http_downstream_capacity_resource import (
    MAX_RESPONSE_BYTES,
    HttpDownstreamCapacityResource,
)


def test_adapter_reads_candidate_with_complete_explicit_scope() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"candidate": {"candidateId": "idea-001"}})

    adapter = HttpDownstreamCapacityResource(
        base_url="https://idea.example",
        timeout_seconds=2,
        base_headers={"Authorization": "Bearer transient"},
        transport=httpx.MockTransport(handle),
    )

    response = adapter.fetch_candidate_detail(
        candidate_id="idea-001",
        tenant_id="tenant-sg",
        book_id="book-sg",
        portfolio_id="portfolio-sg",
        client_id="client-sg",
    )
    adapter.close()

    assert response["candidate"] == {"candidateId": "idea-001"}
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v1/idea-candidates/idea-001"
    assert request.headers["authorization"] == "Bearer transient"
    assert request.headers["x-caller-capabilities"] == "idea.candidate.detail.read"
    assert request.headers["x-caller-tenant-ids"] == "tenant-sg"
    assert request.headers["x-caller-book-ids"] == "book-sg"
    assert request.headers["x-caller-portfolio-ids"] == "portfolio-sg"
    assert request.headers["x-caller-client-ids"] == "client-sg"


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(403, json={"detail": "sensitive"}), "status 403"),
        (httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1)), "size limit"),
        (httpx.Response(200, content=b"not-json"), "invalid JSON"),
        (httpx.Response(200, json=[]), "must be an object"),
    ],
)
def test_adapter_fails_closed_on_untrusted_api_responses(
    response: httpx.Response, message: str
) -> None:
    adapter = HttpDownstreamCapacityResource(
        base_url="https://idea.example",
        timeout_seconds=2,
        transport=httpx.MockTransport(lambda request: response),
    )

    with pytest.raises(ValueError, match=message) as captured:
        adapter.fetch_candidate_detail(
            candidate_id="idea-001",
            tenant_id="tenant-sg",
            book_id="book-sg",
            portfolio_id="portfolio-sg",
            client_id="client-sg",
        )

    assert "sensitive" not in str(captured.value)
    adapter.close()


def test_adapter_rejects_invalid_timeout_and_sanitizes_transport_failure() -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        HttpDownstreamCapacityResource(base_url="https://idea.example", timeout_seconds=0)

    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sensitive endpoint detail", request=request)

    adapter = HttpDownstreamCapacityResource(
        base_url="https://idea.example",
        timeout_seconds=2,
        transport=httpx.MockTransport(fail),
    )
    with pytest.raises(ValueError, match="API request failed") as captured:
        adapter.fetch_candidate_detail(
            candidate_id="idea-001",
            tenant_id="tenant-sg",
            book_id="book-sg",
            portfolio_id="portfolio-sg",
            client_id="client-sg",
        )

    assert "sensitive" not in str(captured.value)
    adapter.close()
