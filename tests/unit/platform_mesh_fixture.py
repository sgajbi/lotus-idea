from __future__ import annotations

import json
from pathlib import Path

from app.application.data_mesh.platform_catalog_source_contract import (
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PRODUCER_PRODUCTS,
)


def write_platform_mesh_fixture(tmp_path: Path) -> Path:
    platform_root = tmp_path / "lotus-platform"
    candidate_product_id = "lotus-idea:IdeaCandidate:v1"
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
                        "classification": "certification_candidate",
                        "mesh_role": "producer",
                        "first_wave_product_count": 0,
                        "required_next_step": (
                            "Complete source-safe runtime trust telemetry, "
                            "certification evidence, and supported-feature promotion "
                            "before activation."
                        ),
                    }
                ],
                "products": [
                    {
                        "product_id": product_id,
                        "classification": (
                            "certification_candidate"
                            if product_id == candidate_product_id
                            else "deferred"
                        ),
                        "maturity_wave": (
                            "enterprise_wave_candidate"
                            if product_id == candidate_product_id
                            else "future_wave"
                        ),
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
