from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path

import pytest
import scripts.generate_implementation_proof_readiness as proof_report
from app.application.ai_lineage_store_proof import build_ai_lineage_store_proof_payload
from app.application.ai_model_risk_operations.source_contract_proof import (
    build_ai_model_risk_operations_proof_payload,
)
from app.application.ai_workflow_pack_registration.source_contract_proof import (
    build_ai_workflow_pack_registration_proof_payload,
)
from app.application.ai_runtime_proof import (
    build_ai_workflow_pack_runtime_execution_proof_payload,
)
from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.workbench.contract_proof import (
    build_gateway_workbench_contract_proof_payload,
)
from app.application.workbench.discovery_contract_proof import (
    build_gateway_workbench_discovery_contract_proof_payload,
)
from app.application.high_volatility_live_proof import build_high_volatility_live_proof_payload
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.data_mesh.mesh_policy_source_contract import (
    build_mesh_policy_source_contract_payload,
)
from tests.support.durable_repository_proof import (
    SOURCE_COMMIT_SHA,
    valid_durable_repository_ci_execution_receipt,
)
from app.application.outbox.broker.source_contract_proof import (
    build_outbox_broker_source_contract_proof_payload,
)
from app.application.outbox.consumer_contract_proof import (
    build_outbox_consumer_contract_proof_payload,
)
from app.application.outbox.platform_mesh.source_contract_proof import (
    REQUIRED_PLATFORM_PRODUCT_IDS,
    build_outbox_platform_mesh_event_source_contract_proof_payload,
)
from app.application.performance_underperformance_live_proof import (
    build_performance_underperformance_live_proof_payload,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    build_platform_catalog_source_contract_payload,
)
from app.application.risk_concentration_live_proof import (
    build_risk_concentration_live_proof_payload,
)
from app.application.risk_drawdown_live_proof import build_risk_drawdown_live_proof_payload
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.application.source_ingestion_worker import MANIFEST_SCHEMA_VERSION
from app.application.workbench.read_path_source_contract import (
    build_workbench_read_path_source_contract_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.ai_workflow_pack_fixture import (
    write_lotus_ai_workflow_pack_fixture,
)
from tests.support.ai_runtime_proof import ai_runtime_execution_receipt
from tests.support.ai_lineage_store_proof import valid_ai_lineage_ci_execution_receipt
from tests.support.source_ingestion_runtime_evidence import runtime_execution
from tests.unit.source_ingestion_proof_helpers import (
    valid_scheduled_worker_proof as _valid_scheduled_worker_proof,
)
from tests.unit.workbench.test_discovery_contract_proof import _write_platform_fixture


def test_implementation_proof_readiness_payload_is_source_safe() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    payload = proof_report.implementation_proof_readiness_payload(snapshot)

    assert payload["repository"] == "lotus-idea"
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportabilityStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
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
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert (
        "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
        in archetypes["evidenceRefs"]
    )
    assert "make opportunity-archetype-contract-gate" in archetypes["evidenceRefs"]
    assert "opportunity_archetype_live_risk_source_proof_missing" in archetypes["blockers"]
    assert (
        "opportunity_archetype_live_risk_volatility_source_proof_missing"
        in (archetypes["blockers"])
    )
    assert "opportunity_archetype_live_performance_source_proof_missing" in (archetypes["blockers"])
    assert (
        "opportunity_archetype_risk_source_consumer_approval_missing"
        not in (archetypes["blockers"])
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes["blockers"]
    assert archetypes["supportedFeaturePromoted"] is False
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert (
        "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json"
        in ai_explanation["evidenceRefs"]
    )
    assert "make ai-model-risk-ops-contract-gate" in ai_explanation["evidenceRefs"]
    assert "make ai-model-risk-operations-proof-contract-gate" in (ai_explanation["evidenceRefs"])
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation["blockers"]
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation["blockers"]
    serialized = json.dumps(payload)
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "request_body" not in serialized
    assert "response_body" not in serialized


def test_generate_implementation_proof_readiness_writes_output_file(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["repository"] == "lotus-idea"
    assert payload["generatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["evaluatedAtUtc"] == "2026-06-21T10:10:00Z"
    assert payload["aggregateProofProvenance"]["repository"] == "lotus-idea"
    assert payload["aggregateProofProvenance"]["proofRef"].endswith("proof/readiness.json")
    assert payload["readinessStatus"] == "blocked"


def test_generate_implementation_proof_readiness_uses_explicit_scheduled_worker_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(MANIFEST_ENV, "pre-existing-manifest.json")
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://pre-existing-core")
    monkeypatch.setenv(SCHEDULED_WORKER_PROOF_ENV, "pre-existing-proof.json")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "workItems": [{"portfolioId": "PB_SG_GLOBAL_BAL_001", "asOfDate": "2026-06-21"}],
            }
        ),
        encoding="utf-8",
    )
    scheduled_proof = tmp_path / "scheduled-worker-proof.json"
    scheduled_proof.write_text(json.dumps(_valid_scheduled_worker_proof()), encoding="utf-8")
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-ingestion-manifest",
            str(manifest),
            "--source-ingestion-scheduled-worker-proof",
            str(scheduled_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    source_ingestion = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "source-ingestion"
    )
    assert "scheduled_worker_deploy_proof_missing" not in source_ingestion["blockers"]
    assert "live_core_source_proof_missing" in source_ingestion["blockers"]
    assert "source ingestion scheduled-worker proof artifact" in source_ingestion["evidenceRefs"]
    assert "durable_repository_not_configured" in source_ingestion["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
    assert os.environ[MANIFEST_ENV] == "pre-existing-manifest.json"
    assert os.environ[CORE_BASE_URL_ENV] == "http://pre-existing-core"
    assert os.environ[SCHEDULED_WORKER_PROOF_ENV] == "pre-existing-proof.json"


def test_generate_implementation_proof_readiness_uses_explicit_live_source_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(MANIFEST_ENV, "pre-existing-manifest.json")
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://pre-existing-core")
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, "pre-existing-live-proof.json")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": MANIFEST_SCHEMA_VERSION,
                "evaluatedAtUtc": "2026-06-21T10:00:00Z",
                "workItems": [{"portfolioId": "PB_SG_GLOBAL_BAL_001", "asOfDate": "2026-06-21"}],
            }
        ),
        encoding="utf-8",
    )
    live_proof = tmp_path / "source-ingestion-runtime-execution.json"
    live_proof.write_text(
        json.dumps(
            runtime_execution()
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--source-ingestion-manifest",
            str(manifest),
            "--core-base-url",
            "http://localhost:8310",
            "--source-ingestion-runtime-execution",
            str(live_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    source_ingestion = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "source-ingestion"
    )
    assert "live_core_source_proof_missing" not in source_ingestion["blockers"]
    assert "scheduled_worker_deploy_proof_missing" in source_ingestion["blockers"]
    assert "source ingestion runtime execution artifact" in source_ingestion["evidenceRefs"]
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_live_core_source_proof_missing" not in archetypes["blockers"]
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes["blockers"]
    assert "source ingestion runtime execution artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
    assert os.environ[MANIFEST_ENV] == "pre-existing-manifest.json"
    assert os.environ[CORE_BASE_URL_ENV] == "http://pre-existing-core"
    assert os.environ[SOURCE_INGESTION_RUNTIME_EXECUTION_ENV] == "pre-existing-live-proof.json"


def test_generate_implementation_proof_readiness_uses_explicit_durable_repository_proof(
    tmp_path: Path,
) -> None:
    durable_proof = tmp_path / "durable-repository-proof.json"
    durable_proof.write_text(
        json.dumps(
            build_durable_repository_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                source_commit_sha=SOURCE_COMMIT_SHA,
                ci_execution_receipt=valid_durable_repository_ci_execution_receipt(),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--durable-repository-proof",
            str(durable_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "durable_repository_not_configured" not in payload["overallBlockers"]
    assert "repository_side_queue_pagination_not_certified" not in payload["overallBlockers"]
    assert "live_core_source_proof_missing" in payload["overallBlockers"]
    advisor_queue = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "advisor-review-queue"
    )
    assert "durable_repository_not_configured" not in advisor_queue["blockers"]
    assert "repository_side_queue_pagination_not_certified" not in advisor_queue["blockers"]
    assert "workbench_product_proof_missing" in advisor_queue["blockers"]
    assert "data_product_certification_missing" in advisor_queue["blockers"]
    assert "certified_runtime_trust_telemetry_missing" in advisor_queue["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_lineage_store_proof(
    tmp_path: Path,
) -> None:
    ai_lineage_proof = tmp_path / "ai-lineage-store-proof.json"
    ai_lineage_proof.write_text(
        json.dumps(
            build_ai_lineage_store_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--ai-lineage-store-proof",
            str(ai_lineage_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "certified_ai_lineage_store_missing" not in ai_explanation["blockers"]
    assert "certified_ai_lineage_store_missing" not in payload["overallBlockers"]
    assert "lotus_ai_runtime_execution_missing" in ai_explanation["blockers"]
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation["blockers"]
    assert "AI lineage store proof artifact" in ai_explanation["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_model_risk_operations_proof(
    tmp_path: Path,
) -> None:
    ai_model_risk_proof = tmp_path / "ai-model-risk-operations-source-contract-proof.json"
    ai_model_risk_proof.write_text(
        json.dumps(
            build_ai_model_risk_operations_proof_payload(
                generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-26T00:00:00Z",
            "--ai-model-risk-operations-proof",
            str(ai_model_risk_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation["blockers"]
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation["blockers"]
    assert "AI model-risk operations proof artifact" in ai_explanation["evidenceRefs"]
    assert "certified_runtime_trust_telemetry_missing" in ai_explanation["blockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_workflow_pack_registration_proof(
    tmp_path: Path,
) -> None:
    ai_workflow_pack_proof = tmp_path / "ai-workflow-pack-registration-source-contract-proof.json"
    ai_workflow_pack_proof.write_text(
        json.dumps(
            build_ai_workflow_pack_registration_proof_payload(
                generated_at_utc=datetime(2026, 6, 25, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                lotus_ai_root=write_lotus_ai_workflow_pack_fixture(tmp_path),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-25T00:00:00Z",
            "--ai-workflow-pack-registration-proof",
            str(ai_workflow_pack_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation["blockers"]
    assert "workflow_pack_runtime_contract_not_certified" in payload["overallBlockers"]
    assert "lotus_ai_runtime_execution_missing" in ai_explanation["blockers"]
    assert (
        "AI workflow-pack registration source-contract proof artifact"
        in ai_explanation["evidenceRefs"]
    )
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_ai_workflow_pack_runtime_execution_proof(
    tmp_path: Path,
) -> None:
    ai_runtime_proof = tmp_path / "ai-workflow-pack-runtime-execution-proof.json"
    ai_runtime_proof.write_text(
        json.dumps(
            build_ai_workflow_pack_runtime_execution_proof_payload(
                generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
                receipt=ai_runtime_execution_receipt(),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-26T00:00:00Z",
            "--ai-workflow-pack-runtime-execution-proof",
            str(ai_runtime_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    ai_explanation = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "ai-explanation"
    )
    assert "lotus_ai_runtime_execution_missing" not in ai_explanation["blockers"]
    assert "lotus_ai_runtime_execution_missing" not in payload["overallBlockers"]
    assert "lotus_ai_live_provider_execution_missing" in ai_explanation["blockers"]
    assert "lotus_ai_live_provider_execution_missing" in payload["overallBlockers"]
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation["blockers"]
    assert "AI workflow-pack runtime execution proof artifact" in ai_explanation["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_read_path_source_contract_adds_evidence_without_clearing_runtime_blocker(
    tmp_path: Path,
) -> None:
    source_contract_proof = tmp_path / "read-path-source-contract-proof.json"
    source_contract_proof.write_text(
        json.dumps(
            build_workbench_read_path_source_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--workbench-read-path-source-contract-proof",
            str(source_contract_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "workbench_gateway_bff_consumption_proof_missing" in payload["overallBlockers"]
    workbench = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "workbench-product-proof"
    )
    assert "Workbench read-path source-contract proof artifact" in workbench["evidenceRefs"]
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "canonical_demo_runtime_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_gateway_workbench_contract_proof(
    tmp_path: Path,
) -> None:
    workbench_proof_payload = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=Path(__file__).resolve().parents[2],
    )
    gateway_workbench_proof = tmp_path / "gateway-workbench-contract-proof.json"
    gateway_workbench_proof.write_text(
        json.dumps(
            build_gateway_workbench_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                workbench_read_path_source_contract_proof=workbench_proof_payload,
                workbench_read_path_source_contract_proof_ref=(
                    "output/workbench/read-path-source-contract-proof.json"
                ),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--gateway-workbench-contract-proof",
            str(gateway_workbench_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "gateway_workbench_proof_missing" in payload["overallBlockers"]
    assert "workbench_product_proof_missing" in payload["overallBlockers"]
    assert "workbench_panel_missing" in payload["overallBlockers"]
    assert "gateway_workbench_discovery_proof_missing" in payload["overallBlockers"]
    source_ingestion = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "source-ingestion"
    )
    outbox_delivery = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "outbox-delivery"
    )
    assert "Gateway/Workbench contract proof artifact" in source_ingestion["evidenceRefs"]
    assert "Gateway/Workbench contract proof artifact" in outbox_delivery["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_gateway_workbench_discovery_contract_proof(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    platform_root = _write_platform_fixture(tmp_path)
    workbench_proof_payload = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=repository_root,
    )
    gateway_workbench_contract_proof_payload = build_gateway_workbench_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=repository_root,
        workbench_read_path_source_contract_proof=workbench_proof_payload,
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
    )
    gateway_workbench_discovery_contract_proof = (
        tmp_path / "gateway-workbench-discovery-contract-proof.json"
    )
    gateway_workbench_discovery_contract_proof.write_text(
        json.dumps(
            build_gateway_workbench_discovery_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=repository_root,
                platform_root=platform_root,
                platform_catalog_source_contract=build_platform_catalog_source_contract_payload(
                    generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                    repository_root=repository_root,
                    platform_root=platform_root,
                ),
                workbench_read_path_source_contract_proof=workbench_proof_payload,
                gateway_workbench_contract_proof=gateway_workbench_contract_proof_payload,
                platform_catalog_source_contract_ref=(
                    "output/data-mesh/platform-catalog-source-contract.json"
                ),
                workbench_read_path_source_contract_proof_ref=(
                    "output/workbench/read-path-source-contract-proof.json"
                ),
                gateway_workbench_contract_proof_ref=(
                    "output/workbench/gateway-workbench-contract-proof.json"
                ),
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--gateway-workbench-discovery-contract-proof",
            str(gateway_workbench_discovery_contract_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "gateway_workbench_discovery_proof_missing" in payload["overallBlockers"]
    assert "data_mesh_not_certified" in payload["overallBlockers"]
    assert "producer_products_not_active" in payload["overallBlockers"]
    assert "platform_mesh_certification_missing" in payload["overallBlockers"]
    assert "workbench_product_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_outbox_broker_source_contract_proof(
    tmp_path: Path,
) -> None:
    outbox_proof = tmp_path / "outbox-broker-source-contract-proof.json"
    outbox_proof.write_text(
        json.dumps(
            build_outbox_broker_source_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--outbox-broker-source-contract-proof",
            str(outbox_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "outbox_broker_not_configured" in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" in payload["overallBlockers"]
    assert "downstream_consumer_runtime_proof_missing" in payload["overallBlockers"]
    assert "platform_mesh_event_publication_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_consumer_contract_proof_keeps_runtime_readiness_blocked(
    tmp_path: Path,
) -> None:
    outbox_proof = tmp_path / "outbox-broker-source-contract-proof.json"
    outbox_proof.write_text(
        json.dumps(
            build_outbox_broker_source_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    consumer_proof = tmp_path / "outbox-consumer-contract-proof.json"
    consumer_proof.write_text(
        json.dumps(
            build_outbox_consumer_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-21T10:10:00Z",
            "--outbox-broker-source-contract-proof",
            str(outbox_proof),
            "--outbox-consumer-contract-proof",
            str(consumer_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "outbox_broker_not_configured" in payload["overallBlockers"]
    assert "external_broker_runtime_proof_missing" in payload["overallBlockers"]
    assert "downstream_consumer_runtime_proof_missing" in payload["overallBlockers"]
    assert "platform_mesh_event_publication_proof_missing" in payload["overallBlockers"]
    assert "gateway_workbench_proof_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_outbox_platform_mesh_source_contract(
    tmp_path: Path,
) -> None:
    platform_root = _write_outbox_platform_fixture(tmp_path)
    event_proof = tmp_path / "outbox-platform-mesh-event-source-contract-proof.json"
    event_proof.write_text(
        json.dumps(
            build_outbox_platform_mesh_event_source_contract_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
                platform_root=platform_root,
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--outbox-platform-mesh-event-source-contract-proof",
            str(event_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "platform_mesh_event_publication_proof_missing" in payload["overallBlockers"]
    assert "gateway_workbench_proof_missing" in payload["overallBlockers"]
    assert "supported_feature_promotion_missing" in payload["overallBlockers"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
    outbox_delivery = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "outbox-delivery"
    )
    assert (
        "outbox platform-mesh event source-contract proof artifact"
        in outbox_delivery["evidenceRefs"]
    )


def test_generate_implementation_proof_readiness_uses_explicit_mesh_policy_source_contract(
    tmp_path: Path,
) -> None:
    mesh_policy_source_contract = tmp_path / "mesh-policy-source-contract.json"
    mesh_policy_source_contract.write_text(
        json.dumps(
            build_mesh_policy_source_contract_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                repository_root=Path(__file__).resolve().parents[2],
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--mesh-policy-source-contract-proof",
            str(mesh_policy_source_contract),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    data_mesh = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "data-mesh-certification"
    )
    assert "mesh_slo_policy_certification_missing" in data_mesh["blockers"]
    assert "mesh_access_policy_certification_missing" in data_mesh["blockers"]
    assert "mesh_evidence_policy_certification_missing" in data_mesh["blockers"]
    assert "data_mesh_not_certified" in data_mesh["blockers"]
    assert "mesh policy source-contract artifact" in data_mesh["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_risk_concentration_live_proof(
    tmp_path: Path,
) -> None:
    risk_proof = tmp_path / "risk-concentration-live-proof.json"
    risk_proof.write_text(
        json.dumps(
            build_risk_concentration_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_risk_source_attempted=True,
                evaluation_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-risk",
                    "sourceProductId": "lotus-risk:ConcentrationRiskReport:v1",
                    "evaluationOutcome": "candidate_created",
                    "sourceEvidenceCurrent": True,
                    "sourceDiagnosticCodes": ["risk_issuer_coverage_complete"],
                    "reasonCodes": ["concentration_attention"],
                    "unsupportedReasons": [],
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--risk-concentration-live-proof",
            str(risk_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_live_risk_source_proof_missing" not in (archetypes["blockers"])
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "Risk concentration live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_high_volatility_live_proof(
    tmp_path: Path,
) -> None:
    high_volatility_proof = tmp_path / "high-volatility-live-proof.json"
    high_volatility_proof.write_text(
        json.dumps(
            build_high_volatility_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_risk_source_attempted=True,
                evaluation_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-risk",
                    "sourceProductId": "lotus-risk:RiskMetricsReport:v1",
                    "evaluationOutcome": "candidate_created",
                    "sourceEvidenceCurrent": True,
                    "riskSupportabilityReady": True,
                    "sourceDiagnosticCodes": ["risk_volatility_source_ready"],
                    "reasonCodes": ["drawdown_attention"],
                    "unsupportedReasons": [],
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--high-volatility-live-proof",
            str(high_volatility_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert (
        "opportunity_archetype_live_risk_volatility_source_proof_missing"
        not in (archetypes["blockers"])
    )
    assert "opportunity_archetype_drawdown_source_proof_missing" in archetypes["blockers"]
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "High volatility live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_risk_drawdown_live_proof(
    tmp_path: Path,
) -> None:
    risk_drawdown_proof = tmp_path / "risk-drawdown-live-proof.json"
    risk_drawdown_proof.write_text(
        json.dumps(
            build_risk_drawdown_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_risk_source_attempted=True,
                evaluation_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-risk",
                    "sourceProductId": "lotus-risk:DrawdownAnalyticsReport:v1",
                    "evaluationOutcome": "candidate_created",
                    "sourceEvidenceCurrent": True,
                    "riskSupportabilityReady": True,
                    "sourceDiagnosticCodes": ["risk_drawdown_source_ready"],
                    "reasonCodes": ["drawdown_attention"],
                    "unsupportedReasons": [],
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--risk-drawdown-live-proof",
            str(risk_drawdown_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_drawdown_source_proof_missing" not in (archetypes["blockers"])
    assert (
        "opportunity_archetype_live_risk_volatility_source_proof_missing"
        in (archetypes["blockers"])
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "Risk drawdown live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_uses_explicit_performance_underperformance_live_proof(
    tmp_path: Path,
) -> None:
    performance_proof = tmp_path / "performance-underperformance-live-proof.json"
    performance_proof.write_text(
        json.dumps(
            build_performance_underperformance_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_performance_source_attempted=True,
                evaluation_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-performance",
                    "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
                    "evaluationOutcome": "candidate_created",
                    "sourceEvidenceCurrent": True,
                    "benchmarkContextAvailable": True,
                    "sourceDiagnosticCodes": ["performance_benchmark_context_ready"],
                    "reasonCodes": ["underperformance_attention"],
                    "unsupportedReasons": [],
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--performance-underperformance-live-proof",
            str(performance_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert (
        "opportunity_archetype_live_performance_source_proof_missing"
        not in (archetypes["blockers"])
    )
    assert (
        "opportunity_archetype_benchmark_assignment_source_ref_missing" in (archetypes["blockers"])
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "Performance underperformance live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False


def test_generate_implementation_proof_readiness_rejects_naive_timestamp(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = proof_report.main(["--evaluated-at-utc", "2026-06-21T10:10:00"])

    assert result == 2
    assert "timezone-aware" in capsys.readouterr().err


def _write_outbox_platform_fixture(tmp_path: Path) -> Path:
    platform_root = tmp_path / "lotus-platform-outbox"
    manifest_path = (
        platform_root
        / "platform-contracts"
        / "domain-data-products"
        / "domain-product-source-manifest.v1.json"
    )
    catalog_path = platform_root / "generated" / "domain-product-catalog.json"
    handoff_path = platform_root / "docs" / "operations" / "enterprise-mesh-completion-handoff.md"
    manifest_path.parent.mkdir(parents=True)
    catalog_path.parent.mkdir(parents=True)
    handoff_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "repositories": [
                    {
                        "repository": "lotus-idea",
                        "source_mode": "repo_native",
                        "catalog_inclusion": "included",
                        "repo_native_status": "implemented",
                        "repo_native_declaration_path": "contracts/domain-data-products",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    catalog_path.write_text(
        json.dumps(
            {
                "products": [
                    {
                        "product_id": product_id,
                        "producer_repository": "lotus-idea",
                        "lifecycle_status": "proposed",
                    }
                    for product_id in sorted(REQUIRED_PLATFORM_PRODUCT_IDS)
                ]
            }
        ),
        encoding="utf-8",
    )
    handoff_path.write_text("lotus-idea enterprise mesh completion handoff\n", encoding="utf-8")
    return platform_root
