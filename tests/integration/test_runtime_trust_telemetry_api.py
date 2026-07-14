from __future__ import annotations

from typing import Any

import pytest
from tests.support.http import managed_test_client

import app.api.runtime_trust_telemetry as runtime_trust_telemetry_api
from app.domain import InMemoryIdeaRepository
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests


def telemetry_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.mesh.trust-telemetry.preview.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-runtime-trust-telemetry-preview",
    }


def telemetry_snapshot_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.mesh.trust-telemetry.snapshot.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-runtime-trust-telemetry-snapshot",
    }


def high_cash_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.candidate.persist",
        "Idempotency-Key": "runtime-trust-telemetry-candidate",
    }


@pytest.fixture(autouse=True)
def reset_repository() -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())


def test_runtime_trust_telemetry_preview_api_returns_source_safe_aggregate_state() -> None:
    client = managed_test_client(app)
    persist_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        headers=high_cash_headers(),
        json=high_cash_payload(),
    )
    assert persist_response.status_code == 200

    response = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-preview",
        params={"generatedAtUtc": "2026-06-21T10:10:00Z"},
        headers=telemetry_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["productId"] == "lotus-idea:IdeaCandidate:v1"
    assert payload["generatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert {posture["productId"] for posture in payload["productCoverage"]} >= {
        "lotus-idea:OpportunitySignalCandidate:v1",
        "lotus-idea:IdeaCandidate:v1",
        "lotus-idea:IdeaEvidencePacket:v1",
        "lotus-idea:AdvisorOpportunityQueue:v1",
        "lotus-idea:IdeaTrustTelemetry:v1",
    }
    assert (
        _preview_product_posture(
            payload,
            "lotus-idea:OpportunitySignalCandidate:v1",
        )["coverageStatus"]
        == "blocked_not_runtime_backed"
    )
    assert (
        _preview_product_posture(
            payload,
            "lotus-idea:IdeaCandidate:v1",
        )["observedRecordCount"]
        == 1
    )
    assert payload["candidateSnapshotCount"] == 1
    assert payload["currentSourceRefCount"] == 4
    assert payload["sourceAuthorityCounts"] == {"lotus-core": 4}
    assert payload["dataLifecycleStateCounts"] == {"process_local_uncontrolled": 1}
    assert payload["retentionExpiredCount"] == 0
    assert payload["lifecycleControlMissingCount"] == 1
    assert payload["runtimeTelemetryBacked"] is False
    assert "durable_repository_not_configured" in payload["certificationBlockers"]
    assert payload["platformCertified"] is False
    assert payload["certificationStatus"] == "not_certified"
    assert payload["certificationReady"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "platform_mesh_certification_missing" in payload["certificationBlockers"]
    assert "candidateId" not in response.text
    assert "portfolio_id" not in response.text
    assert "contentHash" not in response.text
    assert "/portfolios/" not in response.text


def test_runtime_trust_telemetry_preview_api_requires_operator_permission() -> None:
    client = managed_test_client(app)

    response = client.get("/api/v1/data-mesh/trust-telemetry/runtime-preview")
    role_denied = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-preview",
        headers=telemetry_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-preview",
        headers=telemetry_headers(capabilities="idea.mesh.readiness.read"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"


def test_runtime_trust_telemetry_preview_api_rejects_naive_generation_time() -> None:
    client = managed_test_client(app)

    response = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-preview",
        params={"generatedAtUtc": "2026-06-21T10:10:00"},
        headers=telemetry_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_runtime_trust_telemetry_preview_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str, bool, bool, dict[str, str]]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                dict(event.attributes),
            )
        )

    monkeypatch.setattr(runtime_trust_telemetry_api, "emit_operation_event", capture)
    client = managed_test_client(app)

    response = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-preview",
        headers=telemetry_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "mesh_trust_telemetry_preview_read",
            "blocked",
            "not_certified",
            False,
            False,
            {"candidate_snapshot_count_bucket": "0"},
        )
    ]


