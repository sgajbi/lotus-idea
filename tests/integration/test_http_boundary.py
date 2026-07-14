from __future__ import annotations

from typing import Any

import pytest
from tests.support.http import managed_test_client

from app.main import create_app
from app.middleware.http_boundary import (
    CORS_ALLOWED_ORIGINS_ENV,
    HttpBoundaryConfig,
    HttpBoundaryConfigurationError,
    HttpBoundaryMiddleware,
    MAX_REQUEST_BODY_BYTES_ENV,
    TRUSTED_HOSTS_ENV,
    _content_length,
    http_boundary_config_from_environment,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def test_http_boundary_adds_secure_response_headers() -> None:
    response = managed_test_client(create_app()).get("/health")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), geolocation=(), microphone=()"
    assert (
        response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    )


def test_cors_is_denied_by_default() -> None:
    response = managed_test_client(create_app()).get(
        "/health",
        headers={"Origin": "https://workbench.example"},
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_configured_cors_allowlist_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CORS_ALLOWED_ORIGINS_ENV, "https://workbench.example")

    response = managed_test_client(create_app()).get(
        "/health",
        headers={"Origin": "https://workbench.example"},
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://workbench.example"


def test_configured_trusted_hosts_reject_untrusted_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(TRUSTED_HOSTS_ENV, "testserver")

    response = managed_test_client(create_app()).get("/health", headers={"Host": "evil.example"})

    assert response.status_code == 400
    assert response.headers["X-Correlation-Id"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.json()["code"] == "invalid_host"
    assert "evil.example" not in response.text


def test_oversized_request_is_rejected_before_body_or_secret_leakage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MAX_REQUEST_BODY_BYTES_ENV, "32")
    body = b'{"portfolioId":"PB_SG_GLOBAL_BAL_001","secret":"token-value"}'

    response = managed_test_client(create_app()).post(
        "/api/v1/conversion-intents/oversized/downstream-submissions",
        content=body,
        headers={
            "Authorization": "Bearer should-not-leak",
            "Content-Type": "application/json",
            "Cookie": "session=should-not-leak",
            "Idempotency-Key": "oversized-request",
        },
    )

    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"
    rendered = response.text.lower()
    assert "pb_sg_global_bal_001" not in rendered
    assert "token-value" not in rendered
    assert "should-not-leak" not in rendered


def test_json_write_request_rejects_unsupported_content_type() -> None:
    response = managed_test_client(create_app()).post(
        "/api/v1/conversion-intents/plain/downstream-submissions",
        content="raw prompt or portfolio PB_SG_GLOBAL_BAL_001",
        headers={
            "Content-Type": "text/plain",
            "Idempotency-Key": "plain-text-request",
        },
    )

    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"trusted_hosts": ()}, "trusted_hosts must not be empty"),
        ({"trusted_hosts": ("testserver", " ")}, "trusted_hosts must not contain blanks"),
        (
            {"cors_allowed_origins": ("https://workbench.example", "")},
            "cors_allowed_origins must not contain blanks",
        ),
        ({"max_request_body_bytes": 0}, "max_request_body_bytes must be positive"),
    ],
)
def test_http_boundary_config_rejects_unsafe_static_configuration(
    kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(HttpBoundaryConfigurationError, match=message):
        HttpBoundaryConfig(**kwargs)


@pytest.mark.parametrize(
    ("configured_limit", "message"),
    [
        ("not-a-number", f"{MAX_REQUEST_BODY_BYTES_ENV} must be an integer"),
        ("0", f"{MAX_REQUEST_BODY_BYTES_ENV} must be positive"),
    ],
)
def test_http_boundary_environment_rejects_invalid_request_size(
    monkeypatch: pytest.MonkeyPatch,
    configured_limit: str,
    message: str,
) -> None:
    monkeypatch.setenv(MAX_REQUEST_BODY_BYTES_ENV, configured_limit)

    with pytest.raises(HttpBoundaryConfigurationError, match=message):
        http_boundary_config_from_environment()


def test_malformed_content_length_is_ignored_for_boundary_decision() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/health",
            "headers": [(b"content-length", b"not-a-number")],
        }
    )

    assert _content_length(request) is None


@pytest.mark.asyncio
async def test_oversized_json_write_without_content_length_is_rejected_before_app() -> None:
    called_downstream = False

    async def downstream_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal called_downstream
        called_downstream = True
        raise AssertionError("oversized body must not reach the downstream app")

    status_code, body, headers = await _call_http_boundary(
        downstream_app,
        body_chunks=(b'{"payload":"', b"x" * 64, b'"}'),
        headers=((b"content-type", b"application/json"),),
        max_request_body_bytes=32,
    )

    assert status_code == 413
    assert b"request_too_large" in body
    assert headers["x-content-type-options"] == "nosniff"
    assert called_downstream is False


@pytest.mark.asyncio
async def test_understated_content_length_cannot_bypass_stream_size_limit() -> None:
    called_downstream = False

    async def downstream_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal called_downstream
        called_downstream = True
        raise AssertionError("understated content-length must not reach the downstream app")

    status_code, body, _headers = await _call_http_boundary(
        downstream_app,
        body_chunks=(b'{"payload":"', b"x" * 64, b'"}'),
        headers=((b"content-type", b"application/json"), (b"content-length", b"1")),
        max_request_body_bytes=32,
    )

    assert status_code == 413
    assert b"request_too_large" in body
    assert called_downstream is False


@pytest.mark.asyncio
async def test_bounded_json_write_without_content_length_is_replayed_downstream() -> None:
    observed_body = b""

    async def downstream_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal observed_body
        message = await receive()
        observed_body = bytes(message.get("body", b""))
        await Response(status_code=204)(scope, receive, send)

    status_code, _body, _headers = await _call_http_boundary(
        downstream_app,
        body_chunks=(b'{"payload":"ok"}',),
        headers=((b"content-type", b"application/json"),),
        max_request_body_bytes=32,
    )

    assert status_code == 204
    assert observed_body == b'{"payload":"ok"}'


async def _call_http_boundary(
    downstream_app: ASGIApp,
    *,
    body_chunks: tuple[bytes, ...],
    headers: tuple[tuple[bytes, bytes], ...],
    max_request_body_bytes: int,
) -> tuple[int, bytes, dict[str, str]]:
    sent_messages: list[Message] = []
    request_messages: list[Message] = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(body_chunks) - 1,
        }
        for index, chunk in enumerate(body_chunks)
    ] or [{"type": "http.request", "body": b"", "more_body": False}]
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/test",
        "raw_path": b"/api/v1/test",
        "query_string": b"",
        "headers": [(b"host", b"testserver"), *headers],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    async def receive() -> Message:
        if request_messages:
            return request_messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    middleware = HttpBoundaryMiddleware(
        downstream_app,
        config=HttpBoundaryConfig(max_request_body_bytes=max_request_body_bytes),
    )
    await middleware(scope, receive, send)

    response_start = next(
        message for message in sent_messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        bytes(message.get("body", b""))
        for message in sent_messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in response_start.get("headers", ())
    }
    return int(response_start["status"]), body, response_headers
