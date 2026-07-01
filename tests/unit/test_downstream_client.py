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


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"retry_max_attempts": 0}, "retry_max_attempts must be positive"),
        (
            {"retry_initial_backoff_seconds": -0.01},
            "retry_initial_backoff_seconds must not be negative",
        ),
        (
            {"retry_max_backoff_seconds": -0.01},
            "retry_max_backoff_seconds must not be negative",
        ),
        (
            {"retry_initial_backoff_seconds": 0.2, "retry_max_backoff_seconds": 0.1},
            "retry_max_backoff_seconds must be greater than or equal",
        ),
        ({"retry_backoff_multiplier": 0.5}, "retry_backoff_multiplier must be greater"),
        ({"retry_status_codes": frozenset({99})}, "retry_status_codes must be valid"),
    ],
)
def test_invalid_retry_policy_is_rejected(kwargs: dict[str, Any], message: str) -> None:
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


def test_owned_client_context_manager_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
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

    with DownstreamJsonClient(
        DownstreamClientConfig(base_url="https://upstream.example")
    ) as client:
        assert client.owns_client is True
        assert created[0].closed is False

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


def test_unsafe_trace_headers_are_replaced_before_forwarding() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Correlation-Id"].startswith("corr-")
        assert request.headers["X-Trace-Id"].startswith("trace-")
        assert request.headers["X-Correlation-Id"] != "PB_SG_GLOBAL_BAL_001"
        assert request.headers["X-Trace-Id"] != "Bearer-token-abc123"
        return httpx.Response(200, json={"status": "ok"})

    payload = _client_for(httpx.MockTransport(handler)).get_json(
        "/status",
        correlation_id="PB_SG_GLOBAL_BAL_001",
        trace_id="Bearer-token-abc123",
    )
    assert payload == {"status": "ok"}


def test_timeout_maps_to_safe_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(DownstreamServiceError) as exc_info:
        _client_for(httpx.MockTransport(handler)).get_json("/status")
    assert exc_info.value.code == "upstream_timeout"
    assert exc_info.value.attempt_count == 1


def test_generic_http_error_maps_to_safe_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    with pytest.raises(DownstreamServiceError) as exc_info:
        _client_for(httpx.MockTransport(handler)).get_json("/status")
    assert exc_info.value.code == "upstream_unavailable"
    assert exc_info.value.attempt_count == 1


def test_retryable_timeout_is_retried_before_success() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"status": "ok"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    assert client.get_json("/status") == {"status": "ok"}
    assert attempts == 2


def test_retryable_http_error_is_retried_before_success() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("temporary connection failure", request=request)
        return httpx.Response(200, json={"status": "ok"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    assert client.get_json("/status") == {"status": "ok"}
    assert attempts == 2


def test_retryable_status_is_retried_before_success() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={"status": "temporarily_unavailable"})
        return httpx.Response(200, json={"status": "ok"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    assert client.get_json("/status") == {"status": "ok"}
    assert attempts == 2


def test_retry_after_is_capped_by_max_backoff() -> None:
    sleeps: list[float] = []
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "10"}, json={})
        return httpx.Response(200, json={"status": "ok"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0.1,
            retry_max_backoff_seconds=0.25,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
        sleep=sleeps.append,
    )

    assert client.get_json("/status") == {"status": "ok"}
    assert sleeps == [0.25]


@pytest.mark.parametrize("retry_after", ["not-a-number", "-1"])
def test_invalid_retry_after_uses_configured_backoff(retry_after: str) -> None:
    sleeps: list[float] = []
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": retry_after}, json={})
        return httpx.Response(200, json={"status": "ok"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0.1,
            retry_max_backoff_seconds=0.5,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
        sleep=sleeps.append,
    )

    assert client.get_json("/status") == {"status": "ok"}
    assert sleeps == [0.1]


def test_retry_exhaustion_reports_bounded_attempt_count() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    with pytest.raises(DownstreamServiceError) as exc_info:
        client.get_json("/status")
    assert exc_info.value.code == "upstream_timeout"
    assert exc_info.value.attempt_count == 2


def test_post_without_idempotency_key_is_not_retried_by_default() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, json={})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=3,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    with pytest.raises(DownstreamServiceError) as exc_info:
        client.post_json("/submit", json_payload={"action": "write"})
    assert exc_info.value.code == "upstream_unavailable"
    assert exc_info.value.status_code == 503
    assert exc_info.value.attempt_count == 1
    assert attempts == 1


def test_post_with_idempotency_key_preserves_headers_across_retries() -> None:
    captured_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.append(
            {
                "correlation_id": request.headers["X-Correlation-Id"],
                "trace_id": request.headers["X-Trace-Id"],
                "idempotency_key": request.headers["Idempotency-Key"],
            }
        )
        if len(captured_headers) == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"status": "accepted"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    payload = client.post_json(
        "/submit",
        json_payload={"action": "write"},
        correlation_id="corr-retry",
        trace_id="trace-retry",
        idempotency_key="idem-retry",
    )

    assert payload == {"status": "accepted"}
    assert captured_headers == [
        {
            "correlation_id": "corr-retry",
            "trace_id": "trace-retry",
            "idempotency_key": "idem-retry",
        },
        {
            "correlation_id": "corr-retry",
            "trace_id": "trace-retry",
            "idempotency_key": "idem-retry",
        },
    ]


def test_read_only_post_can_be_marked_retryable_without_idempotency_key() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"status": "read"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=2,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
            retry_post_without_idempotency=True,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    assert client.post_json("/query", json_payload={"query": "source-read"}) == {"status": "read"}
    assert attempts == 2


def test_non_retryable_client_error_is_not_retried() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"error": "invalid_request"})

    client = DownstreamJsonClient(
        DownstreamClientConfig(
            base_url="https://upstream.example",
            timeout_seconds=0.5,
            retry_max_attempts=3,
            retry_initial_backoff_seconds=0,
            retry_max_backoff_seconds=0,
        ),
        client=httpx.Client(
            base_url="https://upstream.example",
            transport=httpx.MockTransport(handler),
        ),
    )

    with pytest.raises(DownstreamServiceError) as exc_info:
        client.get_json("/status")
    assert exc_info.value.code == "upstream_rejected_request"
    assert exc_info.value.attempt_count == 1
    assert attempts == 1


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
