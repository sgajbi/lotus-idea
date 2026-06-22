from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.source_ingestion_readiness as source_ingestion_readiness_api
from app.application.source_ingestion_readiness import CORE_BASE_URL_ENV, MANIFEST_ENV
from app.main import app
from app.repository_state import DATABASE_URL_ENV


def source_ingestion_readiness_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": "idea.source-ingestion.readiness.read",
        "X-Correlation-Id": "corr-source-ingestion-readiness-api",
    }


def test_source_ingestion_readiness_api_returns_blocked_operator_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    client = TestClient(app)

    response = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["sourceAuthority"] == "lotus-core"
    assert payload["opportunityFamily"] == "high_cash"
    assert payload["exampleManifestAvailable"] is True
    assert payload["configuredManifestAvailable"] is False
    assert payload["coreBaseUrlConfigured"] is False
    assert payload["durableRepositoryConfigured"] is False
    assert payload["runOnceConfigurationStatus"] == "blocked"
    assert payload["runOnceConfigured"] is False
    assert payload["certificationStatus"] == "not_certified"
    assert payload["liveSourceCertified"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert payload["configurationBlockers"] == [
        "source_ingestion_manifest_not_configured",
        "lotus_core_base_url_not_configured",
        "durable_repository_not_configured",
    ]
    assert payload["certificationBlockers"] == [
        "live_core_source_proof_missing",
        "scheduled_worker_deploy_proof_missing",
        "data_mesh_runtime_telemetry_missing",
        "gateway_workbench_proof_missing",
    ]
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


def test_source_ingestion_readiness_api_requires_operator_permission() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/source-ingestion/readiness")

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert "lotus_core_base_url" not in response.text.lower()


def test_source_ingestion_readiness_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(MANIFEST_ENV, raising=False)
    monkeypatch.delenv(CORE_BASE_URL_ENV, raising=False)
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
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

    monkeypatch.setattr(source_ingestion_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "source_ingestion_readiness_read",
            "blocked",
            "not_certified",
            False,
            False,
            None,
        )
    ]


def test_source_ingestion_readiness_api_emits_configured_run_once_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")
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

    monkeypatch.setattr(source_ingestion_readiness_api, "emit_operation_event", capture)
    client = TestClient(app)

    response = client.get(
        "/api/v1/source-ingestion/readiness",
        headers=source_ingestion_readiness_headers(),
    )

    assert response.status_code == 200
    assert response.json()["runOnceConfigurationStatus"] == "configured"
    assert events == [
        (
            "source_ingestion_readiness_read",
            "accepted",
            "not_certified",
            True,
            False,
            None,
        )
    ]
