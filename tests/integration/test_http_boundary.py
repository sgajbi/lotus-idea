from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.middleware.http_boundary import (
    CORS_ALLOWED_ORIGINS_ENV,
    HttpBoundaryConfig,
    HttpBoundaryConfigurationError,
    MAX_REQUEST_BODY_BYTES_ENV,
    TRUSTED_HOSTS_ENV,
    _content_length,
    http_boundary_config_from_environment,
)
from starlette.requests import Request


def test_http_boundary_adds_secure_response_headers() -> None:
    response = TestClient(create_app()).get("/health")

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
    response = TestClient(create_app()).get(
        "/health",
        headers={"Origin": "https://workbench.example"},
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_configured_cors_allowlist_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CORS_ALLOWED_ORIGINS_ENV, "https://workbench.example")

    response = TestClient(create_app()).get(
        "/health",
        headers={"Origin": "https://workbench.example"},
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://workbench.example"


def test_configured_trusted_hosts_reject_untrusted_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(TRUSTED_HOSTS_ENV, "testserver")

    response = TestClient(create_app()).get("/health", headers={"Host": "evil.example"})

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

    response = TestClient(create_app()).post(
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
    response = TestClient(create_app()).post(
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
