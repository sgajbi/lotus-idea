from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from app.application.ai_lineage_store_proof import build_ai_lineage_store_proof_payload
from app.application.ai_workflow_pack_registration.source_contract_proof import (
    build_ai_workflow_pack_registration_proof_payload,
)
from app.application.ai_runtime_proof import (
    build_ai_workflow_pack_runtime_execution_proof_payload,
)
from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.implementation_proof_capability_updates import (
    build_capability_readiness,
)
from app.application.implementation_proof_consumption import (
    _apply_ai_lineage_store_proof,
    _apply_ai_workflow_pack_registration_proof,
    _apply_ai_workflow_pack_runtime_execution_proof,
    _apply_mesh_policy_source_contract,
    _apply_platform_catalog_source_contract,
    _apply_report_materialization_source_contract,
)
from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.supported_feature_promotion import (
    SUPPORTED_FEATURE_REGISTRY_INVALID,
    evaluate_supported_feature_promotion,
)
from tests.support.durable_repository_proof import (
    SOURCE_COMMIT_SHA,
    valid_durable_repository_ci_execution_receipt,
)
from app.application.implementation_proof_opportunity_archetype_proofs import (
    _apply_risk_concentration_live_proof,
)
from app.application.data_mesh.mesh_policy_source_contract import (
    build_mesh_policy_source_contract_payload,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PRODUCER_PRODUCTS,
    build_platform_catalog_source_contract_payload,
)
from app.application.report.intake_route_source_contract import (
    REMAINING_REPORT_INTAKE_ROUTE_CERTIFICATION_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_EVIDENCE_REFS,
)
from app.application.report.materialization_source_contract import (
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
    REPORT_MATERIALIZATION_ROUTE,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
)
from app.domain.proof_evidence import EvidenceClass
from app.application.runtime_trust_telemetry.test_execution_contract import (
    build_runtime_trust_telemetry_test_execution_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    SOURCE_INGESTION_RUNTIME_EXECUTION_ENV,
    MANIFEST_ENV,
)
from app.application.source_ingestion_scheduler import (
    SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
)
from app.application.workbench.read_path_source_contract import (
    build_workbench_read_path_source_contract_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from app.runtime.repository_state import DATABASE_URL_ENV
from tests.support.ai_workflow_pack_fixture import (
    write_lotus_ai_workflow_pack_fixture,
)
from tests.support.ai_runtime_proof import ai_runtime_execution_receipt
from tests.support.ai_lineage_store_proof import valid_ai_lineage_ci_execution_receipt
from tests.support.source_ingestion_runtime_evidence import runtime_execution
from tests.support.source_ingestion_scheduler_evidence import (
    deployment_evidence,
)
from tests.unit.downstream_realization.fixtures import (
    valid_advise_route_source_contract,
    valid_manage_route_source_contract,
)
from tests.support.proof_provenance import bound_aggregate_proof as _bound_aggregate_proof

ROOT = Path(__file__).resolve().parents[2]


def test_implementation_proof_capability_status_is_derived_from_remaining_blockers() -> None:
    capability = build_capability_readiness(
        "source-ingestion",
        "Source-owned high-cash signal ingestion",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("output/source-ingestion/live-proof.json",),
        blockers=(),
    )

    assert capability.certification_ready is True
    assert capability.readiness_status == "ready"
    assert capability.supportability_status == "supported"


@pytest.mark.parametrize(
    ("apply_proof", "capability_id"),
    [
        (_apply_ai_lineage_store_proof, "ai-explanation"),
        (_apply_ai_workflow_pack_registration_proof, "ai-explanation"),
        (_apply_ai_workflow_pack_runtime_execution_proof, "ai-explanation"),
        (_apply_platform_catalog_source_contract, "runtime-trust-telemetry-preview"),
        (_apply_risk_concentration_live_proof, "opportunity-archetype-scenarios"),
    ],
)
def test_implementation_proof_application_is_noop_when_target_blocker_is_absent(
    apply_proof: object,
    capability_id: str,
) -> None:
    capability = build_capability_readiness(
        capability_id,
        "Already-cleared proof family",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("still_blocked_by_other_requirement",),
    )

    result = apply_proof(capability, "new-proof.json")  # type: ignore[operator]

    assert result is capability


def test_report_materialization_source_contract_is_noop_for_other_capability() -> None:
    capability = build_capability_readiness(
        "ai-explanation",
        "AI explanation",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("report_evidence_pack_live_materialization_proof_missing",),
    )

    result = _apply_report_materialization_source_contract(
        capability,
        "output/report/materialization-source-contract-proof.json",
    )

    assert result is capability


def test_report_materialization_source_contract_without_ref_preserves_capability() -> None:
    capability = build_capability_readiness(
        "downstream-realization",
        "Downstream realization",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=(
            "report_evidence_pack_live_materialization_proof_missing",
            "client_publication_authority_blocked",
        ),
    )

    result = _apply_report_materialization_source_contract(capability, None)

    assert "report_evidence_pack_live_materialization_proof_missing" in result.blockers
    assert "client_publication_authority_blocked" in result.blockers
    assert result.evidence_refs == ("existing-proof.json",)


def test_implementation_proof_readiness_reports_blocked_foundation_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LOTUS_IDEA_SOURCE_INGESTION_MANIFEST", raising=False)
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_IDEA_DATABASE_URL", raising=False)

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    assert snapshot.repository == "lotus-idea"
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.certification_ready is False
    assert snapshot.capability_count == 11
    assert snapshot.certification_ready_capability_count == 0
    assert snapshot.blocked_capability_count == 11
    assert snapshot.supported_feature_count == 0
    assert snapshot.supported_features_promoted is False
    assert "outbox_broker_not_configured" in snapshot.overall_blockers
    assert "external_broker_runtime_proof_missing" in snapshot.overall_blockers
    assert "source_ingestion_manifest_not_configured" in snapshot.overall_blockers
    assert "opportunity_archetype_live_risk_source_proof_missing" in snapshot.overall_blockers
    assert (
        "opportunity_archetype_live_performance_source_proof_missing" in snapshot.overall_blockers
    )
    assert (
        "opportunity_archetype_risk_source_consumer_approval_missing"
        not in snapshot.overall_blockers
    )
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.source_of_truth["supported_features"] == (
        "supported-features/supported-features.json"
    )
    assert snapshot.source_of_truth["opportunity_archetypes"] == (
        "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
    )


def test_implementation_proof_readiness_capabilities_are_source_safe() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    capability_ids = {capability.capability_id for capability in snapshot.capabilities}
    assert capability_ids == {
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
    runtime_telemetry = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "runtime-trust-telemetry-preview"
    )
    assert "make runtime-trust-telemetry-preview-check" in runtime_telemetry.evidence_refs
    assert "make runtime-trust-telemetry-snapshot-check" in runtime_telemetry.evidence_refs
    assert (
        "src/app/application/runtime_trust_telemetry/telemetry.py"
        in runtime_telemetry.evidence_refs
    )
    assert "src/app/application/runtime_trust_telemetry.py" not in runtime_telemetry.evidence_refs
    assert (
        "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot" in runtime_telemetry.evidence_refs
    )
    assert "scripts/runtime_trust_telemetry/generate_snapshot.py" in runtime_telemetry.evidence_refs
    assert "platform_mesh_certification_missing" in runtime_telemetry.blockers
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    assert "GET /api/v1/outbox-delivery/readiness" in outbox_delivery.evidence_refs
    assert "POST /api/v1/outbox-delivery/run-once" in outbox_delivery.evidence_refs
    assert "src/app/infrastructure/outbox/publisher.py" in outbox_delivery.evidence_refs
    assert "make outbox-broker-source-contract-proof-gate" in outbox_delivery.evidence_refs
    assert "make outbox-platform-mesh-event-source-contract-proof-gate" in (
        outbox_delivery.evidence_refs
    )
    assert "outbox_broker_not_configured" in outbox_delivery.blockers
    assert "external_broker_runtime_proof_missing" in outbox_delivery.blockers
    source_ingestion = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "source-ingestion"
    )
    assert "GET /api/v1/source-ingestion/readiness" in source_ingestion.evidence_refs
    assert "POST /api/v1/source-ingestion/run-once" in source_ingestion.evidence_refs
    assert "make source-ingestion-worker-check" in source_ingestion.evidence_refs
    assert "make source-ingestion-scheduled-worker-check" in source_ingestion.evidence_refs
    assert "make source-ingestion-runtime-execution-contract-gate" in source_ingestion.evidence_refs
    assert (
        "scripts/source_ingestion/generate_runtime_execution.py" in source_ingestion.evidence_refs
    )
    assert "scripts/source_ingestion_scheduler/generate_source_contract.py" in (
        source_ingestion.evidence_refs
    )
    assert "scripts/source_ingestion_scheduler/generate_deployment_evidence.py" in (
        source_ingestion.evidence_refs
    )
    assert "live_core_source_proof_missing" in source_ingestion.blockers
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert (
        "contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json"
        in archetypes.evidence_refs
    )
    assert "make opportunity-archetype-contract-gate" in archetypes.evidence_refs
    assert "src/app/application/source_ingestion.py" in archetypes.evidence_refs
    assert "opportunity_archetype_live_risk_source_proof_missing" in archetypes.blockers
    assert "opportunity_archetype_live_performance_source_proof_missing" in (archetypes.blockers)
    assert "opportunity_archetype_risk_source_consumer_approval_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert archetypes.readiness_status == "blocked"
    assert archetypes.supportability_status == "not_certified"
    assert archetypes.supported_feature_promoted is False
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "GET /api/v1/downstream-realization/readiness" in downstream.evidence_refs
    assert (
        "POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions"
        in downstream.evidence_refs
    )
    assert (
        "POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions"
        in downstream.evidence_refs
    )
    assert (
        "lotus-report/contracts/idea-evidence-intake/"
        "lotus-report-idea-evidence-pack-intake.v1.json" in downstream.evidence_refs
    )
    assert "lotus_report_live_intake_route_proof_missing" in downstream.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in downstream.blockers
    assert "dedicated_report_idea_evidence_intake_contract_missing" not in downstream.blockers
    ai_explanation = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "ai-explanation"
    )
    assert (
        "contracts/observability/lotus-idea-ai-model-risk-operations.v1.json"
        in ai_explanation.evidence_refs
    )
    assert "make ai-model-risk-ops-contract-gate" in ai_explanation.evidence_refs
    assert "make ai-model-risk-operations-proof-contract-gate" in (ai_explanation.evidence_refs)
    assert "make ai-workflow-pack-registration-proof-contract-gate" in (
        ai_explanation.evidence_refs
    )
    assert "make ai-workflow-pack-runtime-execution-proof-contract-gate" in (
        ai_explanation.evidence_refs
    )
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation.blockers
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation.blockers
    serialized = repr(snapshot)
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "request_body" not in serialized
    assert "response_body" not in serialized


