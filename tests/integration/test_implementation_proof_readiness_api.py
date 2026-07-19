from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import pytest
from tests.support.http import managed_test_client

import app.api.implementation_proof_readiness as implementation_proof_readiness_api
import app.application.implementation_proof_readiness as implementation_proof_readiness_application
from app.application.ai_lineage_store_proof import (
    AI_LINEAGE_STORE_PROOF_ENV,
    build_ai_lineage_store_proof_payload,
)
from app.application.ai_model_risk_operations.source_contract_proof import (
    AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
    build_ai_model_risk_operations_proof_payload,
)
from app.application.bond_maturity_runtime_evidence import (
    BOND_MATURITY_RUNTIME_EXECUTION_ENV,
)
from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_PROOF_ENV,
    build_durable_repository_proof_payload,
)
from app.application.operator_workflows_operations.source_contract_proof import (
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
    build_operator_workflows_operations_proof_payload,
)
from app.application.runtime_trust_telemetry.test_execution_contract import (
    RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
    build_runtime_trust_telemetry_test_execution_payload,
)
from tests.support.durable_repository_proof import (
    SOURCE_COMMIT_SHA,
    valid_durable_repository_ci_execution_receipt,
)
from tests.support.bond_maturity_runtime_evidence import (
    valid_bond_maturity_runtime_evidence,
)
from app.application.report.intake_route_source_contract import (
    REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    MANIFEST_ENV,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
    SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
)
from app.application.proof_provenance import current_source_revision
from tests.support.source_ingestion_runtime_evidence import runtime_execution
from tests.support.source_ingestion_scheduler_evidence import (
    deployment_evidence,
    source_contract,
)
from app.application.workbench.read_path_source_contract import (
    WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
    build_workbench_read_path_source_contract_proof_payload,
)
from app.runtime.repository_state import reset_idea_repository_for_tests
from app.main import app
from tests.support.ai_lineage_store_proof import valid_ai_lineage_ci_execution_receipt
from tests.support.proof_provenance import bind_clean_aggregate_proof_provenance
from tests.unit.test_supported_features_gate import (
    _base_registry,
    _valid_implemented_feature,
)

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ReadinessProofArtifactPaths:
    manifest: Path
    source_ingestion_runtime: Path
    scheduled_worker_deployment: Path
    scheduled_worker_source_contract: Path
    durable_repository: Path
    runtime_trust_telemetry: Path
    ai_lineage_store: Path
    ai_model_risk_operations: Path
    operator_workflows_operations: Path
    workbench_read_path: Path
    report_intake_route: Path
    bond_maturity_live: Path


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
    monkeypatch.delenv(RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV, raising=False)
    monkeypatch.delenv(AI_MODEL_RISK_OPERATIONS_PROOF_ENV, raising=False)
    monkeypatch.delenv(OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV, raising=False)
    monkeypatch.delenv(WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV, raising=False)
    monkeypatch.delenv(REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV, raising=False)
    monkeypatch.delenv(BOND_MATURITY_RUNTIME_EXECUTION_ENV, raising=False)
    reset_idea_repository_for_tests()
    client = managed_test_client(app)

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
    assert "operator_workflow_dashboard_runtime_proof_missing" in operator_workflows["blockers"]
    assert "operator_workflow_alert_rules_runtime_proof_missing" in operator_workflows["blockers"]
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

    response = managed_test_client(app).get(
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

    response = managed_test_client(app).get(
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
    client = managed_test_client(app)

    response = client.get(readiness_url(), headers=proof_readiness_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert "live_core_source_proof_missing" not in payload["overallBlockers"]
    assert "scheduled_worker_deploy_proof_missing" not in payload["overallBlockers"]
    assert "durable_repository_not_configured" not in payload["overallBlockers"]
    assert "runtime_candidate_snapshot_missing" in payload["overallBlockers"]
    assert "certified_runtime_trust_telemetry_missing" in payload["overallBlockers"]
    assert "data_mesh_runtime_telemetry_not_certified" in payload["overallBlockers"]
    assert "runtime_trust_telemetry_product_coverage_incomplete" in payload["overallBlockers"]
    assert "certified_ai_lineage_store_missing" not in payload["overallBlockers"]
    assert "operator_workflow_dashboard_runtime_proof_missing" in payload["overallBlockers"]
    assert "operator_workflow_alert_rules_runtime_proof_missing" in payload["overallBlockers"]
    assert "workbench_gateway_bff_consumption_proof_missing" in payload["overallBlockers"]
    assert "lotus_report_live_intake_route_proof_missing" in payload["overallBlockers"]
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
        "source ingestion runtime execution artifact"
        in capabilities["source-ingestion"]["evidenceRefs"]
    )
    assert (
        "source ingestion scheduled-worker deployment evidence artifact"
        in capabilities["source-ingestion"]["evidenceRefs"]
    )
    assert (
        "source ingestion scheduled-worker source contract artifact"
        in capabilities["source-ingestion"]["evidenceRefs"]
    )
    assert "durable repository proof artifact" in capabilities["source-ingestion"]["evidenceRefs"]
    assert (
        "runtime trust telemetry test execution artifact"
        in capabilities["runtime-trust-telemetry-preview"]["evidenceRefs"]
    )
    assert (
        "runtime_candidate_snapshot_missing"
        in (capabilities["runtime-trust-telemetry-preview"]["blockers"])
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
        "Workbench read-path source-contract proof artifact"
        in capabilities["workbench-product-proof"]["evidenceRefs"]
    )
    assert "Report intake-route source-contract proof artifact" in " ".join(
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
    client = managed_test_client(app)

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
    client = managed_test_client(app)

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
    client = managed_test_client(app)

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
    client = managed_test_client(app)

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
    _bind_readiness_proof_provenance(monkeypatch)
    artifact_paths = _readiness_proof_artifact_paths(tmp_path)
    _write_readiness_proof_artifacts(
        artifact_paths=artifact_paths,
        evaluated_at_utc=evaluated_at_utc,
    )
    _bind_readiness_proof_artifact_env(
        monkeypatch=monkeypatch,
        artifact_paths=artifact_paths,
    )


def _bind_readiness_proof_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.runtime.proof_artifacts.bind_aggregate_proof_provenance",
        bind_clean_aggregate_proof_provenance,
    )


def _readiness_proof_artifact_paths(tmp_path: Path) -> ReadinessProofArtifactPaths:
    return ReadinessProofArtifactPaths(
        manifest=tmp_path / "source-ingestion-manifest.json",
        source_ingestion_runtime=tmp_path / "source-ingestion-runtime-execution.json",
        scheduled_worker_deployment=(
            tmp_path / "source-ingestion-scheduled-worker-deployment-evidence.json"
        ),
        scheduled_worker_source_contract=(
            tmp_path / "source-ingestion-scheduled-worker-source-contract.json"
        ),
        durable_repository=tmp_path / "durable-repository-proof.json",
        runtime_trust_telemetry=tmp_path / "runtime-trust-telemetry-test-execution.json",
        ai_lineage_store=tmp_path / "ai-lineage-store-proof.json",
        ai_model_risk_operations=(tmp_path / "ai-model-risk-operations-source-contract-proof.json"),
        operator_workflows_operations=(
            tmp_path / "operator-workflows-operations-source-contract-proof.json"
        ),
        workbench_read_path=tmp_path / "read-path-source-contract-proof.json",
        report_intake_route=tmp_path / "report-intake-route-source-contract-proof.json",
        bond_maturity_live=tmp_path / "bond-maturity-live-proof.json",
    )


def _write_readiness_proof_artifacts(
    *,
    artifact_paths: ReadinessProofArtifactPaths,
    evaluated_at_utc: datetime,
) -> None:
    artifact_paths.manifest.write_text("{}", encoding="utf-8")
    _write_proof(
        artifact_paths.source_ingestion_runtime,
        runtime_execution(generated_at_utc=evaluated_at_utc),
    )
    _write_proof(
        artifact_paths.scheduled_worker_deployment,
        deployment_evidence(
            repository_root=ROOT,
            source_commit_sha=current_source_revision(ROOT),
        ),
    )
    _write_proof(
        artifact_paths.scheduled_worker_source_contract,
        source_contract(repository_root=ROOT),
    )
    _write_proof(
        artifact_paths.durable_repository,
        build_durable_repository_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
            source_commit_sha=SOURCE_COMMIT_SHA,
            ci_execution_receipt=valid_durable_repository_ci_execution_receipt(),
        ),
    )
    _write_proof(
        artifact_paths.runtime_trust_telemetry,
        build_runtime_trust_telemetry_test_execution_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        artifact_paths.ai_lineage_store,
        build_ai_lineage_store_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
            ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
        ),
    )
    _write_proof(
        artifact_paths.ai_model_risk_operations,
        build_ai_model_risk_operations_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        artifact_paths.operator_workflows_operations,
        build_operator_workflows_operations_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        artifact_paths.workbench_read_path,
        build_workbench_read_path_source_contract_proof_payload(
            generated_at_utc=evaluated_at_utc,
            repository_root=ROOT,
        ),
    )
    _write_proof(
        artifact_paths.report_intake_route,
        _valid_report_intake_route_source_contract_proof(
            generated_at_utc=evaluated_at_utc,
        ),
    )
    _write_proof(
        artifact_paths.bond_maturity_live,
        _valid_bond_maturity_live_proof(generated_at_utc=evaluated_at_utc),
    )


