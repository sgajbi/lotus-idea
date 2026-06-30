from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.application.gateway_workbench_operational_proof import (
    build_gateway_workbench_operational_proof_payload,
)
from app.application.implementation_proof_capability_updates import (
    build_capability_readiness,
)
from app.application.implementation_proof_readiness import (
    _apply_gateway_workbench_operational_proof,
    build_implementation_proof_readiness_snapshot,
)
from app.application.workbench_read_path_proof import build_workbench_read_path_proof_payload
from app.domain import InMemoryIdeaRepository


ROOT = Path(__file__).resolve().parents[2]


def test_gateway_workbench_operational_proof_application_is_noop_for_other_capability() -> None:
    capability = build_capability_readiness(
        "workbench-product-proof",
        "Workbench product realization",
        readiness_status="blocked",
        supportability_status="not_certified",
        evidence_refs=("existing-proof.json",),
        blockers=("gateway_workbench_proof_missing", "workbench_panel_missing"),
    )

    result = _apply_gateway_workbench_operational_proof(
        capability,
        "output/workbench/gateway-workbench-operational-proof.json",
    )

    assert result is capability


def test_readiness_uses_gateway_workbench_operational_proof_without_support_promotion() -> None:
    proof = _valid_gateway_workbench_operational_proof()

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        gateway_workbench_operational_proof=proof,
        gateway_workbench_operational_proof_ref=(
            "output/workbench/gateway-workbench-operational-proof.json"
        ),
    )

    assert "gateway_workbench_proof_missing" not in snapshot.overall_blockers
    assert "workbench_product_proof_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "gateway_workbench_discovery_proof_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    source_ingestion = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "source-ingestion"
    )
    outbox_delivery = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "outbox-delivery"
    )
    workbench = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "workbench-product-proof"
    )
    assert "gateway_workbench_proof_missing" not in source_ingestion.blockers
    assert "gateway_workbench_proof_missing" not in outbox_delivery.blockers
    assert "workbench_panel_missing" in workbench.blockers
    assert "output/workbench/gateway-workbench-operational-proof.json" in (
        source_ingestion.evidence_refs
    )
    assert "output/workbench/gateway-workbench-operational-proof.json" in (
        outbox_delivery.evidence_refs
    )
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_gateway_workbench_operational_proof() -> dict[str, object]:
    workbench_read_path_proof = build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    return build_gateway_workbench_operational_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_read_path_proof=workbench_read_path_proof,
        workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
    )