def test_implementation_proof_readiness_uses_durable_repository_proof_without_support_promotion() -> (
    None
):
    proof_ref = "output/persistence/durable-repository-proof.json"
    proof = _bound_aggregate_proof(
        build_durable_repository_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
            source_commit_sha=SOURCE_COMMIT_SHA,
            ci_execution_receipt=valid_durable_repository_ci_execution_receipt(),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        durable_repository_proof=proof,
        durable_repository_proof_ref=proof_ref,
    )

    assert "durable_repository_not_configured" not in snapshot.overall_blockers
    assert "repository_side_queue_pagination_not_certified" not in snapshot.overall_blockers
    assert "live_core_source_proof_missing" in snapshot.overall_blockers
    assert "platform_mesh_certification_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    review_queue = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "advisor-review-queue"
    )
    assert "repository_side_queue_pagination_not_certified" not in review_queue.blockers
    assert "output/persistence/durable-repository-proof.json" in review_queue.evidence_refs


def test_implementation_proof_readiness_lists_valid_source_ingestion_proof_refs_without_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    live_proof = tmp_path / "source-ingestion-runtime-execution.json"
    deployment_evidence_path = (
        tmp_path / "source-ingestion-scheduled-worker-deployment-evidence.json"
    )
    manifest.write_text("{}", encoding="utf-8")
    source_ingestion_runtime_execution_ref = "output/source-ingestion/live-proof.json"
    source_ingestion_runtime_execution = _bound_aggregate_proof(
        runtime_execution(),
        source_ingestion_runtime_execution_ref,
    )
    live_proof.write_text(
        json.dumps(source_ingestion_runtime_execution),
        encoding="utf-8",
    )
    deployment_evidence_path.write_text(
        json.dumps(deployment_evidence(repository_root=ROOT)),
        encoding="utf-8",
    )
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(SOURCE_INGESTION_RUNTIME_EXECUTION_ENV, str(live_proof))
    monkeypatch.setenv(
        SCHEDULED_WORKER_DEPLOYMENT_EVIDENCE_ENV,
        str(deployment_evidence_path),
    )
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        source_ingestion_runtime_execution=source_ingestion_runtime_execution,
        source_ingestion_runtime_execution_ref=source_ingestion_runtime_execution_ref,
        source_ingestion_scheduled_worker_deployment_evidence_ref=(
            "output/source-ingestion/scheduled-worker-deployment-evidence.json"
        ),
    )

    source_ingestion = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "source-ingestion"
    )
    assert "live_core_source_proof_missing" not in source_ingestion.blockers
    assert "scheduled_worker_deploy_proof_missing" not in source_ingestion.blockers
    assert "data_mesh_runtime_telemetry_not_certified" in source_ingestion.blockers
    assert "gateway_workbench_proof_missing" in source_ingestion.blockers
    assert "output/source-ingestion/live-proof.json" in source_ingestion.evidence_refs
    assert "output/source-ingestion/scheduled-worker-deployment-evidence.json" in (
        source_ingestion.evidence_refs
    )
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_runtime_trust_telemetry_test_execution_adds_evidence_without_clearing_runtime() -> None:
    proof_ref = "output/trust-telemetry/test-execution/runtime-trust-telemetry-test-execution.json"
    proof = _bound_aggregate_proof(
        build_runtime_trust_telemetry_test_execution_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        runtime_trust_telemetry_test_execution=proof,
        runtime_trust_telemetry_test_execution_ref=proof_ref,
    )

    assert "runtime_candidate_snapshot_missing" in snapshot.overall_blockers
    assert "certified_runtime_trust_telemetry_missing" in snapshot.overall_blockers
    assert "data_mesh_runtime_telemetry_not_certified" in snapshot.overall_blockers
    assert "runtime_trust_telemetry_product_coverage_incomplete" in (snapshot.overall_blockers)
    assert "durable_repository_not_configured" in snapshot.overall_blockers
    assert "platform_mesh_certification_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    capabilities = {capability.capability_id: capability for capability in snapshot.capabilities}
    assert proof_ref in capabilities["runtime-trust-telemetry-preview"].evidence_refs
    assert proof_ref in capabilities["data-mesh-certification"].evidence_refs
    assert "runtime_candidate_snapshot_missing" in (
        capabilities["runtime-trust-telemetry-preview"].blockers
    )


