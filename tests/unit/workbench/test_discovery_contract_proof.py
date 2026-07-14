from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, cast

import pytest

from app.domain.proof_evidence import EvidenceClass
from app.application.workbench.discovery_contract_proof import (
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED,
    GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION,
    REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS,
    REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS,
    REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS,
    _catalog_declares_gateway_consumable_idea_products,
    _is_timezone_aware_datetime_text,
    _optional_json,
    _required_file_evidence_present,
    build_gateway_workbench_discovery_contract_proof_payload,
    gateway_workbench_discovery_contract_proof_is_valid,
)
from app.application.workbench.contract_proof import (
    build_gateway_workbench_contract_proof_payload,
)
from app.application.data_mesh.platform_catalog_source_contract import (
    REQUIRED_CONSUMER_DEPENDENCIES,
    REQUIRED_PRODUCER_PRODUCTS,
    build_platform_catalog_source_contract_payload,
)
from app.application.workbench.read_path_source_contract import (
    build_workbench_read_path_source_contract_proof_payload,
)


ROOT = Path(__file__).resolve().parents[3]
GENERATED_AT_UTC = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_builds_source_safe_gateway_workbench_discovery_contract_proof(tmp_path: Path) -> None:
    proof = _valid_gateway_workbench_discovery_contract_proof(tmp_path)

    assert proof["schemaVersion"] == GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_PROOF_SCHEMA_VERSION
    assert proof["repository"] == "lotus-idea"
    assert proof["proofType"] == "gateway_workbench_discovery_contract"
    assert proof["proofScope"] == "source_catalog_and_consumer_declaration"
    assert proof["evidenceClass"] == EvidenceClass.SOURCE_CONTRACT.value
    assert proof["gatewayWorkbenchDiscoveryContractProofValid"] is True
    assert tuple(proof["aggregateBlockersCleared"]) == (
        GATEWAY_WORKBENCH_DISCOVERY_CONTRACT_BLOCKERS_CLEARED
    )
    assert tuple(proof["localEvidenceRefs"]) == (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS
    )
    assert tuple(proof["platformEvidenceRefs"]) == (
        REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_PLATFORM_EVIDENCE_REFS
    )
    assert tuple(proof["remainingCertificationBlockers"]) == (
        REMAINING_GATEWAY_WORKBENCH_DISCOVERY_BLOCKERS
    )
    assert proof["declaredProductCount"] == len(REQUIRED_PRODUCER_PRODUCTS)
    assert proof["declaredConsumer"] == "lotus-gateway"
    assert proof["dataMeshCertified"] is False
    assert proof["producerProductsActive"] is False
    assert proof["fullWorkbenchProductCertified"] is False
    assert proof["gatewayWorkbenchDiscoveryCertified"] is False
    assert proof["canonicalDemoRuntimeCertified"] is False
    assert proof["runtimeExecutionObserved"] is False
    assert proof["supportedFeaturePromoted"] is False
    assert proof["proofClosed"] is False
    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is True
    serialized = json.dumps(proof)
    assert "PB_SG_GLOBAL_BAL_001" not in serialized
    assert "portfolio_id" not in serialized
    assert "client_id" not in serialized
    assert "requestBody" not in serialized


def test_rejects_gateway_workbench_discovery_contract_proof_when_catalog_routes_are_published(
    tmp_path: Path,
) -> None:
    platform_root = _write_platform_fixture(tmp_path, publish_routes=True)
    proof = _gateway_workbench_discovery_contract_proof(platform_root)

    assert proof["gatewayWorkbenchDiscoveryContractProofValid"] is False
    assert proof["proofChecks"]["catalogDeclaresGatewayConsumableIdeaProducts"] is False
    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("schemaVersion", "wrong"),
        ("repository", "lotus-core"),
        ("proofType", "mesh"),
        ("proofScope", "certified"),
        ("evidenceClass", EvidenceClass.RUNTIME_EXECUTION.value),
        ("gatewayWorkbenchDiscoveryContractProofValid", False),
        ("dataMeshCertified", True),
        ("producerProductsActive", True),
        ("fullWorkbenchProductCertified", True),
        ("gatewayWorkbenchDiscoveryCertified", True),
        ("canonicalDemoRuntimeCertified", True),
        ("runtimeExecutionObserved", True),
        ("supportedFeaturePromoted", True),
        ("proofClosed", True),
        ("generatedAtUtc", "not-a-datetime"),
    ],
)
def test_rejects_gateway_workbench_discovery_contract_proof_with_invalid_top_level_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_gateway_workbench_discovery_contract_proof(tmp_path)
    proof[field_name] = bad_value

    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "field_name",
    [
        "aggregateBlockersCleared",
        "localEvidenceRefs",
        "platformEvidenceRefs",
        "remainingCertificationBlockers",
        "proofChecks",
    ],
)
def test_rejects_gateway_workbench_discovery_contract_proof_with_invalid_contract_fields(
    field_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_gateway_workbench_discovery_contract_proof(tmp_path)
    proof[field_name] = (
        ["gateway_workbench_discovery_proof_missing"]
        if field_name == "aggregateBlockersCleared"
        else []
    )

    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is False


def test_rejects_gateway_workbench_discovery_contract_proof_without_explicit_clearance_list(
    tmp_path: Path,
) -> None:
    proof = _valid_gateway_workbench_discovery_contract_proof(tmp_path)
    del proof["aggregateBlockersCleared"]

    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("declaredProductCount", 0),
        ("declaredConsumer", "lotus-workbench"),
        ("platformCatalogSourceContractRef", None),
        ("workbenchReadPathSourceContractProofRef", None),
        ("gatewayWorkbenchContractProofRef", None),
    ],
)
def test_rejects_gateway_workbench_discovery_contract_proof_with_invalid_evidence_fields(
    field_name: str,
    bad_value: object,
    tmp_path: Path,
) -> None:
    proof = _valid_gateway_workbench_discovery_contract_proof(tmp_path)
    proof[field_name] = bad_value

    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "check_name",
    [
        "timezoneAwareGeneratedAtUtc",
        "fileEvidencePresent",
        "platformCatalogSourceContractValid",
        "workbenchReadPathSourceContractProofValid",
        "gatewayWorkbenchContractProofValid",
        "catalogDeclaresGatewayConsumableIdeaProducts",
        "productsRemainProposed",
        "routesRemainUnpublished",
    ],
)
def test_rejects_gateway_workbench_discovery_contract_proof_with_invalid_proof_checks(
    check_name: str,
    tmp_path: Path,
) -> None:
    proof = _valid_gateway_workbench_discovery_contract_proof(tmp_path)
    proof_checks = dict(cast(Mapping[str, object], proof["proofChecks"]))
    proof_checks[check_name] = False
    proof["proofChecks"] = proof_checks

    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is False


@pytest.mark.parametrize(
    "case_name",
    [
        "missing_payload",
        "products_not_list",
        "missing_products",
        "wrong_producer",
        "active_lifecycle",
        "missing_gateway_consumer",
    ],
)
def test_catalog_declaration_helper_rejects_non_contract_catalog_payloads(
    case_name: str,
) -> None:
    catalog_payload: dict[str, Any] | None
    match case_name:
        case "missing_payload":
            catalog_payload = None
        case "products_not_list":
            catalog_payload = {"products": "not-a-list"}
        case "missing_products":
            catalog_payload = {"products": []}
        case "wrong_producer":
            catalog_payload = {
                "products": [
                    {
                        **_catalog_product(product_id, publish_routes=False),
                        "producer_repository": "lotus-core",
                    }
                    for product_id in REQUIRED_PRODUCER_PRODUCTS
                ]
            }
        case "active_lifecycle":
            catalog_payload = {
                "products": [
                    {
                        **_catalog_product(product_id, publish_routes=False),
                        "lifecycle_status": "active",
                    }
                    for product_id in REQUIRED_PRODUCER_PRODUCTS
                ]
            }
        case "missing_gateway_consumer":
            catalog_payload = {
                "products": [
                    {
                        **_catalog_product(product_id, publish_routes=False),
                        "approved_consumers": ["lotus-report"],
                    }
                    for product_id in REQUIRED_PRODUCER_PRODUCTS
                ]
            }
        case _:
            raise AssertionError(f"Unhandled catalog case: {case_name}")

    assert _catalog_declares_gateway_consumable_idea_products(catalog_payload) is False


def test_required_file_evidence_rejects_missing_local_evidence(tmp_path: Path) -> None:
    assert (
        _required_file_evidence_present(
            repository_root=tmp_path / "lotus-idea",
            platform_root=tmp_path / "lotus-platform",
        )
        is False
    )


def test_required_file_evidence_rejects_missing_platform_evidence() -> None:
    assert (
        _required_file_evidence_present(
            repository_root=ROOT,
            platform_root=Path("missing-lotus-platform"),
        )
        is False
    )


def test_required_file_evidence_rejects_unreadable_makefile(tmp_path: Path) -> None:
    repository_root = tmp_path / "lotus-idea"
    platform_root = _write_platform_fixture(tmp_path)
    for ref in REQUIRED_GATEWAY_WORKBENCH_DISCOVERY_LOCAL_EVIDENCE_REFS:
        if ref.startswith(("GET ", "POST ", "make ")):
            continue
        (repository_root / ref).parent.mkdir(parents=True, exist_ok=True)
        (repository_root / ref).write_text("proof evidence\n", encoding="utf-8")
    (repository_root / "Makefile").mkdir()

    assert (
        _required_file_evidence_present(
            repository_root=repository_root,
            platform_root=platform_root,
        )
        is False
    )


def test_optional_json_and_datetime_helpers_reject_missing_or_invalid_values(
    tmp_path: Path,
) -> None:
    assert _optional_json(tmp_path / "missing.json") is None
    assert _is_timezone_aware_datetime_text(None) is False


def test_gateway_workbench_discovery_contract_proof_cli_writes_valid_artifact(
    tmp_path: Path,
) -> None:
    module = _load_generator_script()
    platform_root = _write_platform_fixture(tmp_path)
    dependency_proofs = _write_dependency_proofs(tmp_path, platform_root)
    output_path = tmp_path / "proof" / "gateway-workbench-discovery-contract-proof.json"

    result = module.main(
        [
            "--generated-at-utc",
            "2026-06-21T10:10:00Z",
            "--platform-root",
            str(platform_root),
            "--platform-catalog-source-contract-proof",
            str(dependency_proofs["platform_catalog_source_contract"]),
            "--workbench-read-path-source-contract-proof",
            str(dependency_proofs["workbench_read_path_source_contract"]),
            "--gateway-workbench-contract-proof",
            str(dependency_proofs["gateway_workbench_contract"]),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    proof = json.loads(output_path.read_text(encoding="utf-8"))
    assert gateway_workbench_discovery_contract_proof_is_valid(proof) is True


def test_gateway_workbench_discovery_contract_gate_scans_tuple_content() -> None:
    module = _load_contract_gate_script()
    errors: list[str] = []

    module._validate_forbidden_content(("PB_SG_GLOBAL_BAL_001",), errors)

    assert errors == ["$[0]: forbidden source-sensitive text `PB_SG_GLOBAL_BAL_001` is present"]


def test_gateway_workbench_discovery_contract_gate_accepts_missing_platform_checkout(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()

    errors = module.validate_gateway_workbench_discovery_contract_proof_contract(
        platform_root=tmp_path / "missing-lotus-platform",
    )

    assert errors == []


def test_gateway_workbench_discovery_contract_gate_rejects_invalid_present_platform_evidence(
    tmp_path: Path,
) -> None:
    module = _load_contract_gate_script()
    platform_root = _write_platform_fixture(tmp_path, publish_routes=True)

    errors = module.validate_gateway_workbench_discovery_contract_proof_contract(
        platform_root=platform_root,
    )

    assert errors == [
        "Gateway/Workbench discovery contract proof must validate against sibling platform truth when "
        "sibling evidence is present"
    ]


def _valid_gateway_workbench_discovery_contract_proof(tmp_path: Path) -> dict[str, Any]:
    return _gateway_workbench_discovery_contract_proof(_write_platform_fixture(tmp_path))


def _gateway_workbench_discovery_contract_proof(platform_root: Path) -> dict[str, Any]:
    dependency_proofs = _dependency_proofs(platform_root)
    return build_gateway_workbench_discovery_contract_proof_payload(
        generated_at_utc=GENERATED_AT_UTC,
        repository_root=ROOT,
        platform_root=platform_root,
        platform_catalog_source_contract=dependency_proofs["platform_catalog_source_contract"],
        workbench_read_path_source_contract_proof=(
            dependency_proofs["workbench_read_path_source_contract"]
        ),
        gateway_workbench_contract_proof=dependency_proofs["gateway_workbench_contract"],
        platform_catalog_source_contract_ref="output/data-mesh/platform-catalog-source-contract.json",
        workbench_read_path_source_contract_proof_ref=(
            "output/workbench/read-path-source-contract-proof.json"
        ),
        gateway_workbench_contract_proof_ref=(
            "output/workbench/gateway-workbench-contract-proof.json"
        ),
    )


def _dependency_proofs(platform_root: Path) -> dict[str, dict[str, Any]]:
    read_path_source_contract_proof = build_workbench_read_path_source_contract_proof_payload(
        generated_at_utc=GENERATED_AT_UTC,
        repository_root=ROOT,
    )
    return {
        "platform_catalog_source_contract": build_platform_catalog_source_contract_payload(
            generated_at_utc=GENERATED_AT_UTC,
            repository_root=ROOT,
            platform_root=platform_root,
        ),
        "workbench_read_path_source_contract": read_path_source_contract_proof,
        "gateway_workbench_contract": build_gateway_workbench_contract_proof_payload(
            generated_at_utc=GENERATED_AT_UTC,
            repository_root=ROOT,
            workbench_read_path_source_contract_proof=read_path_source_contract_proof,
            workbench_read_path_source_contract_proof_ref=(
                "output/workbench/read-path-source-contract-proof.json"
            ),
        ),
    }


def _write_dependency_proofs(tmp_path: Path, platform_root: Path) -> dict[str, Path]:
    proof_paths = {
        "platform_catalog_source_contract": tmp_path / "platform-catalog-source-contract.json",
        "workbench_read_path_source_contract": (tmp_path / "read-path-source-contract-proof.json"),
        "gateway_workbench_contract": tmp_path / "gateway-workbench-contract-proof.json",
    }
    for name, payload in _dependency_proofs(platform_root).items():
        proof_paths[name].write_text(json.dumps(payload), encoding="utf-8")
    return proof_paths


def _write_platform_fixture(tmp_path: Path, *, publish_routes: bool = False) -> Path:
    platform_root = tmp_path / "lotus-platform"
    (platform_root / "generated").mkdir(parents=True)
    (platform_root / "platform-contracts" / "domain-data-products").mkdir(parents=True)
    _write_json(
        platform_root
        / "platform-contracts"
        / "domain-data-products"
        / "domain-product-source-manifest.v1.json",
        {"repositories": [_source_manifest_repository()]},
    )
    _write_json(
        platform_root / "generated" / "domain-product-catalog.json",
        {
            "products": [
                _catalog_product(product_id, publish_routes=publish_routes)
                for product_id in REQUIRED_PRODUCER_PRODUCTS
            ],
            "consumers": [_catalog_consumer()],
        },
    )
    _write_json(platform_root / "generated" / "domain-product-dependency-graph.json", {})
    _write_json(
        platform_root / "generated" / "enterprise-mesh-maturity-matrix.json",
        {
            "repositories": [
                {
                    "repository": "lotus-idea",
                    "classification": "deferred",
                    "mesh_role": "producer",
                }
            ],
            "products": [
                _maturity_product(product_id) for product_id in REQUIRED_PRODUCER_PRODUCTS
            ],
        },
    )
    (platform_root / "docs" / "operations").mkdir(parents=True)
    (platform_root / "docs" / "operations" / "enterprise-mesh-completion-handoff.md").write_text(
        "# Enterprise Mesh Completion Handoff\n",
        encoding="utf-8",
    )
    return platform_root


def _source_manifest_repository() -> dict[str, Any]:
    return {
        "repository": "lotus-idea",
        "source_mode": "repo_native",
        "catalog_inclusion": "included",
        "repo_native_status": "implemented",
        "repo_native_declaration_path": "contracts/domain-data-products",
        "platform_declaration_paths": [],
    }


def _catalog_product(product_id: str, *, publish_routes: bool) -> dict[str, Any]:
    _, product_name, product_version = product_id.split(":")
    return {
        "product_id": product_id,
        "product_name": product_name,
        "product_version": product_version,
        "producer_repository": "lotus-idea",
        "lifecycle_status": "proposed",
        "approved_consumers": ["lotus-gateway"],
        "current_routes": ["/api/v1/ideas"] if publish_routes else [],
    }


def _catalog_consumer() -> dict[str, Any]:
    return {
        "consumer_repository": "lotus-idea",
        "dependencies": [
            {"dependency_id": dependency_id} for dependency_id in REQUIRED_CONSUMER_DEPENDENCIES
        ],
    }


def _maturity_product(product_id: str) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "classification": "deferred",
        "maturity_wave": "future_wave",
        "lifecycle_status": "proposed",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _load_generator_script() -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / "generate_discovery_contract_proof.py"
    spec = importlib.util.spec_from_file_location(
        "generate_gateway_workbench_discovery_contract_proof",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "workbench" / "discovery_contract_proof_gate.py"
    spec = importlib.util.spec_from_file_location(
        "gateway_workbench_discovery_contract_proof_contract_gate",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
