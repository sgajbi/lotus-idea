from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.application.opportunity_archetype_contracts import (
    load_opportunity_archetype_contract,
    opportunity_archetype_contract_from_payload,
)


ROOT = Path(__file__).resolve().parents[2]


def test_opportunity_archetype_contract_gate_passes_current_contract() -> None:
    module = _load_contract_gate_script()

    assert module.validate_opportunity_archetype_contract() == []


def test_opportunity_archetype_contract_identifies_only_high_cash_as_first_journey() -> None:
    contract = load_opportunity_archetype_contract()

    first_journeys = [
        archetype.archetype_id
        for archetype in contract.archetypes
        if archetype.first_supported_journey
    ]

    assert first_journeys == ["high-cash-idle-liquidity"]


def test_opportunity_archetype_contract_preserves_not_certified_boundaries() -> None:
    contract = load_opportunity_archetype_contract()

    assert contract.lifecycle_status == "foundation"
    assert contract.supportability_status == "not_certified"
    assert contract.demo_ready is False
    assert contract.client_publication_ready is False
    assert contract.supported_feature_promoted is False
    assert contract.data_mesh_certified is False
    assert all(archetype.blockers for archetype in contract.archetypes)
    assert all(
        scenario.supported_feature_promoted is False
        for archetype in contract.archetypes
        for scenario in archetype.canonical_scenarios
    )


