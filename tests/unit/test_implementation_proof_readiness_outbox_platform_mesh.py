from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.outbox.platform_mesh_event_publication_proof import (
    build_outbox_platform_mesh_event_publication_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof
from tests.unit.test_implementation_proof_readiness import ROOT, _write_platform_mesh_fixture


def test_outbox_platform_mesh_event_proof_clears_only_mesh_event_blocker(
    tmp_path: Path,
) -> None:
    proof_ref = "output/outbox/outbox-platform-mesh-event-publication-proof.json"
    proof = bound_aggregate_proof(
        build_outbox_platform_mesh_event_publication_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            repository_root=ROOT,
            platform_root=_write_platform_mesh_fixture(tmp_path),
        ),
        proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_platform_mesh_event_publication_proof=proof,
        outbox_platform_mesh_event_publication_proof_ref=proof_ref,
    )

    assert "platform_mesh_event_publication_proof_missing" not in snapshot.overall_blockers
    assert "gateway_workbench_proof_missing" in snapshot.overall_blockers
    assert "supported_feature_promotion_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    assert "platform_mesh_event_publication_proof_missing" not in outbox_delivery.blockers
    assert "gateway_workbench_proof_missing" in outbox_delivery.blockers
    assert "supported_feature_promotion_missing" in outbox_delivery.blockers
    assert (
        "output/outbox/outbox-platform-mesh-event-publication-proof.json"
        in outbox_delivery.evidence_refs
    )
