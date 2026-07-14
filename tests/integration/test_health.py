import json
import logging

from fastapi import HTTPException
from tests.support.http import managed_test_client
import psycopg
import pytest
from _pytest.logging import LogCaptureFixture
from pytest import MonkeyPatch
from app.main import app, create_app
from app.runtime.repository_state import DATABASE_URL_ENV, reset_idea_repository_for_tests
from app.runtime.recovery_posture import RECOVERY_POSTURE_ENV


def test_create_app_returns_isolated_application_instance() -> None:
    isolated = create_app()

    @isolated.get("/__test_only", include_in_schema=False)
    async def _test_only_route() -> dict[str, str]:
        return {"status": "test-only"}

    assert isolated is not app
    assert managed_test_client(isolated).get("/__test_only").status_code == 200
    assert managed_test_client(app).get("/__test_only").status_code == 404


def test_create_app_keeps_readiness_state_isolated() -> None:
    isolated = create_app()
    isolated.state.is_draining = True

    assert managed_test_client(isolated).get("/health/ready").status_code == 503
    assert managed_test_client(app).get("/health/ready").status_code == 200


def test_health_endpoints() -> None:
    client = managed_test_client(app)
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_correlation_and_trace_header_propagation() -> None:
    client = managed_test_client(app)
    response = client.get(
        "/health",
        headers={"X-Correlation-Id": "corr-123", "X-Trace-Id": "trace-123"},
    )
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-123"
    assert response.headers["X-Trace-Id"] == "trace-123"