def test_implementation_proof_readiness_uses_ai_lineage_store_proof_without_runtime_claim() -> None:
    proof_ref = "output/ai/ai-lineage-store-proof.json"
    proof = _bound_aggregate_proof(
        build_ai_lineage_store_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
            ci_execution_receipt=valid_ai_lineage_ci_execution_receipt(),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        ai_lineage_store_proof=proof,
        ai_lineage_store_proof_ref=proof_ref,
    )

    assert "certified_ai_lineage_store_missing" not in snapshot.overall_blockers
    assert "lotus_ai_runtime_execution_missing" in snapshot.overall_blockers
    assert "model_risk_dashboard_runtime_proof_missing" in snapshot.overall_blockers
    assert "model_risk_alert_rules_runtime_proof_missing" in snapshot.overall_blockers
    assert "workflow_pack_runtime_contract_not_certified" in snapshot.overall_blockers
    assert "model_risk_operations_dashboard_not_certified" not in snapshot.overall_blockers
    assert "model_risk_operations_alerts_not_certified" not in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    ai_explanation = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "ai-explanation"
    )
    assert "certified_ai_lineage_store_missing" not in ai_explanation.blockers
    assert "lotus_ai_runtime_execution_missing" in ai_explanation.blockers
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation.blockers
    assert "output/ai/ai-lineage-store-proof.json" in ai_explanation.evidence_refs


