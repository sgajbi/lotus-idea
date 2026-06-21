from __future__ import annotations

from pathlib import Path

import pytest

from app.application.data_mesh_readiness import build_data_mesh_readiness_snapshot


ROOT = Path(__file__).resolve().parents[2]


def test_data_mesh_readiness_snapshot_reports_not_certified_posture() -> None:
    snapshot = build_data_mesh_readiness_snapshot(repository_root=ROOT)

    assert snapshot.repository == "lotus-idea"
    assert snapshot.lifecycle_status == "planned"
    assert snapshot.certification_status == "not_certified"
    assert snapshot.mesh_role == "planned_producer_and_consumer"
    assert snapshot.platform_certified is False
    assert snapshot.runtime_telemetry_backed is False
    assert snapshot.supported_feature_promoted is False
    assert snapshot.blockers == (
        "data_mesh_not_certified",
        "producer_products_not_active",
        "runtime_trust_telemetry_blocked",
    )
    assert snapshot.source_of_truth == {
        "producer_declaration": "contracts/domain-data-products/lotus-idea-products.v1.json",
        "consumer_declaration": "contracts/domain-data-products/lotus-idea-consumers.v1.json",
        "trust_telemetry": "contracts/trust-telemetry/idea-candidate.telemetry.v1.json",
        "slo_policy": "contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json",
        "access_policy": "contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json",
        "evidence_policy": (
            "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json"
        ),
    }


def test_data_mesh_readiness_snapshot_includes_repo_declared_products() -> None:
    snapshot = build_data_mesh_readiness_snapshot(repository_root=ROOT)
    products = {product.product_id: product for product in snapshot.products}

    assert "lotus-idea:IdeaCandidate:v1" in products
    assert "lotus-idea:IdeaTrustTelemetry:v1" in products
    assert products["lotus-idea:IdeaCandidate:v1"].lifecycle_status == "proposed"
    assert products["lotus-idea:IdeaCandidate:v1"].approved_consumers == ("lotus-gateway",)


def test_data_mesh_readiness_snapshot_fails_closed_when_contracts_are_missing(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        build_data_mesh_readiness_snapshot(repository_root=tmp_path)
