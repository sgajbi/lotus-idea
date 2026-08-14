from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from app.application.data_mesh.platform_catalog_source_contract import (
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PRODUCER_PRODUCTS,
)

CANDIDATE_PRODUCT_ID = "lotus-idea:IdeaCandidate:v1"
SOURCE_MANIFEST_REF = (
    "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
)
CATALOG_REF = "generated/domain-product-catalog.json"
DEPENDENCY_GRAPH_REF = "generated/domain-product-dependency-graph.json"
MATURITY_MATRIX_REF = "generated/enterprise-mesh-maturity-matrix.json"
HANDOFF_REF = "docs/operations/enterprise-mesh-completion-handoff.md"


@dataclass(frozen=True)
class PlatformMeshFixturePaths:
    platform_root: Path
    source_manifest: Path
    catalog: Path
    dependency_graph: Path
    maturity_matrix: Path
    handoff: Path


def write_platform_mesh_fixture(tmp_path: Path) -> Path:
    platform_root = tmp_path / "lotus-platform"
    paths = _platform_mesh_fixture_paths(platform_root)
    _ensure_fixture_directories(paths)
    _write_json(paths.source_manifest, _source_manifest_payload())
    _write_json(paths.catalog, _catalog_payload())
    _write_json(paths.dependency_graph, _dependency_graph_payload())
    _write_json(paths.maturity_matrix, _maturity_matrix_payload())
    paths.handoff.write_text("lotus-idea future-wave onboarding proof\n", encoding="utf-8")
    return platform_root


def _platform_mesh_fixture_paths(platform_root: Path) -> PlatformMeshFixturePaths:
    return PlatformMeshFixturePaths(
        platform_root=platform_root,
        source_manifest=platform_root / SOURCE_MANIFEST_REF,
        catalog=platform_root / CATALOG_REF,
        dependency_graph=platform_root / DEPENDENCY_GRAPH_REF,
        maturity_matrix=platform_root / MATURITY_MATRIX_REF,
        handoff=platform_root / HANDOFF_REF,
    )


def _ensure_fixture_directories(paths: PlatformMeshFixturePaths) -> None:
    for directory in {
        paths.source_manifest.parent,
        paths.catalog.parent,
        paths.handoff.parent,
    }:
        directory.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _source_manifest_payload() -> dict[str, object]:
    return {
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


def _catalog_payload() -> dict[str, object]:
    return {
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


def _dependency_graph_payload() -> dict[str, object]:
    return {"contract_id": "lotus-domain-product-dependency-graph"}


def _maturity_matrix_payload() -> dict[str, object]:
    return {
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
                "classification": _product_classification(product_id),
                "maturity_wave": _product_maturity_wave(product_id),
                "lifecycle_status": "proposed",
            }
            for product_id in REQUIRED_PRODUCER_PRODUCTS
        ],
    }


def _product_classification(product_id: str) -> str:
    return "certification_candidate" if product_id == CANDIDATE_PRODUCT_ID else "deferred"


def _product_maturity_wave(product_id: str) -> str:
    if product_id == CANDIDATE_PRODUCT_ID:
        return "enterprise_wave_candidate"
    return "future_wave"