def test_ai_workflow_pack_registration_source_contract_adds_evidence_without_clearing_runtime_blocker(
    tmp_path: Path,
) -> None:
    proof_ref = "output/ai/ai-workflow-pack-registration-source-contract-proof.json"
    proof = _bound_aggregate_proof(
        build_ai_workflow_pack_registration_proof_payload(
            generated_at_utc=datetime(2026, 6, 25, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            lotus_ai_root=write_lotus_ai_workflow_pack_fixture(tmp_path),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 25, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        ai_workflow_pack_registration_proof=proof,
        ai_workflow_pack_registration_proof_ref=proof_ref,
    )

    assert "workflow_pack_runtime_contract_not_certified" in snapshot.overall_blockers
    assert "certified_ai_lineage_store_missing" in snapshot.overall_blockers
    assert "lotus_ai_runtime_execution_missing" in snapshot.overall_blockers
    assert "model_risk_operations_dashboard_not_certified" not in snapshot.overall_blockers
    assert "model_risk_operations_alerts_not_certified" not in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    ai_explanation = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "ai-explanation"
    )
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation.blockers
    assert "lotus_ai_runtime_execution_missing" in ai_explanation.blockers
    assert "output/ai/ai-workflow-pack-registration-source-contract-proof.json" in (
        ai_explanation.evidence_refs
    )


def test_implementation_proof_readiness_uses_ai_workflow_pack_runtime_execution_proof_without_publication_claim(
    tmp_path: Path,
) -> None:
    proof_ref = "output/ai/ai-workflow-pack-runtime-execution-proof.json"
    proof = _bound_aggregate_proof(
        build_ai_workflow_pack_runtime_execution_proof_payload(
            generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
            receipt=ai_runtime_execution_receipt(),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        ai_workflow_pack_runtime_execution_proof=proof,
        ai_workflow_pack_runtime_execution_proof_ref=proof_ref,
    )

    assert "lotus_ai_runtime_execution_missing" not in snapshot.overall_blockers
    assert "lotus_ai_live_provider_execution_missing" in snapshot.overall_blockers
    assert "certified_ai_lineage_store_missing" in snapshot.overall_blockers
    assert "workflow_pack_runtime_contract_not_certified" in snapshot.overall_blockers
    assert "model_risk_operations_dashboard_not_certified" not in snapshot.overall_blockers
    assert "model_risk_operations_alerts_not_certified" not in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    ai_explanation = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "ai-explanation"
    )
    assert "lotus_ai_runtime_execution_missing" not in ai_explanation.blockers
    assert "lotus_ai_live_provider_execution_missing" in ai_explanation.blockers
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation.blockers
    assert "output/ai/ai-workflow-pack-runtime-execution-proof.json" in (
        ai_explanation.evidence_refs
    )


def test_workbench_read_path_source_contract_adds_evidence_without_clearing_runtime() -> None:
    proof_ref = "output/workbench/read-path-source-contract-proof.json"
    proof = _bound_aggregate_proof(
        build_workbench_read_path_source_contract_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        workbench_read_path_source_contract_proof=proof,
        workbench_read_path_source_contract_proof_ref=proof_ref,
    )

    assert "workbench_gateway_bff_consumption_proof_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "browser_accessibility_proof_missing" in snapshot.overall_blockers
    assert "canonical_demo_runtime_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    workbench = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "workbench-product-proof"
    )
    assert "workbench_gateway_bff_consumption_proof_missing" in workbench.blockers
    assert "workbench_panel_missing" in workbench.blockers
    assert "output/workbench/read-path-source-contract-proof.json" in workbench.evidence_refs


