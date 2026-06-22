from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.implementation_proof_readiness as implementation_proof_readiness_api
from app.api.repository_state import reset_idea_repository_for_tests
from app.main import app


def proof_readiness_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": "idea.implementation-proof.readiness.read",
        "X-Correlation-Id": "corr-implementation-proof-readiness-api",
    }


def readiness_url(*, evaluated_at_utc: str = "2026-06-21T10:10:00Z") -> str:
    return f"/api/v1/implementation-proof/readiness?evaluatedAtUtc={evaluated_at_utc}"


def test_implementation_proof_readiness_api_returns_blocked_operator_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOTUS_IDEA_SOURCE_INGESTION_MANIFEST", raising=False)
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_IDEA_DATABASE_URL", raising=False)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["certificationReady"] is False
    assert payload["capabilityCount"] == 7
    assert payload["certificationReadyCapabilityCount"] == 0
    assert payload["blockedCapabilityCount"] == 7
    assert payload["supportedFeatureCount"] == 0
    assert payload["supportedFeaturesPromoted"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "no_supported_features_promoted" in payload["overallBlockers"]
    assert payload["sourceOfTruth"]["endpoint_certification"] == (
        "docs/operations/endpoint-certification-ledger.json"
    )
    assert {capability["capabilityId"] for capability in payload["capabilities"]} == {
        "source-ingestion",
        "advisor-review-queue",
        "ai-explanation",
        "data-mesh-certification",
        "workbench-product-proof",
        "downstream-realization",
        "supported-feature-promotion",
    }
    assert "portfolio_id" not in response.text
    assert "client_id" not in response.text


def test_implementation_proof_readiness_api_requires_operator_permission() -> None:
    client = TestClient(app)

    response = client.get(readiness_url())

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert "portfolio" not in response.text.lower()


def test_implementation_proof_readiness_api_rejects_naive_evaluation_time() -> None:
    client = TestClient(app)

    response = client.get(
        readiness_url(evaluated_at_utc="2026-06-21T10:10:00"),
        headers=proof_readiness_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert response.json()["detail"] == "evaluatedAtUtc must be timezone-aware."


def test_implementation_proof_readiness_api_emits_not_certified_operation_event(
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

    monkeypatch.setattr(implementation_proof_readiness_api, "emit_operation_event", capture)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    assert events == [
        (
            "implementation_proof_readiness_read",
            "blocked",
            "not_certified",
            False,
            False,
            None,
        )
    ]


def test_implementation_proof_readiness_api_reports_unavailable_contracts_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str | None]] = []

    def fail_snapshot(**_: Any) -> None:
        raise ValueError("broken proof source")

    def capture(event: Any) -> None:
        events.append((event.operation.value, event.outcome.value, event.error_code))

    monkeypatch.setattr(
        implementation_proof_readiness_api,
        "build_implementation_proof_readiness_snapshot",
        fail_snapshot,
    )
    monkeypatch.setattr(implementation_proof_readiness_api, "emit_operation_event", capture)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 503
    assert response.json()["code"] == "implementation_proof_readiness_unavailable"
    assert "broken proof source" not in response.text
    assert events == [
        (
            "implementation_proof_readiness_read",
            "invalid_state",
            "implementation_proof_readiness_unavailable",
        )
    ]