def test_runtime_trust_telemetry_snapshot_api_returns_source_safe_contract_state() -> None:
    client = managed_test_client(app)
    persist_response = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        headers=high_cash_headers(),
        json=high_cash_payload(),
    )
    assert persist_response.status_code == 200

    response = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
        params={"generatedAtUtc": "2026-06-21T10:10:00Z"},
        headers=telemetry_snapshot_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_id"] == "lotus-domain-product-trust-telemetry-snapshot"
    assert payload["product_id"] == "lotus-idea:IdeaCandidate:v1"
    assert payload["emitted_at_utc"] == "2026-06-21T10:10:00Z"
    assert {posture["product_id"] for posture in payload["product_coverage"]} >= {
        "lotus-idea:OpportunitySignalCandidate:v1",
        "lotus-idea:IdeaCandidate:v1",
        "lotus-idea:IdeaEvidencePacket:v1",
        "lotus-idea:AdvisorOpportunityQueue:v1",
        "lotus-idea:IdeaTrustTelemetry:v1",
    }
    assert (
        _snapshot_product_posture(
            payload,
            "lotus-idea:OpportunitySignalCandidate:v1",
        )["coverage_status"]
        == "blocked_not_runtime_backed"
    )
    assert payload["freshness"]["freshness_state"] == "current"
    assert payload["freshness"]["age_seconds"] == 600
    assert payload["completeness_status"] == "partial"
    assert payload["data_quality_status"] == "quality_passed"
    assert payload["lineage"]["lineage_materialized"] is True
    assert payload["lineage"]["evidence_access_class"] == "operator_only"
    assert payload["blocking"]["blocked"] is True
    assert "platform_mesh_certification_missing" in payload["blocking"]["blocked_reason"]
    assert payload["evidence"]["source_artifact_uri"].endswith(
        "output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json"
    )
    assert "candidateId" not in response.text
    assert "portfolio_id" not in response.text
    assert "contentHash" not in response.text
    assert "/portfolios/" not in response.text


def test_runtime_trust_telemetry_snapshot_api_requires_operator_permission() -> None:
    client = managed_test_client(app)

    response = client.get("/api/v1/data-mesh/trust-telemetry/runtime-snapshot")
    role_denied = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
        headers=telemetry_snapshot_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
        headers=telemetry_snapshot_headers(capabilities="idea.mesh.trust-telemetry.preview.read"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"


def test_runtime_trust_telemetry_snapshot_api_rejects_naive_generation_time() -> None:
    client = managed_test_client(app)

    response = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
        params={"generatedAtUtc": "2026-06-21T10:10:00"},
        headers=telemetry_snapshot_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def test_runtime_trust_telemetry_snapshot_api_emits_not_certified_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str, bool, bool, dict[str, str]]] = []

    def capture(event: Any) -> None:
        events.append(
            (
                event.operation.value,
                event.outcome.value,
                event.supportability_status.value,
                event.durable_storage_backed,
                event.supported_feature_promoted,
                dict(event.attributes),
            )
        )

    monkeypatch.setattr(runtime_trust_telemetry_api, "emit_operation_event", capture)
    client = managed_test_client(app)

    response = client.get(
        "/api/v1/data-mesh/trust-telemetry/runtime-snapshot",
        headers=telemetry_snapshot_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "mesh_trust_telemetry_snapshot_read",
            "blocked",
            "not_certified",
            False,
            False,
            {"candidate_snapshot_count_bucket": "0"},
        )
    ]


def high_cash_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedCashWeight": "0.18",
        "sourceEvidence": {
            "portfolioStateRef": source_ref("lotus-core:PortfolioStateSnapshot:v1"),
            "holdingsRef": source_ref("lotus-core:HoldingsAsOf:v1"),
            "cashMovementRef": source_ref("lotus-core:PortfolioCashMovementSummary:v1"),
            "cashflowProjectionRef": source_ref("lotus-core:PortfolioCashflowProjection:v1"),
        },
        "entitlementAllowed": True,
    }


def _preview_product_posture(payload: dict[str, Any], product_id: str) -> dict[str, Any]:
    return next(
        posture for posture in payload["productCoverage"] if posture["productId"] == product_id
    )


def _snapshot_product_posture(payload: dict[str, Any], product_id: str) -> dict[str, Any]:
    return next(
        posture for posture in payload["product_coverage"] if posture["product_id"] == product_id
    )


def source_ref(product_id: str) -> dict[str, str]:
    return {
        "productId": product_id,
        "sourceSystem": "lotus-core",
        "productVersion": "v1",
        "route": "/portfolios/{portfolioRef}/source-owned",
        "asOfDate": "2026-06-21",
        "generatedAtUtc": "2026-06-21T10:00:00Z",
        "contentHash": f"sha256:{product_id}",
        "dataQualityStatus": "complete",
        "freshness": "current",
    }
