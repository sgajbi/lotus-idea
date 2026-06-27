from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from app.application.opportunity_archetype_contracts import load_opportunity_archetype_contract


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
    assert "src/app/infrastructure/lotus_performance_sources.py" in underperformance.evidence_refs
    assert "live_performance_source_proof_missing" in underperformance.blockers
    assert "benchmark_assignment_source_ref_missing" in underperformance.blockers
    assert "supported_feature_promotion_missing" in underperformance.blockers
    assert underperformance.canonical_scenarios[0].scenario_status == "bounded_foundation"
    assert underperformance.canonical_scenarios[0].proof_status == "not_client_demo_ready"


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


def test_opportunity_archetype_contract_gate_rejects_promoted_scenario() -> None:
    module = _load_contract_gate_script()
    payload = _contract_payload()
    payload["archetypes"][0]["canonical_scenarios"][0]["supported_feature_promoted"] = True

    errors = module.validate_opportunity_archetype_contract_payload(module._parse_payload(payload))

    assert "high-cash-idle-liquidity: scenario must not promote supported features" in errors


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
