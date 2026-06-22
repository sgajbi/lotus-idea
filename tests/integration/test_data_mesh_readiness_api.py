from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.data_mesh_readiness as data_mesh_readiness_api
from app.main import app


def mesh_readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.mesh.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-data-mesh-readiness-api",
    }


def test_data_mesh_readiness_api_returns_not_certified_operator_posture() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/data-mesh/readiness", headers=mesh_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["lifecycleStatus"] == "planned"
    assert payload["certificationStatus"] == "not_certified"
    assert payload["meshRole"] == "planned_producer_and_consumer"
    assert payload["blockers"] == [
        "data_mesh_not_certified",
        "producer_products_not_active",
        "certified_runtime_trust_telemetry_missing",
    ]
    assert payload["runtimeTelemetryBacked"] is False
    assert payload["platformCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["sourceOfTruth"]["producer_declaration"] == (
        "contracts/domain-data-products/lotus-idea-products.v1.json"
    )
    assert {product["productId"] for product in payload["products"]} >= {
        "lotus-idea:IdeaCandidate:v1",
        "lotus-idea:IdeaTrustTelemetry:v1",
    }


def test_data_mesh_readiness_api_requires_operator_permission() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/data-mesh/readiness")
    role_denied = client.get(
        "/api/v1/data-mesh/readiness",
        headers=mesh_readiness_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/data-mesh/readiness",
        headers=mesh_readiness_headers(capabilities="idea.review.queue.read"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"
    assert "portfolio" not in response.text.lower()


def test_data_mesh_readiness_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str, bool, bool, str | None]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                event.error_code,
            )
        )

    monkeypatch.setattr(data_mesh_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get("/api/v1/data-mesh/readiness", headers=mesh_readiness_headers())

    assert response.status_code == 200
    assert events == [
        (
            "mesh_readiness_read",
            "blocked",
            "not_certified",
            False,
            False,
            None,
        )
    ]


def test_data_mesh_readiness_api_reports_unavailable_contracts_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str | None]] = []

    def fail_snapshot() -> None:
        raise ValueError("broken contract")

    def capture(event: Any) -> None:
        events.append((event.operation.value, event.outcome.value, event.error_code))

    monkeypatch.setattr(
        data_mesh_readiness_api, "build_data_mesh_readiness_snapshot", fail_snapshot
    )
    monkeypatch.setattr(data_mesh_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get("/api/v1/data-mesh/readiness", headers=mesh_readiness_headers())

    assert response.status_code == 503
    assert response.json()["code"] == "mesh_readiness_unavailable"
    assert "broken contract" not in response.text
    assert events == [
        (
            "mesh_readiness_read",
            "invalid_state",
            "mesh_readiness_unavailable",
        )
    ]
