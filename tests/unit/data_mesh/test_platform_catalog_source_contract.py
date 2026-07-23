from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.application.data_mesh.platform_catalog_source_contract import (
    PLATFORM_CATALOG_SOURCE_BLOCKERS_SATISFIED,
    PLATFORM_CATALOG_SOURCE_CONTRACT_SCHEMA_VERSION,
    REMAINING_PLATFORM_CATALOG_CERTIFICATION_BLOCKERS,
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PLATFORM_CATALOG_EVIDENCE_REFS,
    REQUIRED_PRODUCER_PRODUCTS,
    _catalog_includes_idea_consumer,
    _catalog_includes_idea_products,
    _maturity_matrix_keeps_idea_unpromoted,
    _source_manifest_includes_idea,
    build_platform_catalog_source_contract_payload,
    platform_catalog_source_contract_is_valid,
)
from app.domain.proof_evidence import EvidenceClass

ROOT = Path(__file__).resolve().parents[3]


def test_builds_source_safe_platform_catalog_source_contract(tmp_path: Path) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)

    assert proof["schemaVersion"] == PLATFORM_CATALOG_SOURCE_CONTRACT_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "platform_catalog_source_contract"
    assert proof["proofScope"] == "platform_source_manifest_catalog_and_deferred_maturity"
    assert proof["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert proof["sourceContractValid"] is True
    assert tuple(proof["sourceContractBlockersSatisfied"]) == (
        PLATFORM_CATALOG_SOURCE_BLOCKERS_SATISFIED
    )
    assert tuple(proof["evidenceRefs"]) == REQUIRED_PLATFORM_CATALOG_EVIDENCE_REFS
    assert len(proof["sourceAuthority"]) == 4
    assert all(len(source["sha256"]) == 64 for source in proof["sourceAuthority"])
    assert proof["producerProductCount"] == len(REQUIRED_PRODUCER_PRODUCTS)
    assert proof["consumerDependencyCount"] == len(REQUIRED_CONSUMER_DEPENDENCIES)
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_PLATFORM_CATALOG_CERTIFICATION_BLOCKERS
    )
    assert proof["platformMeshCertified"] is False
    assert proof["producerProductsActive"] is False
    assert proof["gatewayWorkbenchDiscoveryCertified"] is False
    assert proof["platformRuntimePublicationObserved"] is False
    assert proof["productionCertificationGranted"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["certificationClosed"] is False
    assert platform_catalog_source_contract_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def test_rejects_platform_catalog_source_contract_when_platform_evidence_is_missing(
    tmp_path: Path,
) -> None:
    proof = build_platform_catalog_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=tmp_path,
    )

    assert proof["sourceContractValid"] is False
    assert platform_catalog_source_contract_is_valid(proof) is False


def test_rejects_platform_catalog_source_contract_with_naive_timestamp(tmp_path: Path) -> None:
    proof = build_platform_catalog_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0),
        repository_root=ROOT,
        platform_root=_write_platform_fixture(tmp_path),
    )

    assert proof["sourceContractValid"] is False
    assert platform_catalog_source_contract_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "mesh"),
        ("proofScope", "certified"),
        ("sourceContractValid", False),
        ("evidenceClass", "runtime_execution"),
        ("platformRuntimePublicationObserved", True),
        ("platformMeshCertified", True),
        ("producerProductsActive", True),
        ("gatewayWorkbenchDiscoveryCertified", True),
        ("productionCertificationGranted", True),
        ("supportedFeaturePromoted", True),
        ("certificationClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
        ("generatedAtUtc", None),
    ],
)
def test_rejects_platform_catalog_source_contract_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    proof[field_name] = bad_value

    assert platform_catalog_source_contract_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("sourceContractBlockersSatisfied", []),
        ("evidenceRefs", []),
        ("remainingCertificationBlockers", []),
        ("contractChecks", []),
        ("producerProductCount", 0),
        ("consumerDependencyCount", 0),
        ("sourceAuthority", []),
    ],
)
def test_rejects_platform_catalog_source_contract_with_invalid_contract_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    proof[field_name] = bad_value

    assert platform_catalog_source_contract_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "sourceAuthorityDigestBound",
        "platformSourceManifestIncludesIdea",
        "platformCatalogIncludesIdeaProducts",
        "platformCatalogIncludesIdeaConsumer",
        "platformMaturityKeepsIdeaUnpromoted",
    ],
)
def test_rejects_platform_catalog_source_contract_with_invalid_proof_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["contractChecks"]))
    proof_checks[check_name] = False
    proof["contractChecks"] = proof_checks

    assert platform_catalog_source_contract_is_valid(proof) is False


