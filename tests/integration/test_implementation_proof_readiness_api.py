from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.api.implementation_proof_readiness as implementation_proof_readiness_api
import app.application.implementation_proof_readiness as implementation_proof_readiness_application
from app.application.ai_lineage_store_proof import (
    AI_LINEAGE_STORE_PROOF_ENV,
    build_ai_lineage_store_proof_payload,
)
from app.application.ai_model_risk_operations_proof import (
    AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
    build_ai_model_risk_operations_proof_payload,
)
from app.application.bond_maturity_live_proof import (
    BOND_MATURITY_LIVE_PROOF_ENV,
    build_bond_maturity_live_proof_payload,
)
from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_PROOF_ENV,
    build_durable_repository_proof_payload,
)
from app.application.operator_workflows_operations_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
    build_operator_workflows_operations_proof_payload,
)
from app.application.runtime_trust_telemetry_proof import (
    RUNTIME_TRUST_TELEMETRY_PROOF_ENV,
    build_runtime_trust_telemetry_proof_payload,
)
from app.application.report_intake_route_proof import (
    REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_PROOF_ENV,
    REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS,
)
from app.application.source_ingestion_live_proof import (
    build_source_ingestion_live_proof_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.application.source_ingestion_scheduled_worker import (
    build_scheduled_worker_check_summary,
    build_scheduled_worker_deploy_proof_payload,
    source_ingestion_schedule_config_from_values,
)
from app.application.source_ingestion_worker import (
    MANIFEST_SCHEMA_VERSION,
    source_ingestion_worker_plan_from_manifest,
)
from app.application.workbench_read_path_proof import (
    WORKBENCH_READ_PATH_PROOF_ENV,
    build_workbench_read_path_proof_payload,
)
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.main import app
from tests.support.proof_provenance import bind_clean_aggregate_proof_provenance
from tests.unit.test_supported_features_gate import (
    _base_registry,
    _valid_implemented_feature,
)

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
    monkeypatch.delenv(AI_MODEL_RISK_OPERATIONS_PROOF_ENV, raising=False)
    monkeypatch.delenv(OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV, raising=False)
    monkeypatch.delenv(WORKBENCH_READ_PATH_PROOF_ENV, raising=False)
    monkeypatch.delenv(REPORT_INTAKE_ROUTE_PROOF_ENV, raising=False)
    monkeypatch.delenv(BOND_MATURITY_LIVE_PROOF_ENV, raising=False)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["repository"] == "lotus-idea"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["certificationReady"] is False
    assert payload["capabilityCount"] == 11
    assert payload["certificationReadyCapabilityCount"] == 0
    assert payload["blockedCapabilityCount"] == 11
    assert payload["supportedFeatureCount"] == 0
    assert payload["supportedFeaturesPromoted"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "outbox_broker_not_configured" in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" in payload["overallBlockers"]
    assert "opportunity_archetype_live_risk_source_proof_missing" in payload["overallBlockers"]
    assert (
        "opportunity_archetype_risk_source_consumer_approval_missing"
        not in payload["overallBlockers"]
    )
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "no_supported_features_promoted" in payload["overallBlockers"]
    assert payload["sourceOfTruth"]["endpoint_certification"] == (
        "docs/operations/endpoint-certification-ledger.json"
    )
    assert payload["sourceOfTruth"]["opportunity_archetypes"] == (
        "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
    )
    assert {capability["capabilityId"] for capability in payload["capabilities"]} == {
        "source-ingestion",
        "advisor-review-queue",
        "ai-explanation",
        "data-mesh-certification",
        "runtime-trust-telemetry-preview",
        "outbox-delivery",
        "operator-workflows-operations",
        "workbench-product-proof",
        "opportunity-archetype-scenarios",
        "downstream-realization",
        "supported-feature-promotion",
    }
    capabilities = {
        capability["capabilityId"]: capability for capability in payload["capabilities"]
    }
    assert (
        "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json"
        in capabilities["ai-explanation"]["evidenceRefs"]
    )
    assert "make ai-model-risk-ops-contract-gate" in capabilities["ai-explanation"]["evidenceRefs"]
    assert (
        "make ai-model-risk-operations-proof-contract-gate"
        in (capabilities["ai-explanation"]["evidenceRefs"])
    )
    ai_explanation_blockers = capabilities["ai-explanation"]["blockers"]
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation_blockers
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation_blockers
    assert "certified_runtime_trust_telemetry_missing" in ai_explanation_blockers
    operator_workflows = capabilities["operator-workflows-operations"]
    assert (
        "contracts/observability/lotus-idea-operator-workflows-operations.v1.json"
        in operator_workflows["evidenceRefs"]
    )
    assert "operator_workflow_dashboard_not_certified" in operator_workflows["blockers"]
    assert "operator_workflow_alerts_not_certified" in operator_workflows["blockers"]
    archetype_scenarios = capabilities["opportunity-archetype-scenarios"]
    assert (
        "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
        in archetype_scenarios["evidenceRefs"]
    )
    assert "make opportunity-archetype-contract-gate" in archetype_scenarios["evidenceRefs"]
    assert (
        "opportunity_archetype_live_risk_source_proof_missing" in (archetype_scenarios["blockers"])
    )
    assert (
        "opportunity_archetype_risk_source_consumer_approval_missing"
        not in (archetype_scenarios["blockers"])
    )
    assert "opportunity_archetype_data_mesh_not_certified" in (archetype_scenarios["blockers"])
    assert (
        "opportunity_archetype_supported_feature_promotion_missing"
        in (archetype_scenarios["blockers"])
    )
    assert archetype_scenarios["supportedFeaturePromoted"] is False
    assert "portfolio_id" not in response.text
    assert "client_id" not in response.text


def test_implementation_proof_readiness_api_blocks_invalid_registry_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "supported-features.json"
    registry_path.write_text(
        json.dumps({"features": [{"id": "fake-feature", "status": "implemented"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        implementation_proof_readiness_application,
        "SUPPORTED_FEATURES_PATH",
        registry_path,
    )
    reset_idea_repository_for_tests()

    response = TestClient(app).get(
        readiness_url(evaluated_at_utc="2026-07-10T00:00:00Z"),
        headers=proof_readiness_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["supportedFeatureCount"] == 0
    assert payload["supportedFeaturesPromoted"] is False
    assert payload["supportedFeaturePromoted"] is False
    assert "supported_feature_registry_invalid" in payload["overallBlockers"]
    capability = next(
        item
        for item in payload["capabilities"]
        if item["capabilityId"] == "supported-feature-promotion"
    )
    assert capability["blockers"] == ["supported_feature_registry_invalid"]
    assert capability["evidenceRefs"][0] == "supported-features.json"
    assert str(tmp_path) not in response.text


def test_implementation_proof_readiness_api_reports_valid_promotion_consistently(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "supported-features.json"
    registry = _base_registry()
    registry["features"] = [_valid_implemented_feature()]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    monkeypatch.setattr(
        implementation_proof_readiness_application,
        "SUPPORTED_FEATURES_PATH",
        registry_path,
    )
    reset_idea_repository_for_tests()

    response = TestClient(app).get(
        readiness_url(evaluated_at_utc="2026-07-10T00:00:00Z"),
        headers=proof_readiness_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["supportedFeatureCount"] == 1
    assert payload["supportedFeaturesPromoted"] is True
    assert payload["supportedFeaturePromoted"] is True
    capability = next(
        item
        for item in payload["capabilities"]
        if item["capabilityId"] == "supported-feature-promotion"
    )
    assert capability["blockers"] == []
    assert capability["supportedFeaturePromoted"] is True


def test_implementation_proof_readiness_api_consumes_configured_proof_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evaluated_at_utc = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)
    _configure_readiness_proof_artifacts(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        evaluated_at_utc=evaluated_at_utc,
    )
    monkeypatch.delenv("LOTUS_IDEA_DATABASE_URL", raising=False)
    reset_idea_repository_for_tests()
    client = TestClient(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert "live_core_source_proof_missing" not in payload["overallBlockers"]
    assert "scheduled_worker_deploy_proof_missing" not in payload["overallBlockers"]
    assert "durable_repository_not_configured" not in payload["overallBlockers"]
    assert "runtime_candidate_snapshot_missing" not in payload["overallBlockers"]
    assert "certified_runtime_trust_telemetry_missing" in payload["overallBlockers"]
    assert "data_mesh_runtime_telemetry_not_certified" in payload["overallBlockers"]
    assert "runtime_trust_telemetry_product_coverage_incomplete" in payload["overallBlockers"]
    assert "certified_ai_lineage_store_missing" not in payload["overallBlockers"]
    assert "operator_workflow_dashboard_not_certified" not in payload["overallBlockers"]
    assert "operator_workflow_alerts_not_certified" not in payload["overallBlockers"]
    assert "workbench_gateway_bff_consumption_proof_missing" not in payload["overallBlockers"]
    assert "lotus_report_live_intake_route_proof_missing" not in payload["overallBlockers"]
    assert (
        "opportunity_archetype_maturity_live_core_source_proof_missing"
        not in payload["overallBlockers"]
    )
    assert "report_evidence_pack_live_materialization_proof_missing" in (payload["overallBlockers"])
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "platform_mesh_certification_missing" in payload["overallBlockers"]
    assert "no_supported_features_promoted" in payload["overallBlockers"]
    capabilities = {
        capability["capabilityId"]: capability for capability in payload["capabilities"]
    }
    assert (
        "source ingestion live proof artifact" in capabilities["source-ingestion"]["evidenceRefs"]
    )
    assert (
        "source ingestion scheduled-worker proof artifact"
        in capabilities["source-ingestion"]["evidenceRefs"]
    )
    assert "durable repository proof artifact" in capabilities["source-ingestion"]["evidenceRefs"]
    assert (
        "runtime trust telemetry proof artifact"
        in capabilities["runtime-trust-telemetry-preview"]["evidenceRefs"]
    )
    assert (
        "runtime_candidate_snapshot_missing"
        not in (capabilities["runtime-trust-telemetry-preview"]["blockers"])
    )
    assert (
        "certified_runtime_trust_telemetry_missing"
        in (capabilities["runtime-trust-telemetry-preview"]["blockers"])
    )
    assert (
        "runtime_trust_telemetry_product_coverage_incomplete"
        in (capabilities["data-mesh-certification"]["blockers"])
    )
    assert "AI lineage store proof artifact" in capabilities["ai-explanation"]["evidenceRefs"]
    assert (
        "AI model-risk operations proof artifact"
        in (capabilities["ai-explanation"]["evidenceRefs"])
    )
    assert "lotus_ai_runtime_execution_missing" in capabilities["ai-explanation"]["blockers"]
    assert (
        "operator workflows operations proof artifact"
        in capabilities["operator-workflows-operations"]["evidenceRefs"]
    )
    assert (
        "external_broker_runtime_proof_missing"
        in (capabilities["operator-workflows-operations"]["blockers"])
    )
    assert (
        "workbench read-path proof artifact"
        in capabilities["workbench-product-proof"]["evidenceRefs"]
    )
    assert "report intake route proof artifact" in " ".join(
        capabilities["downstream-realization"]["evidenceRefs"]
    )
    assert (
        "bond maturity live proof artifact"
        in capabilities["opportunity-archetype-scenarios"]["evidenceRefs"]
    )
    assert (
        "opportunity_archetype_maturity_live_core_source_proof_missing"
        not in capabilities["opportunity-archetype-scenarios"]["blockers"]
    )
    assert "PB_SG_GLOBAL_BAL_001" not in response.text


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


def _configure_readiness_proof_artifacts(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    evaluated_at_utc: datetime,
) -> None:
    monkeypatch.setattr(
        "app.runtime.proof_artifacts.bind_aggregate_proof_provenance",
        bind_clean_aggregate_proof_provenance,
    )
    manifest_path = tmp_path / "source-ingestion-manifest.json"
    live_proof_path = tmp_path / "source-ingestion-live-proof.json"
    scheduled_proof_path = tmp_path / "source-ingestion-scheduled-worker-proof.json"
    durable_proof_path = tmp_path / "durable-repository-proof.json"
    runtime_proof_path = tmp_path / "runtime-trust-telemetry-proof.json"
    ai_lineage_proof_path = tmp_path / "ai-lineage-store-proof.json"
    ai_model_risk_proof_path = tmp_path / "ai-model-risk-operations-proof.json"
    operator_workflows_proof_path = tmp_path / "operator-workflows-operations-proof.json"
    workbench_proof_path = tmp_path / "workbench-read-path-proof.json"
    report_route_proof_path = tmp_path / "report-intake-route-proof.json"
    bond_maturity_live_proof_path = tmp_path / "bond-maturity-live-proof.json"

    manifest_path.write_text("{}", encoding="utf-8")
    _write_proof(
        live_proof_path,
        build_source_ingestion_live_proof_payload(
            generated_at_utc=evaluated_at_utc,
            live_core_source_attempted=True,
            worker_summary={
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "mode": "run_once",
                "sourceAuthority": "lotus-core",
                "durableStorageBacked": True,
                "totalCount": 1,
                "decisionCounts": {"accepted": 1, "replayed": 0},
            },
        ),
    )
    _write_proof(
        scheduled_proof_path,
        _valid_scheduled_worker_proof(generated_at_utc=evaluated_at_utc),
    )
    _write_proof(
        durable_proof_path,
        build_durable_repository_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        runtime_proof_path,
        build_runtime_trust_telemetry_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        ai_lineage_proof_path,
        build_ai_lineage_store_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        ai_model_risk_proof_path,
        build_ai_model_risk_operations_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        operator_workflows_proof_path,
        build_operator_workflows_operations_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        workbench_proof_path,
        build_workbench_read_path_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(report_route_proof_path, _valid_report_intake_route_proof())
    _write_proof(
        bond_maturity_live_proof_path,
        _valid_bond_maturity_live_proof(generated_at_utc=evaluated_at_utc),
    )

    monkeypatch.setenv(MANIFEST_ENV, str(manifest_path))
    monkeypatch.setenv(LIVE_PROOF_ENV, str(live_proof_path))
    monkeypatch.setenv(SCHEDULED_WORKER_PROOF_ENV, str(scheduled_proof_path))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DURABLE_REPOSITORY_PROOF_ENV, str(durable_proof_path))
    monkeypatch.setenv(RUNTIME_TRUST_TELEMETRY_PROOF_ENV, str(runtime_proof_path))
    monkeypatch.setenv(AI_LINEAGE_STORE_PROOF_ENV, str(ai_lineage_proof_path))
    monkeypatch.setenv(AI_MODEL_RISK_OPERATIONS_PROOF_ENV, str(ai_model_risk_proof_path))
    monkeypatch.setenv(OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV, str(operator_workflows_proof_path))
    monkeypatch.setenv(WORKBENCH_READ_PATH_PROOF_ENV, str(workbench_proof_path))
    monkeypatch.setenv(REPORT_INTAKE_ROUTE_PROOF_ENV, str(report_route_proof_path))
    monkeypatch.setenv(BOND_MATURITY_LIVE_PROOF_ENV, str(bond_maturity_live_proof_path))


def _write_proof(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _valid_scheduled_worker_proof(*, generated_at_utc: datetime) -> dict[str, object]:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
            "tenantId": "default",
            "evaluatedAtUtc": "2026-06-21T10:00:00Z",
            "workItems": [{"portfolioId": "PB_SG_GLOBAL_BAL_001", "asOfDate": "2026-06-21"}],
        }
    )
    summary = build_scheduled_worker_check_summary(
        plan=plan,
        schedule=source_ingestion_schedule_config_from_values(
            interval_seconds=300,
            max_runs=1,
        ),
    )
    return build_scheduled_worker_deploy_proof_payload(
        generated_at_utc=generated_at_utc,
        check_summary=summary,
        scheduler_entrypoint_present=True,
        run_once_worker_entrypoint_present=True,
        docker_compose_service_present=True,
    )


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


def _valid_bond_maturity_live_proof(*, generated_at_utc: datetime) -> dict[str, object]:
    return build_bond_maturity_live_proof_payload(
        generated_at_utc=generated_at_utc,
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "holdingsRefPresent": True,
            "maturityFactRefPresent": True,
            "nextMaturityDatePresent": True,
            "maturingPositionCountPresent": True,
            "sourceEvidenceCurrent": True,
            "maturityDiagnostic": "core_maturity_evidence_ready",
            "sourceDiagnosticCodes": ["core_maturity_evidence_ready"],
        },
    )