def test_implementation_proof_readiness_uses_platform_catalog_source_contract_without_certification(
    tmp_path: Path,
) -> None:
    proof_ref = "output/data-mesh/platform-catalog-source-contract.json"
    proof = _bound_aggregate_proof(
        build_platform_catalog_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            platform_root=_write_platform_mesh_fixture(tmp_path),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        platform_catalog_source_contract_proof=proof,
        platform_catalog_source_contract_proof_ref=proof_ref,
    )

    assert "platform_source_manifest_inclusion_missing" not in snapshot.overall_blockers
    assert "platform_catalog_inclusion_missing" not in snapshot.overall_blockers
    assert "data_mesh_not_certified" in snapshot.overall_blockers
    assert "producer_products_not_active" in snapshot.overall_blockers
    assert "certified_runtime_trust_telemetry_missing" in snapshot.overall_blockers
    assert "mesh_slo_policy_certification_missing" in snapshot.overall_blockers
    assert "gateway_workbench_discovery_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    data_mesh = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "data-mesh-certification"
    )
    runtime_telemetry = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "runtime-trust-telemetry-preview"
    )
    assert "platform_source_manifest_inclusion_missing" not in data_mesh.blockers
    assert "platform_catalog_inclusion_missing" not in data_mesh.blockers
    assert "data_mesh_not_certified" in data_mesh.blockers
    assert "mesh_slo_policy_certification_missing" in data_mesh.blockers
    assert "platform_source_manifest_inclusion_missing" not in runtime_telemetry.blockers
    assert "platform_mesh_certification_missing" in runtime_telemetry.blockers
    assert "output/data-mesh/platform-catalog-source-contract.json" in data_mesh.evidence_refs
    assert "output/data-mesh/platform-catalog-source-contract.json" in (
        runtime_telemetry.evidence_refs
    )


