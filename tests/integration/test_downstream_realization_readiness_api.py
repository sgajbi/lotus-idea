from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.downstream_realization_readiness as downstream_readiness_api
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.main import app


def downstream_readiness_headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.downstream-realization.readiness.read",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Correlation-Id": "corr-downstream-realization-readiness-api",
    }


def test_downstream_realization_readiness_api_returns_blocked_operator_posture() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/downstream-realization/readiness",
        headers=downstream_readiness_headers(),
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == ("corr-downstream-realization-readiness-api")
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["certificationReady"] is False
    assert payload["durableStorageBacked"] is False
    assert payload["conversionIntentCount"] == 0
    assert payload["conversionOutcomeCount"] == 0
    assert payload["reportEvidencePackRequestCount"] == 0
    assert payload["downstreamAdapterFoundationPresent"] is True
    assert payload["supportedFeaturePromoted"] is False
    assert "advise_proposal_creation_adapter_missing" not in payload["blockers"]
    assert "manage_action_register_adapter_missing" not in payload["blockers"]
    assert "report_evidence_pack_materialization_missing" not in payload["blockers"]
    assert "advise_live_contract_proof_missing" in payload["blockers"]
    assert "manage_live_contract_proof_missing" in payload["blockers"]
    assert "lotus_report_live_intake_route_proof_missing" in payload["blockers"]
    assert "report_evidence_pack_live_materialization_proof_missing" in payload["blockers"]
    assert "dedicated_report_idea_evidence_intake_contract_missing" not in payload["blockers"]
    assert {capability["capabilityId"] for capability in payload["capabilities"]} == {
        "advise-proposal-realization",
        "manage-action-realization",
        "report-render-archive-realization",
    }
    assert {capability["sourceAuthority"] for capability in payload["capabilities"]} == {
        "lotus-advise",
        "lotus-manage",
        "lotus-report",
    }
    assert {contract["contractId"] for contract in payload["downstreamContracts"]} == {
        "lotus-idea-to-lotus-advise-proposal-intake:v1",
        "lotus-idea-to-lotus-manage-action-intake:v1",
        "lotus-idea-to-lotus-report-evidence-pack-intake:v1",
    }
    report_contract = next(
        contract
        for contract in payload["downstreamContracts"]
        if contract["contractId"] == "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
    )
    assert report_contract["ownerRepository"] == "lotus-report"
    assert report_contract["sourceAuthority"] == "lotus-report"
    assert report_contract["targetRoute"] == "planned:lotus-report-idea-evidence-pack-intake"
    assert report_contract["routeFitStatus"] == "not_certified"
    assert report_contract["adapterStatus"] == "adapter_foundation_present"
    assert report_contract["certificationReady"] is False
    assert "lotus_report_live_intake_route_proof_missing" in report_contract["blockers"]
    assert (
        "dedicated_report_idea_evidence_intake_contract_missing"
        not in (report_contract["blockers"])
    )
    assert (
        "lotus-report/contracts/idea-evidence-intake/"
        "lotus-report-idea-evidence-pack-intake.v1.json" in report_contract["evidenceRefs"]
    )
    assert "client_id" not in response.text
    assert "portfolio_id" not in response.text
    assert "request_body" not in response.text
    assert "clientId" not in response.text
    assert "portfolioId" not in response.text
    assert "requestBody" not in response.text


def test_downstream_realization_readiness_api_requires_operator_permission() -> None:
    client = TestClient(app)

    role_denied = client.get(
        "/api/v1/downstream-realization/readiness",
        headers=downstream_readiness_headers(roles="advisor"),
    )
    capability_denied = client.get(
        "/api/v1/downstream-realization/readiness",
        headers=downstream_readiness_headers(
            capabilities="idea.conversion.intent.record",
        ),
    )

    assert role_denied.status_code == 403
    assert role_denied.json()["code"] == "permission_denied"
    assert capability_denied.status_code == 403
    assert capability_denied.json()["code"] == "permission_denied"


def test_downstream_realization_readiness_api_emits_not_certified_operation_event(
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

    monkeypatch.setattr(downstream_readiness_api, "emit_operation_event", capture)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(
        "/api/v1/downstream-realization/readiness",
        headers=downstream_readiness_headers(),
    )

    assert response.status_code == 200
    assert events == [
        (
            "downstream_realization_readiness_read",
            "blocked",
            "not_certified",
            False,
            False,
            None,
        )
    ]
