from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.outbox.broker.source_contract_proof import (
    build_outbox_broker_source_contract_proof_payload,
)
from app.application.outbox.consumer_contract_proof import (
    build_outbox_consumer_contract_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof

ROOT = Path(__file__).resolve().parents[2]


def test_consumer_contract_proof_adds_evidence_without_clearing_runtime_blocker() -> None:
    broker_proof_ref = "output/outbox/broker/source-contract-proof.json"
    consumer_proof_ref = "output/outbox/outbox-consumer-contract-proof.json"
    broker_proof = bound_aggregate_proof(
        build_outbox_broker_source_contract_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        broker_proof_ref,
    )
    consumer_proof = bound_aggregate_proof(
        build_outbox_consumer_contract_proof_payload(
            generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
            repository_root=ROOT,
        ),
        consumer_proof_ref,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_broker_source_contract_proof=broker_proof,
        outbox_broker_source_contract_proof_ref=broker_proof_ref,
        outbox_consumer_contract_proof=consumer_proof,
        outbox_consumer_contract_proof_ref=consumer_proof_ref,
    )

    assert "outbox_broker_not_configured" in snapshot.overall_blockers
    assert "external_broker_runtime_proof_missing" in snapshot.overall_blockers
    assert "downstream_consumer_runtime_proof_missing" in snapshot.overall_blockers
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
    assert "outbox_broker_not_configured" in outbox_delivery.blockers
    assert "external_broker_runtime_proof_missing" in outbox_delivery.blockers
    assert "downstream_consumer_runtime_proof_missing" in outbox_delivery.blockers
    assert "platform_mesh_event_publication_proof_missing" in outbox_delivery.blockers
    assert "gateway_workbench_proof_missing" in outbox_delivery.blockers
    assert "supported_feature_promotion_missing" in outbox_delivery.blockers
    assert "output/outbox/outbox-consumer-contract-proof.json" in outbox_delivery.evidence_refs
    assert broker_proof_ref in outbox_delivery.evidence_refs


def test_runtime_class_forgery_is_not_consumed_as_consumer_contract_evidence() -> None:
    proof_ref = "output/outbox/outbox-consumer-contract-proof.json"
    payload = build_outbox_consumer_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    payload["evidenceClass"] = "runtime_execution"
    proof = bound_aggregate_proof(payload, proof_ref)

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        outbox_consumer_contract_proof=proof,
        outbox_consumer_contract_proof_ref=proof_ref,
    )

    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    assert "downstream_consumer_runtime_proof_missing" in outbox_delivery.blockers
    assert proof_ref not in outbox_delivery.evidence_refs
