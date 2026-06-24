from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.platform_mesh_onboarding_proof import (
    PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED,
    PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION,
    REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS,
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PLATFORM_MESH_EVIDENCE_REFS,
    REQUIRED_PRODUCER_PRODUCTS,
    build_platform_mesh_onboarding_proof_payload,
    platform_mesh_onboarding_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[2]


def test_builds_source_safe_platform_mesh_onboarding_proof(tmp_path: Path) -> None:
    proof = _valid_platform_mesh_onboarding_proof(tmp_path)

    assert proof["schemaVersion"] == PLATFORM_MESH_ONBOARDING_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "platform_mesh_onboarding_contract"
    assert proof["proofScope"] == "platform_source_manifest_and_catalog_inclusion"
    assert proof["platformMeshOnboardingProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == PLATFORM_MESH_ONBOARDING_BLOCKERS_CLEARED
    assert tuple(proof["evidenceRefs"]) == REQUIRED_PLATFORM_MESH_EVIDENCE_REFS
    assert proof["producerProductCount"] == len(REQUIRED_PRODUCER_PRODUCTS)
    assert proof["consumerDependencyCount"] == len(REQUIRED_CONSUMER_DEPENDENCIES)
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_PLATFORM_MESH_ONBOARDING_BLOCKERS
    )
    assert proof["platformMeshCertified"] is False
    assert proof["producerProductsActive"] is False
    assert proof["gatewayWorkbenchDiscoveryCertified"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert platform_mesh_onboarding_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def test_rejects_platform_mesh_onboarding_proof_when_platform_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_platform_mesh_onboarding_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=tmp_path,
    )

    assert proof["platformMeshOnboardingProofValid"] is False
    assert platform_mesh_onboarding_proof_is_valid(proof) is False


def test_rejects_platform_mesh_onboarding_proof_with_naive_timestamp(tmp_path: Path) -> None:
    proof = build_platform_mesh_onboarding_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0),
        repository_root=ROOT,
        platform_root=_write_platform_fixture(tmp_path),
    )

    assert proof["platformMeshOnboardingProofValid"] is False
    assert platform_mesh_onboarding_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "mesh"),
        ("proofScope", "certified"),
        ("platformMeshOnboardingProofValid", False),
        ("platformMeshCertified", True),
        ("producerProductsActive", True),
        ("gatewayWorkbenchDiscoveryCertified", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_platform_mesh_onboarding_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_platform_mesh_onboarding_proof(tmp_path)
    proof[field_name] = bad_value

    assert platform_mesh_onboarding_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("aggregateBlockersCleared", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("proofChecks", []),
        ("producerProductCount", 0),
        ("consumerDependencyCount", 0),
    ],
)
def test_rejects_platform_mesh_onboarding_proof_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_platform_mesh_onboarding_proof(tmp_path)
    proof[field_name] = bad_value

    assert platform_mesh_onboarding_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "platformSourceManifestIncludesIdea",
        "platformCatalogIncludesIdeaProducts",
        "platformCatalogIncludesIdeaConsumer",
        "platformMaturityKeepsIdeaDeferred",
    ],
)
def test_rejects_platform_mesh_onboarding_proof_with_invalid_proof_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_platform_mesh_onboarding_proof(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert platform_mesh_onboarding_proof_is_valid(proof) is False


def test_platform_mesh_onboarding_proof_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    platform_root = _write_platform_fixture(tmp_path)
    output_path = tmp_path / "proof" / "platform-mesh-onboarding-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--platform-root",
            str(platform_root),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert platform_mesh_onboarding_proof_is_valid(proof) is True


def test_platform_mesh_onboarding_proof_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def _valid_platform_mesh_onboarding_proof(tmp_path: Path) -> dict[str, Any]:
    return build_platform_mesh_onboarding_proof_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=_write_platform_fixture(tmp_path),
    )


def _write_platform_fixture(tmp_path: Path) -> Path:
    platform_root = tmp_path / "lotus-platform"
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
    source_manifest_path.write_text(json.dumps(_source_manifest_payload()), encoding="utf-8")
    catalog_path.write_text(json.dumps(_catalog_payload()), encoding="utf-8")
    graph_path.write_text(
        '{"contract_id":"lotus-domain-product-dependency-graph"}', encoding="utf-8"
    )
    maturity_path.write_text(json.dumps(_maturity_payload()), encoding="utf-8")
    handoff_path.write_text("lotus-idea future-wave onboarding proof\n", encoding="utf-8")
    return platform_root


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


def _maturity_payload() -> dict[str, object]:
    return {
        "repositories": [
            {
                "repository": "lotus-idea",
                "classification": "deferred",
                "mesh_role": "producer",
            }
        ],
        "products": [
            {
                "product_id": product_id,
                "classification": "deferred",
                "maturity_wave": "future_wave",
                "lifecycle_status": "proposed",
            }
            for product_id in REQUIRED_PRODUCER_PRODUCTS
        ],
    }


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "generate_platform_mesh_onboarding_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_platform_mesh_onboarding_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "platform_mesh_onboarding_proof_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "platform_mesh_onboarding_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