def test_opportunity_archetype_contract_records_concentration_foundation_without_promotion() -> (
    None
):
    contract = load_opportunity_archetype_contract()

    concentration = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "concentration-risk-review"
    )

    assert concentration.implementation_status == "partially_implemented"
    assert concentration.first_supported_journey is False
    assert "lotus-risk:ConcentrationRiskReport:v1" in concentration.source_products
    assert "src/app/application/risk_concentration_live_proof.py" in concentration.evidence_refs
    assert "make risk-concentration-live-proof-contract-gate" in concentration.evidence_refs
    assert "live_risk_source_proof_missing" in concentration.blockers
    assert "risk_source_consumer_approval_missing" not in concentration.blockers
    assert "data_mesh_not_certified" in concentration.blockers
    assert "supported_feature_promotion_missing" in concentration.blockers
    assert concentration.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert concentration.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_records_underperformance_foundation_without_promotion() -> (
    None
):
    contract = load_opportunity_archetype_contract()

    underperformance = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "underperformance-review"
    )

    assert underperformance.implementation_status == "partially_implemented"
    assert underperformance.first_supported_journey is False
    assert "lotus-performance:ReturnsSeriesBundle:v1" in underperformance.source_products
    assert "src/app/application/underperformance_signal.py" in underperformance.evidence_refs
    assert (
        "src/app/application/performance_underperformance_live_proof.py"
        in underperformance.evidence_refs
    )
    assert "make performance-underperformance-live-proof-contract-gate" in (
        underperformance.evidence_refs
    )
    assert "src/app/infrastructure/lotus_performance_sources.py" in underperformance.evidence_refs
    assert "live_performance_source_proof_missing" in underperformance.blockers
    assert "benchmark_assignment_source_ref_missing" in underperformance.blockers
    assert "supported_feature_promotion_missing" in underperformance.blockers
    assert underperformance.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert underperformance.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_records_manage_foundation_without_promotion() -> None:
    contract = load_opportunity_archetype_contract()

    allocation_drift = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "allocation-drift-mandate-review"
    )

    assert allocation_drift.implementation_status == "partially_implemented"
    assert allocation_drift.first_supported_journey is False
    assert "lotus-manage:PortfolioActionRegister:v1" in allocation_drift.source_products
    assert "src/app/application/mandate_health_signal.py" in allocation_drift.evidence_refs
    assert "src/app/application/manage_mandate_live_proof.py" in allocation_drift.evidence_refs
    assert "src/app/infrastructure/lotus_manage_sources.py" in allocation_drift.evidence_refs
    assert "scripts/generate_manage_mandate_live_proof.py" in allocation_drift.evidence_refs
    assert "make manage-mandate-live-proof-contract-gate" in allocation_drift.evidence_refs
    assert "tests/unit/test_manage_mandate_live_proof.py" in allocation_drift.evidence_refs
    assert "portfolio_scoped_manage_source_proof_missing" in allocation_drift.blockers
    assert "manage_source_adapter_missing" not in allocation_drift.blockers
    assert "mandate_health_signal_policy_missing" not in allocation_drift.blockers
    assert "data_mesh_not_certified" in allocation_drift.blockers
    assert "supported_feature_promotion_missing" in allocation_drift.blockers
    assert allocation_drift.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert allocation_drift.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_records_missing_suitability_foundation_without_promotion() -> (
    None
):
    contract = load_opportunity_archetype_contract()

    missing_suitability = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "missing-suitability-context"
    )

    assert missing_suitability.implementation_status == "partially_implemented"
    assert missing_suitability.first_supported_journey is False
    assert "lotus-advise:AdvisoryPolicyEvaluationRecord:v1" in missing_suitability.source_products
    assert "src/app/domain/missing_suitability_signal.py" in missing_suitability.evidence_refs
    assert "src/app/application/missing_suitability_signal.py" in missing_suitability.evidence_refs
    assert "src/app/infrastructure/lotus_advise_sources.py" in (missing_suitability.evidence_refs)
    assert "tests/unit/test_missing_suitability_signal_evaluation.py" in (
        missing_suitability.evidence_refs
    )
    assert "advise_policy_live_source_proof_missing" in missing_suitability.blockers
    assert "advise_policy_source_adapter_missing" not in missing_suitability.blockers
    assert "suitability_authority_boundary_proof_missing" not in (missing_suitability.blockers)
    assert "data_mesh_not_certified" in missing_suitability.blockers
    assert "client_publication_not_ready" in missing_suitability.blockers
    assert "supported_feature_promotion_missing" in missing_suitability.blockers
    assert missing_suitability.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert missing_suitability.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_records_low_income_foundation_without_promotion() -> None:
    contract = load_opportunity_archetype_contract()

    low_income = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "low-income-liquidity-shortfall"
    )

    assert low_income.implementation_status == "partially_implemented"
    assert low_income.first_supported_journey is False
    assert "lotus-core:PortfolioCashflowProjection:v1" in low_income.source_products
    assert "lotus-core:PortfolioCashMovementSummary:v1" in low_income.source_products
    assert "src/app/application/low_income_signal.py" in low_income.evidence_refs
    assert "src/app/application/low_income_core_cashflow_live_proof.py" in low_income.evidence_refs
    assert "src/app/infrastructure/lotus_core_sources.py" in low_income.evidence_refs
    assert "scripts/generate_low_income_core_cashflow_live_proof.py" in low_income.evidence_refs
    assert "make low-income-core-cashflow-live-proof-contract-gate" in low_income.evidence_refs
    assert "tests/unit/test_low_income_signal_evaluation.py" in low_income.evidence_refs
    assert "tests/unit/test_low_income_core_cashflow_live_proof.py" in low_income.evidence_refs
    assert "live_core_cashflow_source_proof_missing" in low_income.blockers
    assert "data_mesh_not_certified" in low_income.blockers
    assert "client_publication_not_ready" in low_income.blockers
    assert "supported_feature_promotion_missing" in low_income.blockers
    assert low_income.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert low_income.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_records_bond_maturity_foundation_without_promotion() -> (
    None
):
    contract = load_opportunity_archetype_contract()

    bond_maturity = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "bond-maturity-reinvestment"
    )

    assert bond_maturity.implementation_status == "partially_implemented"
    assert bond_maturity.first_supported_journey is False
    assert "lotus-core:HoldingsAsOf:v1" in bond_maturity.source_products
    assert "src/app/domain/bond_maturity_signal.py" in bond_maturity.evidence_refs
    assert "src/app/application/bond_maturity_signal.py" in bond_maturity.evidence_refs
    assert "src/app/ports/core_sources.py" in bond_maturity.evidence_refs
    assert "tests/unit/test_bond_maturity_signal_evaluation.py" in (bond_maturity.evidence_refs)
    assert "tests/unit/test_bond_maturity_application.py" in bond_maturity.evidence_refs
    assert "maturity_source_contract_missing" in bond_maturity.blockers
    assert "maturity_signal_policy_missing" not in bond_maturity.blockers
    assert "data_mesh_not_certified" in bond_maturity.blockers
    assert "client_publication_not_ready" in bond_maturity.blockers
    assert "supported_feature_promotion_missing" in bond_maturity.blockers
    assert bond_maturity.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert bond_maturity.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_records_missing_benchmark_foundation_without_promotion() -> (
    None
):
    contract = load_opportunity_archetype_contract()

    missing_benchmark = next(
        archetype
        for archetype in contract.archetypes
        if archetype.archetype_id == "missing-benchmark-review"
    )

    assert missing_benchmark.implementation_status == "partially_implemented"
    assert missing_benchmark.first_supported_journey is False
    assert "lotus-core:BenchmarkAssignment:v1" in missing_benchmark.source_products
    assert "lotus-performance:ReturnsSeriesBundle:v1" in missing_benchmark.source_products
    assert "src/app/domain/missing_benchmark_signal.py" in missing_benchmark.evidence_refs
    assert "src/app/application/missing_benchmark_signal.py" in missing_benchmark.evidence_refs
    assert "src/app/ports/core_sources.py" in missing_benchmark.evidence_refs
    assert "src/app/infrastructure/lotus_core_sources.py" in missing_benchmark.evidence_refs
    assert "tests/unit/test_missing_benchmark_signal_evaluation.py" in (
        missing_benchmark.evidence_refs
    )
    assert "tests/unit/test_missing_benchmark_application.py" in missing_benchmark.evidence_refs
    assert "tests/unit/test_lotus_core_sources.py" in missing_benchmark.evidence_refs
    assert "missing_benchmark_live_core_source_proof_missing" in missing_benchmark.blockers
    assert "performance_benchmark_readiness_source_ref_missing" in (missing_benchmark.blockers)
    assert "data_mesh_not_certified" in missing_benchmark.blockers
    assert "client_publication_not_ready" in missing_benchmark.blockers
    assert "supported_feature_promotion_missing" in missing_benchmark.blockers
    assert missing_benchmark.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert missing_benchmark.canonical_scenarios[0].proof_status == "not_client_demo_ready"


