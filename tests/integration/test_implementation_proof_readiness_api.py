from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.implementation_proof_readiness as implementation_proof_readiness_api
from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_PROOF_ENV,
    build_durable_repository_proof_payload,
)
from app.application.runtime_trust_telemetry_proof import (
    RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
    build_runtime_trust_telemetry_proof_payload,
)
from app.application.workbench_read_path_proof import (
    WORKBENCH_READ_PATH_PROOF_ENV,
    build_workbench_read_path_proof_payload,
)
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def proof_readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.implementation-proof.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
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
    monkeypatch.delenv(DURABLE_REPOSITORY_PROOF_ENV, raising=False)
    monkeypatch.delenv(RUNTIME_TRUST_TELEMETRY_PROOF_ENV, raising=False)
    monkeypatch.delenv(WORKBENCH_READ_PATH_PROOF_ENV, raising=False)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["certificationReady"] is False
    assert payload["capabilityCount"] == 9
    assert payload["certificationReadyCapabilityCount"] == 0
    assert payload["blockedCapabilityCount"] == 9
    assert payload["supportedFeatureCount"] == 0
    assert payload["supportedFeaturesPromoted"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "outbox_broker_not_configured" in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" in payload["overallBlockers"]
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
        "runtime-trust-telemetry-preview",
        "outbox-delivery",
        "workbench-product-proof",
        "downstream-realization",
        "supported-feature-promotion",
    }
    assert "portfolio_id" not in response.text
    assert "client_id" not in response.text


def test_implementation_proof_readiness_api_consumes_configured_proof_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evaluated_at_utc = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    durable_proof_path = tmp_path / "durable-repository-proof.json"
    runtime_proof_path = tmp_path / "runtime-trust-telemetry-proof.json"
    workbench_proof_path = tmp_path / "workbench-read-path-proof.json"
    durable_proof_path.write_text(
        json.dumps(
            build_durable_repository_proof_payload(
                generated_at_utc=evaluated_at_utc,
                repository_root=ROOT,
            )
        ),
        encoding="utf-8",
    )
    runtime_proof_path.write_text(
        json.dumps(
            build_runtime_trust_telemetry_proof_payload(
                generated_at_utc=evaluated_at_utc,
                repository_root=ROOT,
            )
        ),
        encoding="utf-8",
    )
    workbench_proof_path.write_text(
        json.dumps(
            build_workbench_read_path_proof_payload(
                generated_at_utc=evaluated_at_utc,
                repository_root=ROOT,
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(DURABLE_REPOSITORY_PROOF_ENV, str(durable_proof_path))
    monkeypatch.setenv(RUNTIME_TRUST_TELEMETRY_PROOF_ENV, str(runtime_proof_path))
    monkeypatch.setenv(WORKBENCH_READ_PATH_PROOF_ENV, str(workbench_proof_path))
    monkeypatch.delenv("LOTUS_IDEA_DATABASE_URL", raising=False)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert "durable_repository_not_configured" not in payload["overallBlockers"]
    assert "runtime_candidate_snapshot_missing" not in payload["overallBlockers"]
    assert "workbench_gateway_bff_consumption_proof_missing" not in payload["overallBlockers"]
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "platform_mesh_certification_missing" in payload["overallBlockers"]
    assert "no_supported_features_promoted" in payload["overallBlockers"]
    capabilities = {
        capability["capabilityId"]: capability for capability in payload["capabilities"]
    }
    assert "durable repository proof artifact" in capabilities["source-ingestion"]["evidenceRefs"]
    assert (
        "runtime trust telemetry proof artifact"
        in capabilities["runtime-trust-telemetry-preview"]["evidenceRefs"]
    )
    assert (
        "workbench read-path proof artifact"
        in capabilities["workbench-product-proof"]["evidenceRefs"]
    )


def test_implementation_proof_readiness_api_requires_operator_permission() -> None:
    client = TestClient(app)

    response = client.get(readiness_url())
    role_denied = client.get(
        readiness_url(),
        headers=proof_readiness_headers(roles="advisor"),
    )
    capability_denied = client.get(
        readiness_url(),
        headers=proof_readiness_headers(capabilities="idea.review.queue.read"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"
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
