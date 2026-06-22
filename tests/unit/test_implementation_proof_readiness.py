from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository


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
    assert snapshot.capability_count == 8
    assert snapshot.certification_ready_capability_count == 0
    assert snapshot.blocked_capability_count == 8
    assert snapshot.supported_feature_count == 0
    assert snapshot.supported_features_promoted is False
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
    assert "platform_mesh_certification_missing" in runtime_telemetry.blockers
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "GET /api/v1/downstream-realization/readiness" in downstream.evidence_refs
    assert "report_evidence_pack_materialization_missing" in downstream.blockers
    serialized = repr(snapshot)
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "request_body" not in serialized
    assert "response_body" not in serialized


def test_implementation_proof_readiness_rejects_naive_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        build_implementation_proof_readiness_snapshot(
            evaluated_at_utc=datetime(2026, 6, 21, 10, 10),
            repository=InMemoryIdeaRepository(),
            durable_storage_backed=False,
        )
