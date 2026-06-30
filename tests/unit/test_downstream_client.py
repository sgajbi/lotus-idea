import httpx
import pytest
from typing import Any

from app.infrastructure.downstream_client import (
    DownstreamClientConfig,
    DownstreamClientConfigurationError,
    DownstreamJsonClient,
    DownstreamServiceError,
    build_trace_headers,
)


def _client_for(handler: httpx.MockTransport) -> DownstreamJsonClient:
    return DownstreamJsonClient(
        DownstreamClientConfig(base_url="https://upstream.example", timeout_seconds=0.5),
        client=httpx.Client(base_url="https://upstream.example", transport=handler),
    )


def test_invalid_base_url_is_rejected() -> None:
    with pytest.raises(DownstreamClientConfigurationError):
        DownstreamClientConfig(base_url="not-a-url")


def test_invalid_timeout_is_rejected() -> None:
    with pytest.raises(DownstreamClientConfigurationError):
        DownstreamClientConfig(base_url="https://upstream.example", timeout_seconds=0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_connections": 0}, "max_connections must be positive"),
        ({"max_keepalive_connections": 0}, "max_keepalive_connections must be positive"),
        (
            {"max_connections": 2, "max_keepalive_connections": 3},
            "max_keepalive_connections must not exceed max_connections",
        ),
        ({"pool_timeout_seconds": 0}, "pool_timeout_seconds must be positive"),
    ],
)
def test_invalid_resource_limits_are_rejected(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(DownstreamClientConfigurationError, match=message):
        DownstreamClientConfig(base_url="https://upstream.example", **kwargs)


def test_default_client_can_be_constructed_for_valid_config() -> None:
    client = DownstreamJsonClient(DownstreamClientConfig(base_url="https://upstream.example"))
    assert client is not None
    client.close()


def test_owned_client_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeHttpxClient:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.closed = False

        def close(self) -> None:
            self.closed = True

    created: list[FakeHttpxClient] = []

    def build_client(**kwargs: object) -> FakeHttpxClient:
        client = FakeHttpxClient(**kwargs)
        created.append(client)
        return client

    monkeypatch.setattr("app.infrastructure.downstream_client.httpx.Client", build_client)

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            max_connections=7,
            max_keepalive_connections=3,
            pool_timeout_seconds=0.25,
        )
    )

    assert client.owns_client is True
    assert created[0].closed is False
    assert created[0].kwargs["base_url"] == "https://upstream.example"

    client.close()

    assert created[0].closed is True


def test_injected_client_is_not_closed() -> None:
    class InjectedClient:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    injected = InjectedClient()
    client = DownstreamJsonClient(
        DownstreamClientConfig(base_url="https://upstream.example"),
        client=injected,  # type: ignore[arg-type]
    )

    assert client.owns_client is False
    client.close()
    assert injected.closed is False


def test_empty_trace_headers_are_omitted() -> None:
    assert build_trace_headers(correlation_id=None, trace_id=None) == {}


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


def test_generic_http_error_maps_to_safe_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    with pytest.raises(DownstreamServiceError) as exc_info:
        _client_for(httpx.MockTransport(handler)).get_json("/status")
    assert exc_info.value.code == "upstream_unavailable"


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


def test_non_object_json_response_maps_to_safe_error() -> None:
    client = _client_for(httpx.MockTransport(lambda request: httpx.Response(200, json=["x"])))
    with pytest.raises(DownstreamServiceError) as exc_info:
        client.get_json("/status")
    assert exc_info.value.code == "upstream_malformed_response"