def _bind_readiness_proof_artifact_env(
    *,
    monkeypatch: pytest.MonkeyPatch,
    artifact_paths: ReadinessProofArtifactPaths,
) -> None:
    monkeypatch.setenv(MANIFEST_ENV, str(artifact_paths.manifest))
    monkeypatch.setenv(
        SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
        str(artifact_paths.source_ingestion_runtime),
    )
    monkeypatch.setenv(
        SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
        str(artifact_paths.scheduled_worker_deployment),
    )
    monkeypatch.setenv(
        SCHEDULED_WORKER_SOURCE_CONTRACT_ENV,
        str(artifact_paths.scheduled_worker_source_contract),
    )
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DURABLE_REPOSITORY_PROOF_ENV, str(artifact_paths.durable_repository))
    monkeypatch.setenv(
        RUNTIME_TRUST_TELEMETRY_TEST_EXECUTION_ENV,
        str(artifact_paths.runtime_trust_telemetry),
    )
    monkeypatch.setenv(AI_LINEAGE_STORE_PROOF_ENV, str(artifact_paths.ai_lineage_store))
    monkeypatch.setenv(
        AI_MODEL_RISK_OPERATIONS_PROOF_ENV,
        str(artifact_paths.ai_model_risk_operations),
    )
    monkeypatch.setenv(
        OPERATOR_WORKFLOWS_OPERATIONS_PROOF_ENV,
        str(artifact_paths.operator_workflows_operations),
    )
    monkeypatch.setenv(
        WORKBENCH_READ_PATH_SOURCE_CONTRACT_PROOF_ENV,
        str(artifact_paths.workbench_read_path),
    )
    monkeypatch.setenv(
        REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_ENV,
        str(artifact_paths.report_intake_route),
    )
    monkeypatch.setenv(
        BOND_MATURITY_RUNTIME_EXECUTION_ENV,
        str(artifact_paths.bond_maturity_live),
    )


def _write_proof(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _valid_report_intake_route_source_contract_proof(
    *,
    generated_at_utc: datetime,
) -> dict[str, object]:
    return {
        "schemaVersion": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": generated_at_utc.isoformat(),
        "proofType": "lotus_report_idea_evidence_intake_route_source_contract",
        "proofScope": "report_intake_route_declaration_and_contract_compatibility",
        "evidenceClass": "source_contract",
        "reportIntakeRouteSourceContractValid": True,
        "aggregateBlockersCleared": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
        "targetRoute": REPORT_INTAKE_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractDeclaresCompatibleRoute": True,
            "reportContractPreservesNonProofBoundaries": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
        "reportRouteServingObserved": False,
        "requestAuthorizationObserved": False,
        "tenantIsolationObserved": False,
        "runtimeExecutionObserved": False,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }


def _valid_bond_maturity_live_proof(*, generated_at_utc: datetime) -> dict[str, object]:
    return valid_bond_maturity_runtime_evidence(
        evaluated_at_utc=generated_at_utc,
    )