def test_rejects_platform_catalog_source_contract_claim_inflation(tmp_path: Path) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    proof["runtimePublicationReceipt"] = {"status": "published"}

    assert platform_catalog_source_contract_is_valid(proof) is False


def test_rejects_unknown_contract_check(tmp_path: Path) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    checks = dict(cast(Mapping[str, object], proof["contractChecks"]))
    checks["runtimePublicationObserved"] = True
    proof["contractChecks"] = checks

    assert platform_catalog_source_contract_is_valid(proof) is False


@pytest.mark.parametrize("field_name", ["repository", "ref", "sha256"])
def test_rejects_source_authority_substitution(field_name: str, tmp_path: Path) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    source_authority = [dict(item) for item in proof["sourceAuthority"]]
    source_authority[0][field_name] = {
        "repository": "lotus-risk",
        "ref": "../lotus-platform/generated/other.json",
        "sha256": "not-a-sha256",
    }[field_name]
    proof["sourceAuthority"] = source_authority

    assert platform_catalog_source_contract_is_valid(proof) is False


def test_rejects_malformed_source_authority_entry(tmp_path: Path) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    source_authority = list(proof["sourceAuthority"])
    source_authority[0] = "../lotus-platform/generated/domain-product-catalog.json"
    proof["sourceAuthority"] = source_authority

    assert platform_catalog_source_contract_is_valid(proof) is False


def test_rejects_non_hex_source_authority_digest(tmp_path: Path) -> None:
    proof = _valid_platform_catalog_source_contract(tmp_path)
    source_authority = [dict(item) for item in proof["sourceAuthority"]]
    source_authority[0]["sha256"] = "z" * 64
    proof["sourceAuthority"] = source_authority

    assert platform_catalog_source_contract_is_valid(proof) is False


def test_source_authority_digest_changes_with_catalog_content(tmp_path: Path) -> None:
    platform_root = _write_platform_fixture(tmp_path)
    original = build_platform_catalog_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=platform_root,
    )
    catalog_path = platform_root / "generated/domain-product-catalog.json"
    catalog_path.write_text(
        json.dumps({**_catalog_payload(), "sourceRevision": "changed"}),
        encoding="utf-8",
    )
    changed = build_platform_catalog_source_contract_payload(
        generated_at_utc=datetime(2026, 6, 24, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=platform_root,
    )

    assert original["sourceAuthority"][1]["sha256"] != (changed["sourceAuthority"][1]["sha256"])
    assert platform_catalog_source_contract_is_valid(changed) is True


def test_platform_catalog_source_contract_cli_writes_valid_artifact(tmp_path: Path) -> None:
    module = _load_generator_script()
    platform_root = _write_platform_fixture(tmp_path)
    output_path = tmp_path / "proof" / "platform-catalog-source-contract.json"

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
    assert platform_catalog_source_contract_is_valid(proof) is True


def test_platform_catalog_source_contract_cli_fails_missing_evidence_without_allow_flag(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "missing-platform-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--platform-root",
            str(tmp_path / "missing-lotus-platform"),
            "--output",
            str(output_path),
        ]
    )

    assert result == 1
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["contractChecks"]["fileEvidencePresent"] is False
    assert platform_catalog_source_contract_is_valid(proof) is False


