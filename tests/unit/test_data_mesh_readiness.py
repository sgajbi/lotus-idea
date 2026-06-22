from __future__ import annotations

from pathlib import Path
import json
from typing import Any

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
        "certified_runtime_trust_telemetry_missing",
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


def test_data_mesh_readiness_snapshot_rejects_invalid_source_truth(tmp_path: Path) -> None:
    _write_contracts(tmp_path, readiness_overrides={"source_of_truth": []})

    with pytest.raises(ValueError, match="source_of_truth"):
        build_data_mesh_readiness_snapshot(repository_root=tmp_path)


def test_data_mesh_readiness_snapshot_rejects_invalid_product_list(tmp_path: Path) -> None:
    _write_contracts(tmp_path, producer_overrides={"products": {}})

    with pytest.raises(ValueError, match="products must be a list"):
        build_data_mesh_readiness_snapshot(repository_root=tmp_path)


def _write_contracts(
    repository_root: Path,
    *,
    producer_overrides: dict[str, object] | None = None,
    readiness_overrides: dict[str, object] | None = None,
) -> None:
    producer = {
        "products": [
            {
                "product_name": "IdeaCandidate",
                "product_version": "v1",
                "lifecycle_status": "proposed",
                "approved_consumers": ["lotus-gateway"],
            }
        ]
    } | (producer_overrides or {})
    readiness = {
        "repository": "lotus-idea",
        "lifecycle_status": "planned",
        "certification_status": "not_certified",
        "mesh_role": "planned_producer_and_consumer",
        "source_of_truth": {
            "producer_declaration": "contracts/domain-data-products/lotus-idea-products.v1.json",
        },
        "certification_gates_before_promotion": ["runtime telemetry"],
    } | (readiness_overrides or {})
    telemetry = {"blocking": {"blocked": True}}

    _write_json(
        repository_root / "contracts/domain-data-products/lotus-idea-products.v1.json",
        producer,
    )
    _write_json(
        repository_root / "contracts/domain-data-products/mesh-readiness.v1.json",
        readiness,
    )
    _write_json(
        repository_root / "contracts/trust-telemetry/idea-candidate.telemetry.v1.json",
        telemetry,
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
