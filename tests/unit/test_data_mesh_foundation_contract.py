from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PRODUCTS = {
    "OpportunitySignalCandidate",
    "IdeaCandidate",
    "IdeaEvidencePacket",
    "AdvisorOpportunityQueue",
    "IdeaReviewDecision",
    "IdeaFeedbackEvent",
    "IdeaConversionIntent",
    "IdeaConversionOutcome",
    "IdeaTrustTelemetry",
}

REQUIRED_DEPENDENCIES = {
    ("lotus-core", "PortfolioStateSnapshot"),
    ("lotus-core", "HoldingsAsOf"),
    ("lotus-core", "PortfolioCashMovementSummary"),
    ("lotus-core", "PortfolioCashflowProjection"),
    ("lotus-core", "BenchmarkAssignment"),
    ("lotus-performance", "ReturnsSeriesBundle"),
    ("lotus-performance", "BenchmarkExposureContext"),
    ("lotus-performance", "MandatePerformanceHealthContext"),
    ("lotus-risk", "RiskMetricsReport"),
    ("lotus-risk", "MandateRiskHealthContext"),
    ("lotus-risk", "RegimeScenarioPackEvaluation"),
    ("lotus-advise", "AdvisoryProposalLifecycleRecord"),
    ("lotus-advise", "AdvisoryPolicyEvaluationRecord"),
    ("lotus-manage", "PortfolioActionRegister"),
    ("lotus-report", "ClientReportEvidencePack"),
    ("lotus-advise", "AdvisoryCopilotInteractionRecord"),
}


def _read_json(path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((ROOT / path).read_text(encoding="utf-8")))


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_mesh_contract_placeholder_files_are_removed() -> None:
    governed_paths = [
        ROOT / "contracts",
        ROOT / "docs" / "operations",
    ]

    placeholder_paths = [
        path
        for base_path in governed_paths
        for path in base_path.rglob("*placeholder*")
        if path.is_file()
    ]

    assert placeholder_paths == []


def test_proposed_producer_products_are_repo_owned_and_not_active() -> None:
    payload = _read_json("contracts/domain-data-products/lotus-idea-products.v1.json")

    assert payload["contract_id"] == "domain-data-products"
    assert payload["producer_repository"] == "lotus-idea"
    assert payload["authoritative_domain"] == "opportunity_intelligence"

    products = {product["product_name"]: product for product in payload["products"]}
    assert REQUIRED_PRODUCTS <= products.keys()

    for product_name, product in products.items():
        assert product["owner_repository"] == "lotus-idea", product_name
        assert product["lifecycle_status"] == "proposed", product_name
        assert product["lineage_policy"]["lineage_required"] is True, product_name
        assert product["lineage_policy"]["evidence_bundle_required"] is True, product_name
        assert "correlation_id" in product["required_trust_metadata"], product_name
        assert "lotus-gateway" in product["approved_consumers"], product_name


def test_consumer_dependencies_name_current_source_authorities() -> None:
    payload = _read_json("contracts/domain-data-products/lotus-idea-consumers.v1.json")

    assert payload["contract_id"] == "domain-data-product-consumers"
    assert payload["consumer_repository"] == "lotus-idea"

    dependencies = {
        (dependency["producer_repository"], dependency["product_name"])
        for dependency in payload["dependencies"]
    }
    assert REQUIRED_DEPENDENCIES <= dependencies

    for dependency in payload["dependencies"]:
        assert dependency["migration_posture"]["status"] == "current"
        assert dependency["validation_lanes"]
        assert dependency["failure_posture"] in {
            "fail_closed",
            "degrade_to_partial",
            "support_only",
        }


def test_mesh_readiness_is_not_certified_until_runtime_evidence_exists() -> None:
    readiness = _read_json("contracts/domain-data-products/mesh-readiness.v1.json")
    telemetry = _read_json("contracts/trust-telemetry/idea-candidate.telemetry.v1.json")

    assert readiness["repository"] == "lotus-idea"
    assert readiness["lifecycle_status"] == "planned"
    assert readiness["certification_status"] == "not_certified"
    assert readiness["source_of_truth"]["producer_declaration"].endswith(
        "lotus-idea-products.v1.json"
    )

    assert telemetry["product_id"] == "lotus-idea:IdeaCandidate:v1"
    assert telemetry["producer_repository"] == "lotus-idea"
    assert telemetry["freshness"]["freshness_state"] == "unknown"
    assert telemetry["lineage"]["lineage_materialized"] is False
    assert telemetry["blocking"]["blocked"] is True
    assert "implementation" in telemetry["blocking"]["blocked_reason"]


def test_mesh_slo_access_evidence_policies_exist_for_first_product() -> None:
    slo = _read_json("contracts/mesh-slo/lotus-idea-idea-candidate.slo.v1.json")
    access = _read_json("contracts/mesh-access/lotus-idea-idea-candidate.access.v1.json")
    evidence = _read_json(
        "contracts/mesh-evidence/lotus-idea-idea-candidate.evidence-pack-policy.v1.json"
    )

    assert slo["contract_id"] == "lotus-mesh-slo-policy"
    assert slo["product_id"] == "lotus-idea:IdeaCandidate:v1"
    assert slo["lineage"]["lineage_materialized_required"] is True

    assert access["contract_id"] == "lotus-mesh-access-policy"
    assert access["default_posture"] == "restricted"
    assert access["allowed_consumers"][0]["consumer_repository"] == "lotus-gateway"

    assert evidence["contract_id"] == "lotus-mesh-evidence-pack-policy"
    assert "source_declaration" in evidence["required_manifest_sections"]
    assert evidence["field_access_classes"]["internal_debug"] == "internal_only"


def test_docs_and_wiki_route_agents_to_mesh_readiness_truth() -> None:
    for path in (
        "README.md",
        "REPOSITORY-ENGINEERING-CONTEXT.md",
        "docs/operations/mesh-readiness.md",
        "wiki/Architecture.md",
        "wiki/Integrations.md",
        "wiki/Security-and-Governance.md",
        "wiki/Validation-and-CI.md",
    ):
        content = _read(path)
        assert "lotus-idea-products.v1.json" in content or "mesh" in content.lower()

    assert "not certified" in _read("docs/operations/mesh-readiness.md")
    assert "blocked" in _read("wiki/Security-and-Governance.md")


def test_rfc_index_and_main_rfc_match_data_mesh_foundation_truth() -> None:
    rfc_index = _read("docs/rfcs/README.md")
    main_rfc = _read(
        "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/"
        "RFC-0002-enterprise-opportunity-intelligence-operating-layer.md"
    )

    assert (
        "source-authority-signal-contracts-and-data-mesh-baseline.md) | "
        "Partially implemented - repo-native mesh contract gate enforced, including bounded "
        "Lotus Risk concentration consumer declaration |"
    ) in rfc_index
    assert "OpportunitySignalCandidate:v1" in main_rfc
    assert "IdeaCandidate:v1" in main_rfc
    assert "IdeaReviewDecision:v1" in main_rfc
    assert "WealthOpportunityCandidate" not in main_rfc
    assert "IdeaSuppressionEvent" not in main_rfc
