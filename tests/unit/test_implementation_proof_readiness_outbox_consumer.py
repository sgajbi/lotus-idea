from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.outbox_broker_proof import build_outbox_broker_proof_payload
from app.application.outbox_consumer_runtime_proof import (
    build_outbox_consumer_runtime_proof_payload,
)
from app.domain import InMemoryIdeaRepository

ROOT = Path(__file__).resolve().parents[2]


def test_implementation_proof_readiness_uses_outbox_consumer_runtime_proof_boundary() -> None:
    broker_proof = build_outbox_broker_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    consumer_proof = build_outbox_consumer_runtime_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_broker_proof=broker_proof,
        outbox_broker_proof_ref="output/outbox/outbox-broker-proof.json",
        outbox_consumer_runtime_proof=consumer_proof,
        outbox_consumer_runtime_proof_ref="output/outbox/outbox-consumer-runtime-proof.json",
    )

    assert "outbox_broker_not_configured" not in snapshot.overall_blockers
    assert "external_broker_runtime_proof_missing" not in snapshot.overall_blockers
    assert "downstream_consumer_runtime_proof_missing" not in snapshot.overall_blockers
    assert "platform_mesh_event_publication_proof_missing" in snapshot.overall_blockers
    assert "gateway_workbench_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    assert "downstream_consumer_runtime_proof_missing" not in outbox_delivery.blockers
    assert "platform_mesh_event_publication_proof_missing" in outbox_delivery.blockers
    assert "gateway_workbench_proof_missing" in outbox_delivery.blockers
    assert "supported_feature_promotion_missing" in outbox_delivery.blockers
    assert "output/outbox/outbox-consumer-runtime-proof.json" in outbox_delivery.evidence_refs