def test_implementation_proof_readiness_rejects_stale_platform_catalog_source_contract(
    tmp_path: Path,
) -> None:
    proof_ref = "output/data-mesh/platform-catalog-source-contract.json"
    proof = _bound_aggregate_proof(
        build_platform_catalog_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 22, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            platform_root=_write_platform_mesh_fixture(tmp_path),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        platform_catalog_source_contract_proof=proof,
        platform_catalog_source_contract_proof_ref=proof_ref,
    )

    data_mesh = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "data-mesh-certification"
    )
    assert "platform_source_manifest_inclusion_missing" in data_mesh.blockers
    assert "platform_catalog_inclusion_missing" in data_mesh.blockers
    assert proof_ref not in data_mesh.evidence_refs


def test_implementation_proof_readiness_uses_mesh_policy_source_contract_as_supporting_evidence() -> (
    None
):
    proof_ref = "output/data-mesh/mesh-policy-source-contract.json"
    proof = _bound_aggregate_proof(
        build_mesh_policy_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        mesh_policy_source_contract_proof=proof,
        mesh_policy_source_contract_proof_ref=proof_ref,
    )

    assert "mesh_slo_policy_certification_missing" in snapshot.overall_blockers
    assert "mesh_access_policy_certification_missing" in snapshot.overall_blockers
    assert "mesh_evidence_policy_certification_missing" in snapshot.overall_blockers
    assert "data_mesh_not_certified" in snapshot.overall_blockers
    assert "producer_products_not_active" in snapshot.overall_blockers
    assert "platform_source_manifest_inclusion_missing" in snapshot.overall_blockers
    assert "platform_catalog_inclusion_missing" in snapshot.overall_blockers
    assert "gateway_workbench_discovery_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    data_mesh = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "data-mesh-certification"
    )
    assert "mesh_slo_policy_certification_missing" in data_mesh.blockers
    assert "mesh_access_policy_certification_missing" in data_mesh.blockers
    assert "mesh_evidence_policy_certification_missing" in data_mesh.blockers
    assert "data_mesh_not_certified" in data_mesh.blockers
    assert proof_ref in data_mesh.evidence_refs
    operator_workflows = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "operator-workflows-operations"
    )
    assert proof_ref in operator_workflows.evidence_refs
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_mesh_policy_source_contract_application_preserves_capability_state() -> None:
    capability = build_capability_readiness(
        "data-mesh-certification",
        "Data mesh",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing.json",),
        blockers=("mesh_slo_policy_certification_missing",),
    )

    result = _apply_mesh_policy_source_contract(capability, "source-contract.json")

    assert result.blockers == capability.blockers
    assert result.readiness_status == capability.readiness_status
    assert result.supportability_status == capability.supportability_status
    assert result.evidence_refs == ("existing.json", "source-contract.json")


