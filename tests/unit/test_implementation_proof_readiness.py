from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from typing import Any

import pytest

from app.application.ai_lineage_store_proof import build_ai_lineage_store_proof_payload
from app.application.ai_model_risk_operations_proof import (
    build_ai_model_risk_operations_proof_payload,
)
from app.application.ai_workflow_pack_registration_proof import (
    build_ai_workflow_pack_registration_proof_payload,
)
from app.application.ai_workflow_pack_runtime_execution_proof import (
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
    _apply_downstream_route_contract_proof,
    _apply_mesh_policy_proof,
    _apply_outbox_broker_proof,
    _apply_platform_mesh_onboarding_proof,
    _apply_report_materialization_proof,
)
from app.application.implementation_proof_readiness import (
    _supported_feature_count,
    build_implementation_proof_readiness_snapshot,
)
from app.application.implementation_proof_opportunity_archetype_proofs import (
    _apply_risk_concentration_live_proof,
)
from app.application.mesh_policy_proof import build_mesh_policy_proof_payload
from app.application.outbox_broker_proof import build_outbox_broker_proof_payload
from app.application.platform_mesh_onboarding_proof import (
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PRODUCER_PRODUCTS,
    build_platform_mesh_onboarding_proof_payload,
)
from app.application.report_intake_route_proof import (
    REMAINING_REPORT_INTAKE_ROUTE_BLOCKERS,
    REPORT_INTAKE_ROUTE,
    REPORT_INTAKE_ROUTE_BLOCKERS_CLEARED,
    REPORT_INTAKE_ROUTE_PROOF_SCHEMA_VERSION,
    REQUIRED_REPORT_INTAKE_ROUTE_EVIDENCE_REFS,
)
from app.application.report_materialization_proof import (
    REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
    REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
    REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION,
    REPORT_MATERIALIZATION_ROUTE,
    REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
)
from app.application.runtime_trust_telemetry_proof import (
    build_runtime_trust_telemetry_proof_payload,
)
from app.application.proof_provenance import bind_aggregate_proof_provenance
from app.application.source_ingestion_live_proof import (
    build_source_ingestion_live_proof_payload,
)
from app.application.source_ingestion_readiness import (
    CORE_BASE_URL_ENV,
    LIVE_PROOF_ENV,
    MANIFEST_ENV,
    SCHEDULED_WORKER_PROOF_ENV,
)
from app.application.downstream_route_contract_proof import (
    ADVISE_ROUTE_BLOCKERS_CLEARED,
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
from app.application.workbench_read_path_proof import build_workbench_read_path_proof_payload
from app.domain import InMemoryIdeaRepository
from app.runtime.repository_state import DATABASE_URL_ENV
from tests.support.ai_workflow_pack_fixture import (
    write_lotus_ai_workflow_pack_fixture,
    write_lotus_ai_workflow_pack_runtime_execution_fixture,
)
from tests.support.downstream_route_contract_fixtures import (
    valid_advise_route_proof,
    valid_manage_route_proof,
)

ROOT = Path(__file__).resolve().parents[2]


def _bound_aggregate_proof(payload: dict[str, object], proof_ref: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        artifact_path = Path(directory) / "proof.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        return bind_aggregate_proof_provenance(
            payload,
            artifact_path=artifact_path,
            proof_ref=proof_ref,
            repository_root=ROOT,
        )


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
        (_apply_mesh_policy_proof, "data-mesh-certification"),
        (_apply_ai_lineage_store_proof, "ai-explanation"),
        (_apply_ai_workflow_pack_registration_proof, "ai-explanation"),
        (_apply_ai_workflow_pack_runtime_execution_proof, "ai-explanation"),
        (_apply_outbox_broker_proof, "outbox-delivery"),
        (_apply_platform_mesh_onboarding_proof, "runtime-trust-telemetry-preview"),
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


def test_downstream_route_contract_proof_application_is_noop_for_other_capability() -> None:
    capability = build_capability_readiness(
        "ai-explanation",
        "AI explanation",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("advise_live_contract_proof_missing",),
    )

    result = _apply_downstream_route_contract_proof(
        capability,
        capability_id="downstream-realization",
        blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
        proof_ref="output/downstream/advise-proposal-route-proof.json",
    )

    assert result is capability


def test_downstream_route_contract_proof_application_is_noop_without_matching_blocker() -> None:
    capability = build_capability_readiness(
        "downstream-realization",
        "Downstream realization",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("client_publication_authority_blocked",),
    )

    result = _apply_downstream_route_contract_proof(
        capability,
        capability_id="downstream-realization",
        blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
        proof_ref="output/downstream/advise-proposal-route-proof.json",
    )

    assert result is capability


def test_downstream_route_contract_proof_application_preserves_refs_without_proof_ref() -> None:
    capability = build_capability_readiness(
        "downstream-realization",
        "Downstream realization",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("advise_live_contract_proof_missing", "client_publication_authority_blocked"),
    )

    result = _apply_downstream_route_contract_proof(
        capability,
        capability_id="downstream-realization",
        blockers_cleared=ADVISE_ROUTE_BLOCKERS_CLEARED,
        proof_ref=None,
    )

    assert "advise_live_contract_proof_missing" not in result.blockers
    assert "client_publication_authority_blocked" in result.blockers
    assert result.evidence_refs == ("existing-proof.json",)


def test_report_materialization_proof_application_is_noop_for_other_capability() -> None:
    capability = build_capability_readiness(
        "ai-explanation",
        "AI explanation",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("report_evidence_pack_live_materialization_proof_missing",),
    )

    result = _apply_report_materialization_proof(
        capability,
        "output/downstream/report-materialization-proof.json",
    )

    assert result is capability


def test_report_materialization_proof_application_preserves_refs_without_proof_ref() -> None:
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

    result = _apply_report_materialization_proof(capability, None)

    assert "report_evidence_pack_live_materialization_proof_missing" not in result.blockers
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
    assert snapshot.capability_count == 10
    assert snapshot.certification_ready_capability_count == 0
    assert snapshot.blocked_capability_count == 10
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
        "GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot" in runtime_telemetry.evidence_refs
    )
    assert "scripts/generate_runtime_trust_telemetry_snapshot.py" in runtime_telemetry.evidence_refs
    assert "platform_mesh_certification_missing" in runtime_telemetry.blockers
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    assert "GET /api/v1/outbox-delivery/readiness" in outbox_delivery.evidence_refs
    assert "POST /api/v1/outbox-delivery/run-once" in outbox_delivery.evidence_refs
    assert "src/app/infrastructure/outbox_publisher.py" in outbox_delivery.evidence_refs
    assert "make outbox-broker-proof-contract-gate" in outbox_delivery.evidence_refs
    assert "make outbox-platform-mesh-event-publication-proof-contract-gate" in (
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
    assert "make source-ingestion-live-proof-contract-gate" in source_ingestion.evidence_refs
    assert "scripts/generate_source_ingestion_live_proof.py" in source_ingestion.evidence_refs
    assert "scripts/generate_scheduled_source_ingestion_worker_proof.py" in (
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
    assert "live_core_source_proof_missing" in snapshot.overall_blockers
    assert "platform_mesh_certification_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    source_ingestion = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "source-ingestion"
    )
    assert "durable_repository_not_configured" not in source_ingestion.blockers
    assert "output/persistence/durable-repository-proof.json" in source_ingestion.evidence_refs


def test_implementation_proof_readiness_lists_valid_source_ingestion_proof_refs_without_promotion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    live_proof = tmp_path / "source-ingestion-live-proof.json"
    scheduled_proof = tmp_path / "source-ingestion-scheduled-worker-proof.json"
    manifest.write_text("{}", encoding="utf-8")
    live_proof.write_text(
        json.dumps(
            build_source_ingestion_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
                live_core_source_attempted=True,
                worker_summary={
                    "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
                    "mode": "run_once",
                    "sourceAuthority": "lotus-core",
                    "durableStorageBacked": True,
                    "totalCount": 1,
                    "decisionCounts": {"accepted": 1, "replayed": 0},
                },
            )
        ),
        encoding="utf-8",
    )
    scheduled_proof.write_text(json.dumps(_valid_scheduled_worker_proof()), encoding="utf-8")
    monkeypatch.setenv(MANIFEST_ENV, str(manifest))
    monkeypatch.setenv(LIVE_PROOF_ENV, str(live_proof))
    monkeypatch.setenv(SCHEDULED_WORKER_PROOF_ENV, str(scheduled_proof))
    monkeypatch.setenv(CORE_BASE_URL_ENV, "http://localhost:8310")
    monkeypatch.setenv(DATABASE_URL_ENV, "postgresql://localhost/lotus_idea")

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        source_ingestion_live_proof_ref="output/source-ingestion/live-proof.json",
        source_ingestion_scheduled_worker_proof_ref=(
            "output/source-ingestion/scheduled-worker-proof.json"
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
    assert "output/source-ingestion/scheduled-worker-proof.json" in (source_ingestion.evidence_refs)
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_implementation_proof_readiness_uses_runtime_trust_telemetry_proof_without_mesh_certification() -> (
    None
):
    proof_ref = "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json"
    proof = _bound_aggregate_proof(
        build_runtime_trust_telemetry_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        runtime_trust_telemetry_proof=proof,
        runtime_trust_telemetry_proof_ref=proof_ref,
    )

    assert "runtime_candidate_snapshot_missing" not in snapshot.overall_blockers
    assert "certified_runtime_trust_telemetry_missing" not in snapshot.overall_blockers
    assert "data_mesh_runtime_telemetry_not_certified" not in snapshot.overall_blockers
    assert "durable_repository_not_configured" in snapshot.overall_blockers
    assert "platform_mesh_certification_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_implementation_proof_readiness_uses_ai_lineage_store_proof_without_runtime_claim() -> None:
    proof_ref = "output/ai/ai-lineage-store-proof.json"
    proof = _bound_aggregate_proof(
        build_ai_lineage_store_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
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


def test_implementation_proof_readiness_uses_ai_workflow_pack_registration_proof_without_runtime_claim(
    tmp_path: Path,
) -> None:
    proof_ref = "output/ai/ai-workflow-pack-registration-proof.json"
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

    assert "workflow_pack_runtime_contract_not_certified" not in snapshot.overall_blockers
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
    assert "workflow_pack_runtime_contract_not_certified" not in ai_explanation.blockers
    assert "lotus_ai_runtime_execution_missing" in ai_explanation.blockers
    assert "output/ai/ai-workflow-pack-registration-proof.json" in (ai_explanation.evidence_refs)


def test_implementation_proof_readiness_uses_ai_workflow_pack_runtime_execution_proof_without_publication_claim(
    tmp_path: Path,
) -> None:
    proof_ref = "output/ai/ai-workflow-pack-runtime-execution-proof.json"
    proof = _bound_aggregate_proof(
        build_ai_workflow_pack_runtime_execution_proof_payload(
            generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            lotus_ai_root=write_lotus_ai_workflow_pack_runtime_execution_fixture(tmp_path),
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
    assert "workflow_pack_runtime_contract_not_certified" in ai_explanation.blockers
    assert "output/ai/ai-workflow-pack-runtime-execution-proof.json" in (
        ai_explanation.evidence_refs
    )


def test_implementation_proof_readiness_uses_ai_model_risk_operations_proof_without_product_claim() -> (
    None
):
    proof_ref = "output/ai/ai-model-risk-operations-proof.json"
    proof = _bound_aggregate_proof(
        build_ai_model_risk_operations_proof_payload(
            generated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 26, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        ai_model_risk_operations_proof=proof,
        ai_model_risk_operations_proof_ref=proof_ref,
    )

    assert "model_risk_operations_dashboard_not_certified" not in snapshot.overall_blockers
    assert "model_risk_operations_alerts_not_certified" not in snapshot.overall_blockers
    assert "lotus_ai_runtime_execution_missing" in snapshot.overall_blockers
    assert "certified_runtime_trust_telemetry_missing" in snapshot.overall_blockers
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
    assert "model_risk_operations_dashboard_not_certified" not in ai_explanation.blockers
    assert "model_risk_operations_alerts_not_certified" not in ai_explanation.blockers
    assert "output/ai/ai-model-risk-operations-proof.json" in ai_explanation.evidence_refs


def test_implementation_proof_readiness_uses_workbench_read_path_proof_without_promotion() -> None:
    proof_ref = "output/workbench/workbench-read-path-proof.json"
    proof = _bound_aggregate_proof(
        build_workbench_read_path_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        workbench_read_path_proof=proof,
        workbench_read_path_proof_ref=proof_ref,
    )

    assert "workbench_gateway_bff_consumption_proof_missing" not in snapshot.overall_blockers
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
    assert "workbench_gateway_bff_consumption_proof_missing" not in workbench.blockers
    assert "workbench_panel_missing" in workbench.blockers
    assert "output/workbench/workbench-read-path-proof.json" in workbench.evidence_refs


def test_readiness_uses_outbox_broker_proof_without_support_promotion() -> None:
    proof_ref = "output/outbox/outbox-broker-proof.json"
    proof = _bound_aggregate_proof(
        build_outbox_broker_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_broker_proof=proof,
        outbox_broker_proof_ref=proof_ref,
    )

    assert "outbox_broker_not_configured" not in snapshot.overall_blockers
    assert "external_broker_runtime_proof_missing" not in snapshot.overall_blockers
    assert "downstream_consumer_runtime_proof_missing" in snapshot.overall_blockers
    assert "platform_mesh_event_publication_proof_missing" in snapshot.overall_blockers
    assert "gateway_workbench_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    assert "outbox_broker_not_configured" not in outbox_delivery.blockers
    assert "external_broker_runtime_proof_missing" not in outbox_delivery.blockers
    assert "downstream_consumer_runtime_proof_missing" in outbox_delivery.blockers
    assert "platform_mesh_event_publication_proof_missing" in outbox_delivery.blockers
    assert "gateway_workbench_proof_missing" in outbox_delivery.blockers
    assert "supported_feature_promotion_missing" in outbox_delivery.blockers
    assert "output/outbox/outbox-broker-proof.json" in outbox_delivery.evidence_refs


def test_implementation_proof_readiness_uses_platform_mesh_onboarding_proof_without_certification(
    tmp_path: Path,
) -> None:
    proof_ref = "output/data-mesh/platform-mesh-onboarding-proof.json"
    proof = _bound_aggregate_proof(
        build_platform_mesh_onboarding_proof_payload(
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
        platform_mesh_onboarding_proof=proof,
        platform_mesh_onboarding_proof_ref=proof_ref,
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
    assert "output/data-mesh/platform-mesh-onboarding-proof.json" in data_mesh.evidence_refs
    assert "output/data-mesh/platform-mesh-onboarding-proof.json" in (
        runtime_telemetry.evidence_refs
    )


def test_implementation_proof_readiness_uses_mesh_policy_proof_without_certification() -> None:
    proof_ref = "output/data-mesh/mesh-policy-proof.json"
    proof = _bound_aggregate_proof(
        build_mesh_policy_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        mesh_policy_proof=proof,
        mesh_policy_proof_ref=proof_ref,
    )

    assert "mesh_slo_policy_certification_missing" not in snapshot.overall_blockers
    assert "mesh_access_policy_certification_missing" not in snapshot.overall_blockers
    assert "mesh_evidence_policy_certification_missing" not in snapshot.overall_blockers
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
    assert "mesh_slo_policy_certification_missing" not in data_mesh.blockers
    assert "mesh_access_policy_certification_missing" not in data_mesh.blockers
    assert "mesh_evidence_policy_certification_missing" not in data_mesh.blockers
    assert "data_mesh_not_certified" in data_mesh.blockers
    assert "output/data-mesh/mesh-policy-proof.json" in data_mesh.evidence_refs
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_readiness_uses_report_intake_route_proof_without_materialization() -> None:
    proof_ref = "output/downstream/report-intake-route-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_intake_route_proof=_bound_aggregate_proof(
            _valid_report_intake_route_proof(),
            proof_ref,
        ),
        report_intake_route_proof_ref=proof_ref,
    )

    assert "lotus_report_live_intake_route_proof_missing" not in snapshot.overall_blockers
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
    assert "lotus_report_live_intake_route_proof_missing" not in downstream.blockers
    assert "report_evidence_pack_live_materialization_proof_missing" in downstream.blockers
    assert "rendered_output_creation_missing" in downstream.blockers
    assert "archive_record_creation_missing" in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert "output/downstream/report-intake-route-proof.json" in downstream.evidence_refs


def test_implementation_proof_readiness_uses_advise_and_manage_route_proofs_without_authority() -> (
    None
):
    advise_proof_ref = "output/downstream/advise-proposal-route-proof.json"
    manage_proof_ref = "output/downstream/manage-action-route-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        advise_proposal_route_proof=_bound_aggregate_proof(
            valid_advise_route_proof(),
            advise_proof_ref,
        ),
        advise_proposal_route_proof_ref=advise_proof_ref,
        manage_action_route_proof=_bound_aggregate_proof(
            valid_manage_route_proof(),
            manage_proof_ref,
        ),
        manage_action_route_proof_ref=manage_proof_ref,
    )

    assert "advise_live_contract_proof_missing" not in snapshot.overall_blockers
    assert "manage_live_contract_proof_missing" not in snapshot.overall_blockers
    assert "suitability_policy_authority_remains_lotus_advise" in snapshot.overall_blockers
    assert "rebalance_execution_authority_remains_lotus_manage" in snapshot.overall_blockers
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "advise_live_contract_proof_missing" not in downstream.blockers
    assert "manage_live_contract_proof_missing" not in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert "output/downstream/advise-proposal-route-proof.json" in downstream.evidence_refs
    assert "output/downstream/manage-action-route-proof.json" in downstream.evidence_refs


def test_implementation_proof_readiness_uses_report_materialization_proof_without_publication() -> (
    None
):
    report_intake_proof_ref = "output/downstream/report-intake-route-proof.json"
    report_materialization_proof_ref = "output/downstream/report-materialization-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        report_intake_route_proof=_bound_aggregate_proof(
            _valid_report_intake_route_proof(),
            report_intake_proof_ref,
        ),
        report_intake_route_proof_ref=report_intake_proof_ref,
        report_materialization_proof=_bound_aggregate_proof(
            _valid_report_materialization_proof(),
            report_materialization_proof_ref,
        ),
        report_materialization_proof_ref=report_materialization_proof_ref,
    )

    assert "lotus_report_live_intake_route_proof_missing" not in snapshot.overall_blockers
    assert "report_evidence_pack_live_materialization_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "rendered_output_creation_missing" not in snapshot.overall_blockers
    assert "archive_record_creation_missing" not in snapshot.overall_blockers
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
    assert "report_evidence_pack_live_materialization_proof_missing" not in downstream.blockers
    assert "rendered_output_creation_missing" not in downstream.blockers
    assert "archive_record_creation_missing" not in downstream.blockers
    assert "client_publication_authority_blocked" in downstream.blockers
    assert "output/downstream/report-materialization-proof.json" in downstream.evidence_refs


def test_implementation_proof_readiness_rejects_naive_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        build_implementation_proof_readiness_snapshot(
            evaluated_at_utc=datetime(2026, 6, 21, 10, 10),
            repository=InMemoryIdeaRepository(),
            durable_storage_backed=False,
        )


def test_implementation_proof_readiness_rejects_invalid_supported_features_shape(
    tmp_path: Path,
) -> None:
    supported_features_path = tmp_path / "supported-features"
    supported_features_path.mkdir()
    registry_path = supported_features_path / "supported-features.json"
    registry_path.write_text(
        '{"features": {}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="supported features must be a list"):
        _supported_feature_count(registry_path)


def _valid_scheduled_worker_proof() -> dict[str, object]:
    plan = source_ingestion_worker_plan_from_manifest(
        {
            "schemaVersion": MANIFEST_SCHEMA_VERSION,
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
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        check_summary=summary,
        scheduler_entrypoint_present=True,
        run_once_worker_entrypoint_present=True,
        docker_compose_service_present=True,
    )


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


def _valid_report_materialization_proof() -> dict[str, object]:
    return {
        "schemaVersion": REPORT_MATERIALIZATION_PROOF_SCHEMA_VERSION,
        "repository": "lotus-idea",
        "generatedAtUtc": "2026-06-27T00:00:00+00:00",
        "proofType": "lotus_report_idea_evidence_materialization_contract",
        "proofScope": "source_safe_report_render_archive_materialization",
        "reportMaterializationProofValid": True,
        "aggregateBlockersCleared": REPORT_MATERIALIZATION_BLOCKERS_CLEARED,
        "evidenceRefs": REQUIRED_REPORT_MATERIALIZATION_EVIDENCE_REFS,
        "targetRoute": REPORT_MATERIALIZATION_ROUTE,
        "proofChecks": {
            "timezoneAwareGeneratedAtUtc": True,
            "fileEvidencePresent": True,
            "reportContractProvesMaterialization": True,
            "reportContractPreservesNonProofBoundaries": True,
            "reportContractRetainsPublicationBlocker": True,
        },
        "remainingCertificationBlockers": REMAINING_REPORT_MATERIALIZATION_BLOCKERS,
        "reportMaterializationProven": True,
        "renderedOutputCreated": True,
        "archiveRecordCreated": True,
        "clientPublicationAuthorityGranted": False,
        "supportedFeaturePromoted": False,
        "proofClosed": False,
    }