def test_platform_catalog_source_contract_cli_allows_missing_evidence_when_requested(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    output_path = tmp_path / "proof" / "missing-platform-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--platform-root",
            str(tmp_path / "missing-lotus-platform"),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["sourceContractValid"] is False
    assert proof["contractChecks"]["fileEvidencePresent"] is False
    assert platform_catalog_source_contract_is_valid(proof) is False


def test_platform_catalog_source_contract_cli_rejects_contract_drift_with_allow_flag(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    platform_root = _write_platform_fixture(tmp_path)
    source_manifest_path = (
        platform_root
        / "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
    )
    source_manifest_path.write_text('{"repositories":[]}', encoding="utf-8")
    output_path = tmp_path / "proof" / "drifted-platform-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-24T00:00:00Z",
            "--platform-root",
            str(platform_root),
            "--output",
            str(output_path),
            "--allow-missing-evidence",
        ]
    )

    assert result == 1
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert proof["contractChecks"]["fileEvidencePresent"] is True
    assert proof["contractChecks"]["platformSourceManifestIncludesIdea"] is False
    assert platform_catalog_source_contract_is_valid(proof) is False


def test_platform_catalog_source_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("portfolio_id",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `portfolio_id` is present"]


def test_platform_catalog_source_contract_gate_allows_missing_sibling_evidence(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()

    errors = module.validate_platform_catalog_source_contract(
        platform_root=tmp_path / "missing-lotus-platform"
    )

    assert errors == []


def test_platform_catalog_source_contract_gate_rejects_present_sibling_drift(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()
    platform_root = _write_platform_fixture(tmp_path)
    source_manifest_path = (
        platform_root
        / "platform-contracts/domain-data-products/domain-product-source-manifest.v1.json"
    )
    source_manifest_path.write_text('{"repositories":[]}', encoding="utf-8")

    errors = module.validate_platform_catalog_source_contract(platform_root=platform_root)

    assert (
        "platform catalog source contract must validate against sibling platform truth "
        "when sibling evidence is present"
    ) in errors


def test_source_manifest_inclusion_skips_non_idea_entries() -> None:
    assert (
        _source_manifest_includes_idea({"repositories": ["bad", {"repository": "lotus-core"}]})
        is False
    )


@pytest.mark.parametrize(
    "catalog",
    [
        {"products": "bad"},
        {"products": []},
        {
            "products": [
                {
                    "product_id": product_id,
                    "producer_repository": "lotus-core",
                    "lifecycle_status": "proposed",
                    "current_routes": [],
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ]
        },
        {
            "products": [
                {
                    "product_id": product_id,
                    "producer_repository": "lotus-idea",
                    "lifecycle_status": "active",
                    "current_routes": [],
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ]
        },
        {
            "products": [
                {
                    "product_id": product_id,
                    "producer_repository": "lotus-idea",
                    "lifecycle_status": "proposed",
                    "current_routes": ["/api/v1/data-products"],
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ]
        },
    ],
)
def test_catalog_product_inclusion_fails_closed(catalog: dict[str, object]) -> None:
    assert _catalog_includes_idea_products(catalog) is False


def test_catalog_consumer_inclusion_skips_non_idea_entries() -> None:
    assert (
        _catalog_includes_idea_consumer(
            {"consumers": ["bad", {"consumer_repository": "lotus-core"}]}
        )
        is False
    )


def test_maturity_matrix_unpromoted_posture_accepts_single_idea_candidate() -> None:
    assert _maturity_matrix_keeps_idea_unpromoted(_maturity_payload()) is True


@pytest.mark.parametrize(
    "payload",
    [
        {"repositories": [], "products": []},
        {
            "repositories": [{"repository": "lotus-idea", "classification": "active"}],
            "products": [],
        },
        {
            "repositories": [
                {"repository": "lotus-idea", "classification": "deferred", "mesh_role": "consumer"}
            ],
            "products": [],
        },
        {
            "repositories": [
                {"repository": "lotus-idea", "classification": "deferred", "mesh_role": "producer"}
            ],
            "products": [],
        },
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "certification_candidate",
                    "mesh_role": "producer",
                    "first_wave_product_count": 1,
                    "required_next_step": "Complete promotion proof.",
                }
            ],
            "products": [],
        },
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "certification_candidate",
                    "mesh_role": "producer",
                    "first_wave_product_count": 0,
                }
            ],
            "products": [],
        },
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "certification_candidate",
                    "mesh_role": "producer",
                    "first_wave_product_count": 0,
                    "required_next_step": "Complete promotion proof.",
                }
            ],
            "products": [
                {
                    "product_id": product_id,
                    "classification": "certification_candidate",
                    "maturity_wave": "enterprise_wave_candidate",
                    "lifecycle_status": "proposed",
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ],
        },
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "certification_candidate",
                    "mesh_role": "producer",
                    "first_wave_product_count": 0,
                    "required_next_step": "Complete promotion proof.",
                }
            ],
            "products": [
                {
                    "product_id": product_id,
                    "classification": "active",
                    "maturity_wave": "future_wave",
                    "lifecycle_status": "proposed",
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ],
        },
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "certification_candidate",
                    "mesh_role": "producer",
                    "first_wave_product_count": 0,
                    "required_next_step": "Complete promotion proof.",
                }
            ],
            "products": [
                {
                    "product_id": product_id,
                    "classification": (
                        "certification_candidate"
                        if product_id == "lotus-idea:IdeaCandidate:v1"
                        else "deferred"
                    ),
                    "maturity_wave": (
                        "enterprise_wave_candidate"
                        if product_id == "lotus-idea:IdeaCandidate:v1"
                        else "current_wave"
                    ),
                    "lifecycle_status": "proposed",
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ],
        },
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "certification_candidate",
                    "mesh_role": "producer",
                    "first_wave_product_count": 0,
                    "required_next_step": "Complete promotion proof.",
                }
            ],
            "products": [
                {
                    "product_id": product_id,
                    "classification": (
                        "certification_candidate"
                        if product_id == "lotus-idea:IdeaCandidate:v1"
                        else "deferred"
                    ),
                    "maturity_wave": (
                        "enterprise_wave_candidate"
                        if product_id == "lotus-idea:IdeaCandidate:v1"
                        else "future_wave"
                    ),
                    "lifecycle_status": "active",
                }
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ],
        },
    ],
)
def test_maturity_matrix_unpromoted_posture_fails_closed(
    payload: dict[str, object],
) -> None:
    assert _maturity_matrix_keeps_idea_unpromoted(payload) is False


def _valid_platform_catalog_source_contract(tmp_path: Path) -> dict[str, Any]:
    return build_platform_catalog_source_contract_payload(
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
                "classification": "certification_candidate",
                "mesh_role": "producer",
                "first_wave_product_count": 0,
                "required_next_step": (
                    "Complete runtime telemetry, durable repository, Gateway/Workbench discovery, "
                    "and supported-feature proof before promotion."
                ),
            }
        ],
        "products": [
            {
                "product_id": product_id,
                "classification": (
                    "certification_candidate"
                    if product_id == "lotus-idea:IdeaCandidate:v1"
                    else "deferred"
                ),
                "maturity_wave": (
                    "enterprise_wave_candidate"
                    if product_id == "lotus-idea:IdeaCandidate:v1"
                    else "future_wave"
                ),
                "lifecycle_status": "proposed",
            }
            for product_id in REQUIRED_PRODUCER_PRODUCTS
        ],
    }


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts/data_mesh/generate_platform_catalog_source_contract.py"
    spec = importlib.util.spec_from_file_location(
        "generate_platform_catalog_source_contract",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts/data_mesh/platform_catalog_source_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "platform_catalog_source_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