def test_implementation_proof_readiness_rejects_stale_mesh_policy_source_contract() -> None:
    proof_ref = "output/data-mesh/mesh-policy-source-contract.json"
    proof = _bound_aggregate_proof(
        build_mesh_policy_source_contract_payload(
            generated_at_utc=datetime(2026, 6, 22, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        mesh_policy_source_contract_proof=proof,
        mesh_policy_source_contract_proof_ref=proof_ref,
    )

    data_mesh = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "data-mesh-certification"
    )
    operator_workflows = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "operator-workflows-operations"
    )
    assert proof_ref not in data_mesh.evidence_refs
    assert proof_ref not in operator_workflows.evidence_refs
    assert "mesh_slo_policy_certification_missing" in data_mesh.blockers


def test_readiness_uses_report_intake_route_source_contract_proof_without_materialization() -> None:
    proof_ref = "output/report/intake-route-source-contract-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_intake_route_source_contract_proof=_bound_aggregate_proof(
            _valid_report_intake_route_source_contract_proof(),
            proof_ref,
        ),
        report_intake_route_source_contract_proof_ref=proof_ref,
    )

    assert "lotus_report_live_intake_route_proof_missing" in snapshot.overall_blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in snapshot.overall_blockers
    assert "rendered_output_creation_missing" in snapshot.overall_blockers
    assert "archive_record_creation_missing" in snapshot.overall_blockers
    assert "client_publication_authority_blocked" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "lotus_report_live_intake_route_proof_missing" in downstream.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in downstream.blockers
    assert "rendered_output_creation_missing" in downstream.blockers
    assert "archive_record_creation_missing" in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert "output/report/intake-route-source-contract-proof.json" in downstream.evidence_refs


def test_route_source_contracts_add_evidence_without_clearing_live_or_authority_blockers() -> None:
    advise_proof_ref = "output/downstream/advise-route-source-contract-proof.json"
    manage_proof_ref = "output/downstream/manage-route-source-contract-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        advise_proposal_route_proof=_bound_aggregate_proof(
            valid_advise_route_source_contract(),
            advise_proof_ref,
        ),
        advise_proposal_route_proof_ref=advise_proof_ref,
        manage_action_route_proof=_bound_aggregate_proof(
            valid_manage_route_source_contract(),
            manage_proof_ref,
        ),
        manage_action_route_proof_ref=manage_proof_ref,
    )

    assert "advise_live_contract_proof_missing" in snapshot.overall_blockers
    assert "manage_live_contract_proof_missing" in snapshot.overall_blockers
    assert "suitability_policy_authority_remains_lotus_advise" in snapshot.overall_blockers
    assert "rebalance_execution_authority_remains_lotus_manage" in snapshot.overall_blockers
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "advise_live_contract_proof_missing" in downstream.blockers
    assert "manage_live_contract_proof_missing" in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert advise_proof_ref in downstream.evidence_refs
    assert manage_proof_ref in downstream.evidence_refs


def test_source_contract_adds_evidence_without_clearing_runtime_or_publication_blockers() -> None:
    report_intake_proof_ref = "output/report/intake-route-source-contract-proof.json"
    materialization_contract_ref = "output/report/materialization-source-contract-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_intake_route_source_contract_proof=_bound_aggregate_proof(
            _valid_report_intake_route_source_contract_proof(),
            report_intake_proof_ref,
        ),
        report_intake_route_source_contract_proof_ref=report_intake_proof_ref,
        report_materialization_source_contract_proof=_bound_aggregate_proof(
            _valid_report_materialization_source_contract(),
            materialization_contract_ref,
        ),
        report_materialization_source_contract_proof_ref=materialization_contract_ref,
    )

    assert "lotus_report_live_intake_route_proof_missing" in snapshot.overall_blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in snapshot.overall_blockers
    assert "rendered_output_creation_missing" in snapshot.overall_blockers
    assert "archive_record_creation_missing" in snapshot.overall_blockers
    assert "client_publication_authority_blocked" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "report_evidence_pack_live_materialization_proof_missing" in downstream.blockers
    assert "rendered_output_creation_missing" in downstream.blockers
    assert "archive_record_creation_missing" in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert materialization_contract_ref in downstream.evidence_refs