def test_correlation_and_trace_headers_are_generated() -> None:
    client = managed_test_client(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"]
    assert response.headers["X-Trace-Id"]
    assert response.headers["X-Correlation-Id"].startswith("corr-")
    assert response.headers["X-Trace-Id"].startswith("trace-")


def test_unsafe_correlation_and_trace_headers_are_replaced() -> None:
    client = managed_test_client(app)
    response = client.get(
        "/health",
        headers={
            "X-Correlation-Id": "PB_SG_GLOBAL_BAL_001",
            "X-Trace-Id": "Bearer-token-abc123",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"].startswith("corr-")
    assert response.headers["X-Trace-Id"].startswith("trace-")
    assert response.headers["X-Correlation-Id"] != "PB_SG_GLOBAL_BAL_001"
    assert response.headers["X-Trace-Id"] != "Bearer-token-abc123"
    assert "PB_SG_GLOBAL_BAL_001" not in response.text
    assert "Bearer-token-abc123" not in response.text


def test_not_found_error_is_product_safe() -> None:
    client = managed_test_client(app)
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "portfolio" not in response.text.lower()
    assert "holding" not in response.text.lower()


def test_validation_error_is_product_safe() -> None:
    isolated = create_app()

    @isolated.get("/__test_validation/{item_id}", include_in_schema=False)
    async def _test_validation_route(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    client = managed_test_client(isolated)
    response = client.get("/__test_validation/not-an-int")
    assert response.status_code == 400
    body = response.text.lower()
    assert "invalid_request" in body
    assert "not-an-int" not in body
    assert "portfolio" not in body


def test_validation_error_log_includes_response_correlation_id(
    caplog: LogCaptureFixture,
) -> None:
    isolated = create_app()

    @isolated.get("/__test_validation/{item_id}", include_in_schema=False)
    async def _test_validation_route(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    client = managed_test_client(isolated)
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        response = client.get(
            "/__test_validation/not-an-int",
            headers={
                "X-Correlation-Id": "corr-validation-log",
                "X-Trace-Id": "trace-validation-log",
            },
        )

    assert response.status_code == 400
    assert response.headers["X-Correlation-Id"] == "corr-validation-log"
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "request.validation_failed"
    assert payload["route"] == "/__test_validation/{item_id}"
    assert payload["correlation_id"] == "corr-validation-log"
    assert payload["trace_id"] == "trace-validation-log"
    assert "not-an-int" not in str(payload)


def test_validation_error_log_uses_sanitized_correlation_id(
    caplog: LogCaptureFixture,
) -> None:
    isolated = create_app()

    @isolated.get("/__test_validation/{item_id}", include_in_schema=False)
    async def _test_validation_route(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    raw_correlation_id = "PB_SG_GLOBAL_BAL_001"
    raw_trace_id = "client_secret:abc123"
    client = managed_test_client(isolated)
    with caplog.at_level(logging.INFO, logger="lotus-idea"):
        response = client.get(
            "/__test_validation/not-an-int",
            headers={
                "X-Correlation-Id": raw_correlation_id,
                "X-Trace-Id": raw_trace_id,
            },
        )

    assert response.status_code == 400
    assert response.headers["X-Correlation-Id"].startswith("corr-")
    assert response.headers["X-Trace-Id"].startswith("trace-")
    assert raw_correlation_id not in response.text
    assert raw_trace_id not in response.text
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "request.validation_failed"
    assert payload["correlation_id"] == response.headers["X-Correlation-Id"]
    assert payload["trace_id"] == response.headers["X-Trace-Id"]
    serialized_payload = json.dumps(payload)
    assert raw_correlation_id not in serialized_payload
    assert raw_trace_id not in serialized_payload


def test_unhandled_error_is_product_safe() -> None:
    isolated = create_app()

    @isolated.get("/__test_unhandled_error", include_in_schema=False)
    async def _test_unhandled_error_route() -> None:
        raise RuntimeError("raw internal detail")

    client = managed_test_client(isolated, raise_server_exceptions=False)
    response = client.get("/__test_unhandled_error")
    assert response.status_code == 500
    body = response.text.lower()
    assert "internal_error" in body
    assert "raw internal detail" not in body


def test_http_exception_is_product_safe() -> None:
    isolated = create_app()

    @isolated.get("/__test_http_exception", include_in_schema=False)
    async def _test_http_exception_route() -> None:
        raise HTTPException(status_code=403, detail="raw entitlement detail")

    client = managed_test_client(isolated)
    response = client.get("/__test_http_exception")
    assert response.status_code == 403
    assert "raw entitlement detail" not in response.text.lower()


def test_readiness_reports_draining_state() -> None:
    client = managed_test_client(app)
    app.state.is_draining = True
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "draining"
        assert response.json()["recoveryPosture"] == "draining"
    finally:
        app.state.is_draining = False


def test_readiness_degrades_when_production_profile_lacks_durable_repository(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    reset_idea_repository_for_tests(reload_from_environment=True)
    client = managed_test_client(create_app())

    try:
        response = client.get("/health/ready")
    finally:
        reset_idea_repository_for_tests()

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "recoveryPosture": "normal",
        "runtimeProfile": "production",
        "durableRepositoryConfigured": False,
        "durableStorageBacked": False,
        "processLocalRepositoryAllowed": False,
        "durableWriteRepositoryRequired": True,
        "configurationBlockers": [
            "durable_repository_not_configured",
            "release_image_digest_binding_missing",
        ],
    }


def test_readiness_degrades_when_configured_postgres_cannot_initialize(
    monkeypatch: MonkeyPatch,
) -> None:
    def fake_connect(database_url: str, *, row_factory: object) -> object:
        raise psycopg.OperationalError(
            "could not connect to db.internal.example with password secret"
        )

    monkeypatch.setenv("LOTUS_IDEA_RUNTIME_PROFILE", "production")
    monkeypatch.setenv(
        DATABASE_URL_ENV,
        "postgresql://lotus_idea:secret@db.internal.example:5432/lotus_idea",
    )
    monkeypatch.setattr("app.runtime.repository_state.psycopg.connect", fake_connect)
    reset_idea_repository_for_tests(reload_from_environment=True)
    client = managed_test_client(create_app(), raise_server_exceptions=False)

    try:
        response = client.get("/health/ready")
    finally:
        reset_idea_repository_for_tests()

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "recoveryPosture": "normal",
        "runtimeProfile": "production",
        "durableRepositoryConfigured": True,
        "durableStorageBacked": False,
        "processLocalRepositoryAllowed": False,
        "durableWriteRepositoryRequired": True,
        "configurationBlockers": [
            "durable_repository_unavailable",
            "release_image_digest_binding_missing",
        ],
    }
    serialized = response.text
    assert "secret" not in serialized
    assert "db.internal" not in serialized
    assert "could not connect" not in serialized


@pytest.mark.parametrize(
    ("configured", "expected_status", "expected_posture", "expected_blocker"),
    [
        ("restoring", "restoring", "restoring", "service_recovery_restoring"),
        ("degraded", "degraded", "degraded", "service_recovery_degraded"),
        ("draining", "draining", "draining", "service_recovery_draining"),
        ("invalid-sensitive-value", "degraded", "degraded", "recovery_posture_invalid"),
    ],
)
def test_readiness_fails_closed_for_recovery_posture(
    monkeypatch: MonkeyPatch,
    configured: str,
    expected_status: str,
    expected_posture: str,
    expected_blocker: str,
) -> None:
    monkeypatch.setenv(RECOVERY_POSTURE_ENV, configured)

    response = managed_test_client(create_app()).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == expected_status
    assert response.json()["recoveryPosture"] == expected_posture
    assert expected_blocker in response.json()["configurationBlockers"]
    assert configured not in response.text or configured == expected_posture
