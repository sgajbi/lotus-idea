from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app, create_app


def test_create_app_returns_isolated_application_instance() -> None:
    isolated = create_app()

    @isolated.get("/__test_only", include_in_schema=False)
    async def _test_only_route() -> dict[str, str]:
        return {"status": "test-only"}

    assert isolated is not app
    assert TestClient(isolated).get("/__test_only").status_code == 200
    assert TestClient(app).get("/__test_only").status_code == 404


def test_create_app_keeps_readiness_state_isolated() -> None:
    isolated = create_app()
    isolated.state.is_draining = True

    assert TestClient(isolated).get("/health/ready").status_code == 503
    assert TestClient(app).get("/health/ready").status_code == 200


def test_health_endpoints() -> None:
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_correlation_and_trace_header_propagation() -> None:
    client = TestClient(app)
    response = client.get(
        "/health",
        headers={"X-Correlation-Id": "corr-123", "X-Trace-Id": "trace-123"},
    )
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-123"
    assert response.headers["X-Trace-Id"] == "trace-123"


def test_correlation_and_trace_headers_are_generated() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"]
    assert response.headers["X-Trace-Id"]


def test_not_found_error_is_product_safe() -> None:
    client = TestClient(app)
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "portfolio" not in response.text.lower()
    assert "holding" not in response.text.lower()


def test_validation_error_is_product_safe() -> None:
    isolated = create_app()

    @isolated.get("/__test_validation/{item_id}", include_in_schema=False)
    async def _test_validation_route(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    client = TestClient(isolated)
    response = client.get("/__test_validation/not-an-int")
    assert response.status_code == 400
    body = response.text.lower()
    assert "invalid_request" in body
    assert "not-an-int" not in body
    assert "portfolio" not in body


def test_unhandled_error_is_product_safe() -> None:
    isolated = create_app()

    @isolated.get("/__test_unhandled_error", include_in_schema=False)
    async def _test_unhandled_error_route() -> None:
        raise RuntimeError("raw internal detail")

    client = TestClient(isolated, raise_server_exceptions=False)
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

    client = TestClient(isolated)
    response = client.get("/__test_http_exception")
    assert response.status_code == 403
    assert "raw entitlement detail" not in response.text.lower()


def test_readiness_reports_draining_state() -> None:
    client = TestClient(app)
    app.state.is_draining = True
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "draining"
    finally:
        app.state.is_draining = False