def test_implementation_proof_readiness_rejects_naive_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        build_implementation_proof_readiness_snapshot(
            evaluated_at_utc=datetime(2026, 6, 21, 10, 10),
            repository=InMemoryIdeaRepository(),
            durable_storage_backed=False,
        )


def test_implementation_proof_readiness_blocks_invalid_supported_features_shape(
    tmp_path: Path,
) -> None:
    supported_features_path = tmp_path / "supported-features"
    supported_features_path.mkdir()
    registry_path = supported_features_path / "supported-features.json"
    registry_path.write_text(
        '{"features": {}}',
        encoding="utf-8",
    )

    evaluation = evaluate_supported_feature_promotion(
        registry_path,
        evaluated_at_utc=datetime(2026, 7, 10, tzinfo=UTC),
    )

    assert evaluation.promoted_feature_count == 0
    assert evaluation.blocker_codes == (SUPPORTED_FEATURE_REGISTRY_INVALID,)


def _write_platform_mesh_fixture(tmp_path: Path) -> Path:
    platform_root = tmp_path / "lotus-platform"
    source_manifest_path = (
        platform_root
        / "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
    )
    catalog_path = platform_root / "generated/domain-product-catalog.json"
    graph_path = platform_root / "generated/domain-product-dependency-graph.json"
    maturity_path = platform_root / "generated/enterprise-mesh-maturity-matrix.json"
    handoff_path = platform_root / "docs/operations/enterprise-mesh-completion-handoff.md"
    source_manifest_path.parent.mkdir(parents=True)
    catalog_path.parent.mkdir(parents=True)
    handoff_path.parent.mkdir(parents=True)
    source_manifest_path.write_text(
        json.dumps(
            {
                "repositories": [
                    {
                        "repository": "lotus-idea",
                        "source_mode": "repo_native",
                        "catalog_inclusion": "included",
                        "repo_native_status": "implemented",
                        "repo_native_declaration_path": "contracts/domain-data-products",
                        "platform_declaration_paths": [],
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
                        "current_routes": [],
                    }
                    for product_id in REQUIRED_PRODUCER_PRODUCTS
                ],
                "consumers": [
                    {
                        "consumer_repository": "lotus-idea",
                        "dependencies": [
                            {"dependency_id": dependency_id}
                            for dependency_id in REQUIRED_CONSUMER_DEPENDENCIES
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    graph_path.write_text(
        '{"contract_id":"lotus-domain-product-dependency-graph"}', encoding="utf-8"
    )
    maturity_path.write_text(
        json.dumps(
            {
                "repositories": [
                    {
                        "repository": "lotus-idea",
                        "classification": "deferred",
                        "mesh_role": "producer",
                    }
                ],
                "products": [
                    {
                        "product_id": product_id,
                        "classification": "deferred",
                        "maturity_wave": "future_wave",
                        "lifecycle_status": "proposed",
                    }
                    for product_id in REQUIRED_PRODUCER_PRODUCTS
                ],
            }
        ),
        encoding="utf-8",
    )
    handoff_path.write_text("lotus-idea future-wave onboarding proof\n", encoding="utf-8")
    return platform_root


def _valid_report_intake_route_source_contract_proof() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-24T00:00:00+00:00",
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


def _valid_report_materialization_source_contract() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_MATERIALIZATION_SOURCE_CONTRACT_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-27T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_materialization_source_contract",
        "proofScope": "report_materialization_declaration_and_contract_compatibility",
        "evidenceClass": EvidenceClass.SOURCE_CONTRACT.value,
        "sourceContractValid": True,
        "aggregateBlockersCleared": REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
        "contractChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractDeclaresMaterialization": True,
            "reportContractPreservesNonProofBoundaries": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
        "reportMaterializationProven": False,
        "renderedOutputCreated": False,
        "archiveRecordCreated": False,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "certificationClosed": False,
    }
