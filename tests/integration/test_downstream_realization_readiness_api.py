from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.support.http import managed_test_client

import app.api.downstream_realization_readiness as downstream_readiness_api
from app.application.report_intake_route_proof import (
    REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_PROOF_ENV,
    REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS,
)
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


def test_downstream_realization_readiness_api_returns_blocked_operator_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(REPORT_INTAKE_ROUTE_PROOF_ENV, raising=False)
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

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


def test_downstream_realization_readiness_api_consumes_report_route_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    proof_path = tmp_path / "report-intake-route-proof.json"
    proof_path.write_text(json.dumps(_valid_report_intake_route_proof()), encoding="utf-8")
    monkeypatch.setenv(REPORT_INTAKE_ROUTE_PROOF_ENV, str(proof_path))
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

    response = client.get(
        "/api/v1/downstream-realization/readiness",
        headers=downstream_readiness_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "lotus_report_live_intake_route_proof_missing" not in payload["blockers"]
    assert "report_evidence_pack_live_materialization_proof_missing" in payload["blockers"]
    assert "rendered_output_creation_missing" in payload["blockers"]
    assert "archive_record_creation_missing" in payload["blockers"]
    assert "client_publication_authority_blocked" in payload["blockers"]
    report_contract = next(
        contract
        for contract in payload["downstreamContracts"]
        if contract["contractId"] == "lotus-idea-to-lotus-report-evidence-pack-intake:v1"
    )
    assert report_contract["targetRoute"] == REPORT_INTAKE_ROUTE
    assert report_contract["routeFitStatus"] == "route_foundation_proven_not_certified"
    assert "lotus_report_live_intake_route_proof_missing" not in report_contract["blockers"]
    assert (
        "report_evidence_pack_live_materialization_proof_missing" in (report_contract["blockers"])
    )
    assert "report intake route proof artifact" in response.text
    assert "client_id" not in response.text
    assert "portfolio_id" not in response.text


def test_downstream_realization_readiness_api_requires_operator_permission() -> None:
    client = managed_test_client(app)

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
    client = managed_test_client(app)

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


def _valid_report_intake_route_proof() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-24T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_intake_route_contract",
        "proofScope": "source_safe_report_intake_route_only",
        "reportIntakeRouteProofValid": True,
        "aggregateBlockersCleared": REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS,
        "targetRoute": REPORT_INTAKE_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractProvesRoute": True,
            "reportContractPreservesNonProofBoundaries": True,
            "reportContractRetainsMaterializationBlockers": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }
