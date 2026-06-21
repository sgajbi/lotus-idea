from __future__ import annotations

from copy import deepcopy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _load_data_mesh_contract_gate() -> ModuleType:
    script_path = ROOT / "scripts" / "data_mesh_contract_gate.py"
    spec = importlib.util.spec_from_file_location("data_mesh_contract_gate", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_data_mesh_contract_gate_passes_current_repository_contract() -> None:
    module = _load_data_mesh_contract_gate()

    assert module.validate_data_mesh_contracts() == []


def test_data_mesh_contract_gate_can_run_without_platform_sibling_checkout(
    capsys: Any,
    monkeypatch: Any,
) -> None:
    module = _load_data_mesh_contract_gate()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "data_mesh_contract_gate.py",
            "--platform-catalog",
            str(ROOT / "missing-catalog.json"),
            "--platform-source-manifest",
            str(ROOT / "missing-source-manifest.json"),
        ],
    )

    assert module.main() == 0

    assert "Data-mesh contract gate passed" in capsys.readouterr().out


def test_consumer_gate_blocks_missing_required_source_authority() -> None:
    module = _load_data_mesh_contract_gate()
    consumer = module._read_json(module.CONSUMER_DECLARATION_PATH)
    consumer["dependencies"] = consumer["dependencies"][1:]

    errors = module.validate_consumer_contract(consumer)

    assert any(
        "consumer declaration missing dependencies: lotus-core:PortfolioStateSnapshot:v1" in error
        for error in errors
    )


def test_consumer_gate_blocks_invalid_dependency_posture() -> None:
    module = _load_data_mesh_contract_gate()
    consumer = module._read_json(module.CONSUMER_DECLARATION_PATH)
    dependency = consumer["dependencies"][0]
    dependency["producer_repository"] = "lotus-idea"
    dependency["migration_posture"]["status"] = "legacy"
    dependency["validation_lanes"] = ["feature"]
    dependency["failure_posture"] = "optimistic"
    dependency["required_trust_metadata"] = []
    dependency["business_purpose"] = " "

    errors = module.validate_consumer_contract(consumer)

    assert any("self-owned source dependency" in error for error in errors)
    assert any("migration status must be current" in error for error in errors)
    assert any("validation_lanes must include feature and pr-merge" in error for error in errors)
    assert any("invalid failure_posture" in error for error in errors)
    assert any("required_trust_metadata must include correlation_id" in error for error in errors)
    assert any("business_purpose is required" in error for error in errors)


def test_producer_gate_blocks_premature_product_promotion() -> None:
    module = _load_data_mesh_contract_gate()
    producer = module._read_json(module.PRODUCER_DECLARATION_PATH)
    product = producer["products"][0]
    product["lifecycle_status"] = "active"
    product["current_routes"] = ["/api/v1/ideas"]
    product["approved_consumers"] = []
    product["required_trust_metadata"] = []
    product["lineage_policy"]["lineage_required"] = False
    product["lineage_policy"]["evidence_bundle_required"] = False

    errors = module.validate_producer_contract(producer)

    assert any("lifecycle_status must remain proposed" in error for error in errors)
    assert any("current_routes must not exist" in error for error in errors)
    assert any("approved_consumers must include lotus-gateway" in error for error in errors)
    assert any("required_trust_metadata must include correlation_id" in error for error in errors)
    assert any("lineage_required must be true" in error for error in errors)
    assert any("evidence_bundle_required must be true" in error for error in errors)


def test_mesh_readiness_gate_blocks_unblocked_static_telemetry() -> None:
    module = _load_data_mesh_contract_gate()
    readiness = module._read_json(module.MESH_READINESS_PATH)
    telemetry = module._read_json(module.TRUST_TELEMETRY_PATH)
    slo = module._read_json(module.SLO_POLICY_PATH)
    access = module._read_json(module.ACCESS_POLICY_PATH)
    evidence = module._read_json(module.EVIDENCE_POLICY_PATH)

    readiness["certification_status"] = "certified"
    telemetry["freshness"]["freshness_state"] = "current"
    telemetry["lineage"]["lineage_materialized"] = True
    telemetry["blocking"]["blocked"] = False
    telemetry["observed_trust_metadata"] = {"correlation_id": "runtime-claim"}

    errors = module.validate_mesh_readiness(readiness, telemetry, slo, access, evidence)

    assert "mesh readiness certification_status must remain not_certified" in errors
    assert any("freshness_state must remain unknown" in error for error in errors)
    assert any("lineage must remain unmaterialized" in error for error in errors)
    assert any("trust telemetry must remain blocked" in error for error in errors)
    assert any("observed_trust_metadata must stay empty" in error for error in errors)


def test_mesh_readiness_gate_blocks_weak_policy_posture() -> None:
    module = _load_data_mesh_contract_gate()
    readiness = module._read_json(module.MESH_READINESS_PATH)
    telemetry = module._read_json(module.TRUST_TELEMETRY_PATH)
    slo = module._read_json(module.SLO_POLICY_PATH)
    access = module._read_json(module.ACCESS_POLICY_PATH)
    evidence = module._read_json(module.EVIDENCE_POLICY_PATH)

    slo["lineage"]["lineage_materialized_required"] = False
    access["default_posture"] = "public"
    access["allowed_consumers"] = []
    evidence["required_manifest_sections"] = ["product_identity"]
    evidence["field_access_classes"]["internal_debug"] = "public_customer"

    errors = module.validate_mesh_readiness(readiness, telemetry, slo, access, evidence)

    assert "mesh SLO policy must require materialized lineage" in errors
    assert "mesh access policy default_posture must be restricted" in errors
    assert any("must allow lotus-gateway" in error for error in errors)
    assert "mesh evidence policy must require runtime_telemetry" in errors
    assert "mesh evidence policy internal_debug must be internal_only" in errors


def test_platform_catalog_gate_blocks_unknown_source_product() -> None:
    module = _load_data_mesh_contract_gate()
    consumer = module._read_json(module.CONSUMER_DECLARATION_PATH)
    first_dependency = consumer["dependencies"][0]
    missing_product_id = (
        f"{first_dependency['producer_repository']}:"
        f"{first_dependency['product_name']}:"
        f"{first_dependency['required_product_version']}"
    )
    catalog = {"products": [{"product_id": "lotus-core:AnotherProduct:v1"}]}

    errors = module.validate_against_platform_catalog(consumer, catalog)

    assert missing_product_id in errors[0]
    assert "dependency is absent from platform catalog" in errors[0]


def test_platform_catalog_gate_accepts_current_source_products_when_catalog_exists() -> None:
    module = _load_data_mesh_contract_gate()
    consumer = module._read_json(module.CONSUMER_DECLARATION_PATH)
    catalog = {
        "products": [
            {
                "product_id": (
                    f"{dependency['producer_repository']}:"
                    f"{dependency['product_name']}:"
                    f"{dependency['required_product_version']}"
                )
            }
            for dependency in consumer["dependencies"]
        ]
    }

    assert module.validate_against_platform_catalog(consumer, catalog) == []


def test_platform_source_manifest_gate_blocks_premature_lotus_idea_inclusion() -> None:
    module = _load_data_mesh_contract_gate()
    readiness = module._read_json(module.MESH_READINESS_PATH)
    manifest = {"repositories": [{"repository": "lotus-idea", "catalog_inclusion": "included"}]}

    errors = module.validate_against_platform_source_manifest(readiness, manifest)

    assert errors == [
        "platform source manifest must not include lotus-idea before repo mesh readiness is certified"
    ]


def test_platform_source_manifest_gate_ignores_other_repositories() -> None:
    module = _load_data_mesh_contract_gate()
    readiness = module._read_json(module.MESH_READINESS_PATH)
    manifest = {"repositories": [{"repository": "lotus-core", "catalog_inclusion": "included"}]}

    assert module.validate_against_platform_source_manifest(readiness, manifest) == []


def test_data_mesh_contract_gate_reports_aggregate_errors(monkeypatch: Any, capsys: Any) -> None:
    module = _load_data_mesh_contract_gate()
    monkeypatch.setattr(module, "validate_data_mesh_contracts", lambda **_: ["first", "second"])
    monkeypatch.setattr(sys, "argv", ["data_mesh_contract_gate.py"])

    assert module.main() == 1

    assert capsys.readouterr().out == "first\nsecond\n"


def test_producer_gate_blocks_missing_required_products() -> None:
    module = _load_data_mesh_contract_gate()
    producer = deepcopy(module._read_json(module.PRODUCER_DECLARATION_PATH))
    producer["products"] = [
        product for product in producer["products"] if product["product_name"] != "IdeaCandidate"
    ]

    errors = module.validate_producer_contract(producer)

    assert any("producer declaration missing products: IdeaCandidate" in error for error in errors)
