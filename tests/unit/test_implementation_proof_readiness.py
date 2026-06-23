from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.application.durable_repository_proof import build_durable_repository_proof_payload
from app.application.implementation_proof_readiness import (
    _supported_feature_count,
    build_implementation_proof_readiness_snapshot,
)
from app.application.runtime_trust_telemetry_proof import (
    build_runtime_trust_telemetry_proof_payload,
)
from app.application.workbench_read_path_proof import build_workbench_read_path_proof_payload
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[2]


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
    assert snapshot.capability_count == 9
    assert snapshot.certification_ready_capability_count == 0
    assert snapshot.blocked_capability_count == 9
    assert snapshot.supported_feature_count == 0
    assert snapshot.supported_features_promoted is False
    assert "outbox_broker_not_configured" in snapshot.overall_blockers
    assert "external_broker_runtime_proof_missing" in snapshot.overall_blockers
    assert "source_ingestion_manifest_not_configured" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.source_of_truth["supported_features"] == (
        "supported-features/supported-features.json"
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
    assert "report_evidence_pack_live_materialization_proof_missing" in downstream.blockers
    serialized = repr(snapshot)
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "request_body" not in serialized
    assert "response_body" not in serialized


def test_implementation_proof_readiness_uses_durable_repository_proof_without_support_promotion() -> (
    None
):
    proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        durable_repository_proof=proof,
        durable_repository_proof_ref="output/persistence/durable-repository-proof.json",
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


def test_implementation_proof_readiness_uses_runtime_trust_telemetry_proof_without_certification() -> (
    None
):
    proof = build_runtime_trust_telemetry_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        runtime_trust_telemetry_proof=proof,
        runtime_trust_telemetry_proof_ref=(
            "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json"
        ),
    )

    assert "runtime_candidate_snapshot_missing" not in snapshot.overall_blockers
    assert "durable_repository_not_configured" in snapshot.overall_blockers
    assert "platform_mesh_certification_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    runtime_telemetry = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "runtime-trust-telemetry-preview"
    )
    assert "runtime_candidate_snapshot_missing" not in runtime_telemetry.blockers
    assert "platform_mesh_certification_missing" in runtime_telemetry.blockers
    assert (
        "output/trust-telemetry/runtime/runtime-trust-telemetry-proof.json"
        in runtime_telemetry.evidence_refs
    )


def test_implementation_proof_readiness_uses_workbench_read_path_proof_without_promotion() -> None:
    proof = build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        workbench_read_path_proof=proof,
        workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
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
