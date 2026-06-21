import httpx
import pytest

from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
)


def _client_for(handler: httpx.MockTransport) -> DownstreamJsonClient:
    return DownstreamJsonClient(
        DownstreamClientConfig(base_url="https://upstream.example", timeout_seconds=0.5),
        client=httpx.Client(base_url="https://upstream.example", transport=handler),
    )


def test_invalid_base_url_is_rejected() -> None:
    with pytest.raises(DownstreamClientConfigurationError):
        DownstreamClientConfig(base_url="not-a-url")


def test_trace_headers_are_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Correlation-Id"] == "corr-123"
        assert request.headers["X-Trace-Id"] == "trace-123"
        return httpx.Response(200, json={"status": "ok"})

    payload = _client_for(httpx.MockTransport(handler)).get_json(
        "/status",
        correlation_id="corr-123",
        trace_id="trace-123",
    )
    assert payload == {"status": "ok"}


def test_timeout_maps_to_safe_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(DownstreamServiceError) as exc_info:
        _client_for(httpx.MockTransport(handler)).get_json("/status")
    assert exc_info.value.code == "upstream_timeout"


@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (400, "upstream_rejected_request"),
        (404, "upstream_rejected_request"),
        (500, "upstream_unavailable"),
        (503, "upstream_unavailable"),
    ],
)
def test_http_error_statuses_map_to_safe_errors(status_code: int, expected_code: str) -> None:
    client = _client_for(
        httpx.MockTransport(lambda request: httpx.Response(status_code, json={"error": "x"}))
    )
    with pytest.raises(DownstreamServiceError) as exc_info:
        client.get_json("/status")
    assert exc_info.value.code == expected_code
    assert exc_info.value.status_code == status_code


def test_malformed_response_maps_to_safe_error() -> None:
    client = _client_for(
        httpx.MockTransport(lambda request: httpx.Response(200, content=b"not-json"))
    )
    with pytest.raises(DownstreamServiceError) as exc_info:
        client.get_json("/status")
    assert exc_info.value.code == "upstream_malformed_response"