def test_opportunity_archetype_contract_gate_rejects_demo_ready_claim() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["demo_ready"] = True

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert "opportunity archetype contract must not claim demo readiness" in errors


def test_opportunity_archetype_contract_gate_rejects_extra_first_journey() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][1]["first_supported_journey"] = True

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert "high-cash-idle-liquidity must be the only first supported journey" in errors


def test_opportunity_archetype_contract_gate_rejects_missing_high_cash_evidence() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][0]["evidence_refs"].remove(
        "src/app/application/source_ingestion_live_proof.py"
    )

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert (
        "high-cash-idle-liquidity evidence_refs missing: "
        "src/app/application/source_ingestion_live_proof.py"
    ) in errors


def test_opportunity_archetype_contract_gate_rejects_missing_underperformance_evidence() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][2]["evidence_refs"].remove(
        "src/app/application/underperformance_signal.py"
    )

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert (
        "underperformance-review evidence_refs missing: "
        "src/app/application/underperformance_signal.py"
    ) in errors


def test_opportunity_archetype_contract_gate_rejects_missing_manage_evidence() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][3]["evidence_refs"].remove("src/app/application/mandate_health_signal.py")

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert (
        "allocation-drift-mandate-review evidence_refs missing: "
        "src/app/application/mandate_health_signal.py"
    ) in errors


def test_opportunity_archetype_contract_gate_rejects_missing_suitability_evidence() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][6]["evidence_refs"].remove(
        "src/app/application/missing_suitability_signal.py"
    )

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert (
        "missing-suitability-context evidence_refs missing: "
        "src/app/application/missing_suitability_signal.py"
    ) in errors


def test_opportunity_archetype_contract_gate_rejects_missing_benchmark_evidence() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    missing_benchmark = next(
        archetype
        for archetype in payload["archetypes"]
        if archetype["archetype_id"] == "missing-benchmark-review"
    )
    missing_benchmark["evidence_refs"].remove("src/app/application/missing_benchmark_signal.py")

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert (
        "missing-benchmark-review evidence_refs missing: "
        "src/app/application/missing_benchmark_signal.py"
    ) in errors


def test_opportunity_archetype_contract_gate_rejects_promoted_scenario() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][0]["canonical_scenarios"][0]["supported_feature_promoted"] = True

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert "high-cash-idle-liquidity: scenario must not promote supported features" in errors


def test_opportunity_archetype_contract_loader_rejects_non_object_json(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="opportunity archetype contract must be a JSON object"):
        load_opportunity_archetype_contract(
            repository_root=tmp_path,
            contract_path=Path("contract.json"),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload.__setitem__("source_of_truth", []),
            "opportunity archetype source_of_truth must be an object",
        ),
        (
            lambda payload: payload.__setitem__("archetypes", {}),
            "opportunity archetypes must be a list",
        ),
        (
            lambda payload: payload.__setitem__("archetypes", ["not-object"]),
            "opportunity archetype entries must be objects",
        ),
    ],
)
def test_opportunity_archetype_contract_parser_rejects_invalid_collection_shapes(
    mutation: Any,
    message: str,
) -> None:
    payload = _contract_payload()
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        opportunity_archetype_contract_from_payload(payload)


def test_opportunity_archetype_contract_parser_ignores_non_list_string_fields() -> None:
    payload = _contract_payload()
    payload["archetypes"][0]["source_products"] = "not-list"
    payload["archetypes"][0]["evidence_refs"] = "not-list"
    payload["archetypes"][0]["blockers"] = "not-list"
    payload["archetypes"][0]["canonical_scenarios"][0]["required_evidence"] = "not-list"
    payload["archetypes"][0]["canonical_scenarios"][0]["remaining_blockers"] = "not-list"

    contract = opportunity_archetype_contract_from_payload(payload)

    archetype = contract.archetypes[0]
    assert archetype.source_products == ()
    assert archetype.evidence_refs == ()
    assert archetype.blockers == ()
    assert archetype.canonical_scenarios[0].required_evidence == ()
    assert archetype.canonical_scenarios[0].remaining_blockers == ()


def _contract_payload() -> dict[str, Any]:
    import json

    return copy.deepcopy(
        json.loads(
            (
                ROOT
                / "contracts"
                / "opportunity-archetypes"
                / "lotus-idea-opportunity-archetypes.v1.json"
            ).read_text(encoding="utf-8")
        )
    )


def _load_contract_gate_script() -> ModuleType:
    script_path = ROOT / "scripts" / "opportunity_archetype_contract_gate.py"
    spec = importlib.util.spec_from_file_location(
        "opportunity_archetype_contract_gate", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
