from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.application.opportunity_archetype_contracts import (  # noqa: E402
    OPPORTUNITY_ARCHETYPE_CONTRACT_PATH,
    OpportunityArchetypeContract,
    load_opportunity_archetype_contract,
    opportunity_archetype_contract_from_payload,
)
from opportunity_archetype_contracts.bond_maturity import (  # noqa: E402
    BOND_MATURITY_EVIDENCE as REQUIRED_BOND_MATURITY_EVIDENCE,
)

_parse_payload = opportunity_archetype_contract_from_payload

REQUIRED_ARCHETYPES = {
    "high-cash-idle-liquidity",
    "concentration-risk-review",
    "underperformance-review",
    "allocation-drift-mandate-review",
    "high-volatility-drawdown-review",
    "bond-maturity-reinvestment",
    "low-income-liquidity-shortfall",
    "missing-benchmark-review",
    "mandate-restriction-review",
    "missing-risk-profile-review",
    "missing-suitability-context",
}
REQUIRED_SOURCE_OF_TRUTH = {
    "rfc_main",
    "rfc_slice_00",
    "rfc_slice_05",
    "rfc_slice_16",
    "contract_loader",
    "contract_gate",
    "demo_claims",
    "wiki_demo_readiness",
}
REQUIRED_HIGH_CASH_PRODUCTS = {
    "lotus-core:PortfolioStateSnapshot:v1",
    "lotus-core:HoldingsAsOf:v1",
    "lotus-core:PortfolioCashMovementSummary:v1",
    "lotus-core:PortfolioCashflowProjection:v1",
}
REQUIRED_HIGH_CASH_EVIDENCE = {
    "src/app/domain/signal_evaluation.py",
    "src/app/application/source_ingestion.py",
    "src/app/application/source_ingestion_runtime_evidence/runtime_execution.py",
    "docs/examples/source-ingestion/high-cash-worker-manifest.example.json",
    "make source-ingestion-worker-check",
    "make source-ingestion-runtime-execution-contract-gate",
    "GET /api/v1/source-ingestion/readiness",
    "POST /api/v1/source-ingestion/run-once",
    "tests/unit/source_ingestion_runtime_evidence/test_runtime_execution.py",
}
REQUIRED_CONCENTRATION_EVIDENCE = {
    "src/app/application/concentration_risk_signal.py",
    "src/app/api/concentration_risk_signals.py",
    "src/app/application/risk_concentration_runtime_evidence/runtime_execution.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "POST /api/v1/idea-signals/concentration-risk/evaluate",
    "scripts/risk_concentration_runtime_evidence/generate_runtime_execution.py",
    "make risk-concentration-live-proof-contract-gate",
    "tests/integration/test_concentration_risk_signal_api.py",
    "tests/unit/risk_concentration_runtime_evidence/test_runtime_execution.py",
}
REQUIRED_UNDERPERFORMANCE_EVIDENCE = {
    "src/app/application/underperformance_signal.py",
    "src/app/api/underperformance_signals.py",
    "src/app/application/performance_underperformance_runtime_evidence/runtime_execution.py",
    "src/app/application/performance_underperformance_runtime_evidence/contract.py",
    "src/app/application/core_benchmark_assignment_runtime_evidence/runtime_execution.py",
    "src/app/application/core_benchmark_assignment_runtime_evidence/contract.py",
    "src/app/infrastructure/lotus_performance_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "src/app/ports/performance_sources.py",
    "src/app/ports/core_sources.py",
    "scripts/performance_underperformance_runtime_evidence/generate_runtime_execution.py",
    "scripts/core_benchmark_assignment_runtime_evidence/generate_runtime_execution.py",
    "POST /api/v1/idea-signals/underperformance/evaluate",
    "make performance-underperformance-live-proof-contract-gate",
    "make core-benchmark-assignment-live-proof-contract-gate",
    "tests/integration/test_underperformance_signal_api.py",
    "tests/unit/test_underperformance_signal_evaluation.py",
    "tests/unit/test_underperformance_application.py",
    "tests/unit/test_lotus_performance_sources.py",
    "tests/unit/test_lotus_core_sources.py",
    "tests/unit/performance_underperformance_runtime_evidence/test_runtime_execution.py",
    "tests/unit/core_benchmark_assignment_runtime_evidence/test_runtime_execution.py",
}
REQUIRED_MANAGE_EVIDENCE = {
    "src/app/domain/signal_evaluation.py",
    "src/app/application/mandate_health_signal.py",
    "src/app/api/allocation_drift_signals.py",
    "src/app/application/manage_mandate_runtime_evidence/runtime_execution.py",
    "src/app/application/manage_mandate_runtime_evidence/contract.py",
    "src/app/application/core_portfolio_state_runtime_evidence/runtime_execution.py",
    "src/app/application/core_portfolio_state_runtime_evidence/contract.py",
    "src/app/ports/manage_sources.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_manage_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "scripts/manage_mandate_runtime_evidence/generate_runtime_execution.py",
    "scripts/core_portfolio_state_runtime_evidence/generate_runtime_execution.py",
    "make manage-mandate-live-proof-contract-gate",
    "make core-portfolio-state-live-proof-contract-gate",
    "tests/unit/test_mandate_health_signal_evaluation.py",
    "tests/unit/test_mandate_health_application.py",
    "tests/unit/test_lotus_manage_sources.py",
    "tests/unit/test_lotus_core_sources.py",
    "tests/unit/manage_mandate_runtime_evidence/test_runtime_execution.py",
    "tests/unit/manage_mandate_runtime_evidence/test_generator.py",
    "tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py",
    "tests/unit/core_portfolio_state_runtime_evidence/test_generator.py",
    "tests/unit/test_implementation_proof_readiness_core_portfolio_state.py",
    "tests/integration/test_allocation_drift_signal_api.py",
    "POST /api/v1/idea-signals/allocation-drift/evaluate",
}
REQUIRED_HIGH_VOLATILITY_EVIDENCE = {
    "src/app/domain/signal_evaluation.py",
    "src/app/application/high_volatility_signal.py",
    "src/app/api/high_volatility_signals.py",
    "src/app/application/high_volatility_runtime_evidence/runtime_execution.py",
    "src/app/application/high_volatility_runtime_evidence/contract.py",
    "src/app/application/source_runtime_evidence/receipts.py",
    "src/app/application/drawdown_review_signal.py",
    "src/app/application/risk_drawdown_runtime_evidence/runtime_execution.py",
    "src/app/application/risk_drawdown_runtime_evidence/contract.py",
    "src/app/api/drawdown_review_signals.py",
    "src/app/ports/risk_sources.py",
    "src/app/infrastructure/lotus_risk_sources.py",
    "POST /api/v1/idea-signals/high-volatility/evaluate",
    "POST /api/v1/idea-signals/drawdown-review/evaluate",
    "scripts/high_volatility_runtime_evidence/generate_runtime_execution.py",
    "scripts/risk_drawdown_runtime_evidence/generate_runtime_execution.py",
    "make high-volatility-live-proof-contract-gate",
    "make risk-drawdown-live-proof-contract-gate",
    "tests/unit/test_high_volatility_signal_evaluation.py",
    "tests/unit/test_high_volatility_application.py",
    "tests/unit/test_lotus_risk_volatility_sources.py",
    "tests/unit/high_volatility_runtime_evidence/test_runtime_execution.py",
    "tests/unit/test_drawdown_review_signal_evaluation.py",
    "tests/unit/test_drawdown_review_application.py",
    "tests/integration/test_high_volatility_signal_api.py",
    "tests/integration/test_drawdown_review_signal_api.py",
    "tests/unit/test_lotus_risk_drawdown_sources.py",
    "tests/unit/risk_drawdown_runtime_evidence/test_runtime_execution.py",
}
REQUIRED_MISSING_SUITABILITY_EVIDENCE = {
    "src/app/domain/missing_suitability_signal.py",
    "src/app/application/missing_suitability_signal.py",
    "src/app/api/missing_suitability_signals.py",
    "src/app/application/advise_missing_suitability_runtime_evidence/runtime_execution.py",
    "src/app/application/advise_missing_suitability_runtime_evidence/contract.py",
    "src/app/ports/advise_sources.py",
    "src/app/infrastructure/lotus_advise_sources.py",
    "POST /api/v1/idea-signals/missing-suitability/evaluate",
    "scripts/advise_missing_suitability_runtime_evidence/generate_runtime_execution.py",
    "make missing-suitability-live-proof-contract-gate",
    "tests/integration/test_missing_suitability_signal_api.py",
    "tests/unit/test_missing_suitability_signal_evaluation.py",
    "tests/unit/test_missing_suitability_application.py",
    "tests/unit/test_lotus_advise_sources.py",
    "tests/unit/advise_missing_suitability_runtime_evidence/test_runtime_execution.py",
    "tests/unit/advise_missing_suitability_runtime_evidence/test_generator.py",
}
REQUIRED_LOW_INCOME_EVIDENCE = {
    "src/app/domain/low_income_signal.py",
    "src/app/application/low_income_signal.py",
    "src/app/api/low_income_signals.py",
    "src/app/ports/core_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "POST /api/v1/idea-signals/low-income/evaluate",
    "tests/integration/test_low_income_signal_api.py",
    "tests/unit/test_low_income_signal_evaluation.py",
    "tests/unit/test_low_income_application.py",
    "tests/unit/test_lotus_core_sources.py",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md",
}
REQUIRED_MISSING_BENCHMARK_EVIDENCE = {
    "src/app/domain/missing_benchmark_signal.py",
    "src/app/application/missing_benchmark_signal.py",
    "src/app/api/missing_benchmark_signals.py",
    "src/app/application/core_missing_benchmark_runtime_evidence/runtime_execution.py",
    "src/app/application/core_missing_benchmark_runtime_evidence/contract.py",
    "src/app/application/performance_benchmark_readiness.py",
    "src/app/application/performance_benchmark_readiness_runtime_evidence/runtime_execution.py",
    "src/app/application/performance_benchmark_readiness_runtime_evidence/contract.py",
    "src/app/domain/performance_benchmark_readiness.py",
    "src/app/ports/core_sources.py",
    "src/app/ports/performance_sources.py",
    "src/app/infrastructure/lotus_core_sources.py",
    "src/app/infrastructure/lotus_performance_sources.py",
    "scripts/core_missing_benchmark_runtime_evidence/generate_runtime_execution.py",
    "scripts/performance_benchmark_readiness_runtime_evidence/generate_runtime_execution.py",
    "make missing-benchmark-live-proof-contract-gate",
    "make missing-benchmark-performance-readiness-proof-contract-gate",
    "POST /api/v1/idea-signals/missing-benchmark/evaluate",
    "tests/integration/test_missing_benchmark_signal_api.py",
    "tests/unit/test_missing_benchmark_signal_evaluation.py",
    "tests/unit/test_missing_benchmark_application.py",
    "tests/unit/core_missing_benchmark_runtime_evidence/test_runtime_execution.py",
    "tests/unit/core_missing_benchmark_runtime_evidence/test_generator.py",
    "tests/unit/performance_benchmark_readiness_runtime_evidence/test_runtime_execution.py",
    "tests/unit/performance_benchmark_readiness_runtime_evidence/test_generator.py",
    "tests/unit/test_implementation_proof_readiness_missing_benchmark.py",
    "tests/unit/test_lotus_core_sources.py",
    "tests/unit/test_lotus_performance_sources.py",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md",
}
REQUIRED_MISSING_RISK_PROFILE_EVIDENCE = {
    "src/app/domain/missing_risk_profile_signal.py",
    "src/app/application/missing_risk_profile_signal.py",
    "src/app/api/missing_risk_profile_signals.py",
    "src/app/application/advise_missing_risk_profile_runtime_evidence/runtime_execution.py",
    "src/app/application/advise_missing_risk_profile_runtime_evidence/contract.py",
    "src/app/ports/advise_sources.py",
    "POST /api/v1/idea-signals/missing-risk-profile/evaluate",
    "scripts/advise_missing_risk_profile_runtime_evidence/generate_runtime_execution.py",
    "make missing-risk-profile-live-proof-contract-gate",
    "tests/integration/test_missing_risk_profile_signal_api.py",
    "tests/unit/test_missing_risk_profile_signal_evaluation.py",
    "tests/unit/test_missing_risk_profile_application.py",
    "tests/unit/advise_missing_risk_profile_runtime_evidence/test_runtime_execution.py",
    "tests/unit/advise_missing_risk_profile_runtime_evidence/test_generator.py",
    "tests/unit/test_implementation_proof_readiness_missing_risk_profile.py",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md",
}
REQUIRED_MANDATE_RESTRICTION_EVIDENCE = {
    "src/app/domain/mandate_restriction_signal.py",
    "src/app/application/mandate_restriction_signal.py",
    "src/app/application/advise_mandate_restriction_runtime_evidence/runtime_execution.py",
    "src/app/application/advise_mandate_restriction_runtime_evidence/contract.py",
    "src/app/application/mandate_restriction_source_product_proof.py",
    "src/app/api/idea_signals.py",
    "scripts/advise_mandate_restriction_runtime_evidence/generate_runtime_execution.py",
    "scripts/generate_mandate_restriction_source_product_proof.py",
    "make mandate-restriction-live-proof-contract-gate",
    "make mandate-restriction-source-product-proof-contract-gate",
    "tests/unit/test_mandate_restriction_signal_evaluation.py",
    "tests/unit/test_mandate_restriction_application.py",
    "tests/unit/advise_mandate_restriction_runtime_evidence/test_runtime_execution.py",
    "tests/unit/advise_mandate_restriction_runtime_evidence/test_generator.py",
    "tests/unit/test_mandate_restriction_source_product_proof.py",
    "tests/unit/test_implementation_proof_readiness_mandate_restriction.py",
    "tests/integration/test_mandate_restriction_signal_api.py",
    "POST /api/v1/idea-signals/mandate-restriction/evaluate",
    "docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/RFC-0002-slice-00-critical-review-source-map-and-product-gap-allocation.md",
}
PLANNED_ARCHETYPE_STATUSES = {"planned"}
SUPPORTED_STATUSES = {"partially_implemented", "planned"}
SUPPORTED_SCENARIO_STATUSES = {"bounded_foundation", "planned"}
FOUNDATION_ARCHETYPES = {
    "allocation-drift-mandate-review",
    "bond-maturity-reinvestment",
    "concentration-risk-review",
    "high-volatility-drawdown-review",
    "low-income-liquidity-shortfall",
    "mandate-restriction-review",
    "missing-benchmark-review",
    "missing-risk-profile-review",
    "missing-suitability-context",
    "underperformance-review",
}


def validate_opportunity_archetype_contract(
    *,
    repository_root: Path = ROOT,
    contract_path: Path = OPPORTUNITY_ARCHETYPE_CONTRACT_PATH,
) -> list[str]:
    contract = load_opportunity_archetype_contract(
        repository_root=repository_root,
        contract_path=contract_path,
    )
    return validate_opportunity_archetype_contract_payload(
        contract,
        repository_root=repository_root,
    )


def validate_opportunity_archetype_contract_payload(
    contract: OpportunityArchetypeContract,
    *,
    repository_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    if contract.contract_id != "lotus-idea-opportunity-archetype-scenario-contract":
        errors.append(
            "opportunity archetype contract_id must be "
            "`lotus-idea-opportunity-archetype-scenario-contract`"
        )
    if contract.contract_version != "1.0.0":
        errors.append("opportunity archetype contract_version must be 1.0.0")
    if contract.repository != "lotus-idea":
        errors.append("opportunity archetype repository must be lotus-idea")
    if contract.lifecycle_status != "foundation":
        errors.append("opportunity archetype lifecycle_status must remain foundation")
    if contract.supportability_status != "not_certified":
        errors.append("opportunity archetype supportability_status must remain not_certified")
    if contract.canonical_portfolio_ref != "PB_SG_GLOBAL_BAL_001":
        errors.append("opportunity archetype canonical_portfolio_ref must remain governed")
    if contract.demo_ready:
        errors.append("opportunity archetype contract must not claim demo readiness")
    if contract.client_publication_ready:
        errors.append("opportunity archetype contract must not claim client publication")
    if contract.supported_feature_promoted:
        errors.append("opportunity archetype contract must not promote supported features")
    if contract.data_mesh_certified:
        errors.append("opportunity archetype contract must not claim data-mesh certification")
    errors.extend(_validate_source_of_truth(contract, repository_root=repository_root))
    errors.extend(_validate_archetypes(contract, repository_root=repository_root))
    return errors


def _validate_source_of_truth(
    contract: OpportunityArchetypeContract,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    missing_keys = sorted(REQUIRED_SOURCE_OF_TRUTH - set(contract.source_of_truth))
    if missing_keys:
        errors.append(
            "opportunity archetype source_of_truth missing keys: " + ", ".join(missing_keys)
        )
    for key, relative_path in sorted(contract.source_of_truth.items()):
        path = Path(relative_path)
        if key == "blueprint":
            continue
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"opportunity archetype source_of_truth.{key} path must stay relative")
            continue
        if not (repository_root / path).exists():
            errors.append(f"opportunity archetype source_of_truth.{key} path missing")
    return errors


def _validate_archetypes(
    contract: OpportunityArchetypeContract,
    *,
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    archetypes = {archetype.archetype_id: archetype for archetype in contract.archetypes}
    missing = sorted(REQUIRED_ARCHETYPES - set(archetypes))
    extra = sorted(set(archetypes) - REQUIRED_ARCHETYPES)
    if missing:
        errors.append("opportunity archetype contract missing archetypes: " + ", ".join(missing))
    if extra:
        errors.append(
            "opportunity archetype contract contains unsupported archetypes: " + ", ".join(extra)
        )
    first_journeys = [
        archetype.archetype_id
        for archetype in contract.archetypes
        if archetype.first_supported_journey
    ]
    if first_journeys != ["high-cash-idle-liquidity"]:
        errors.append("high-cash-idle-liquidity must be the only first supported journey")
    for archetype in contract.archetypes:
        if archetype.implementation_status not in SUPPORTED_STATUSES:
            errors.append(f"{archetype.archetype_id}: unsupported implementation_status")
        if archetype.source_authority_status != "source_owned":
            errors.append(f"{archetype.archetype_id}: source_authority_status must be source_owned")
        if not archetype.source_products:
            errors.append(f"{archetype.archetype_id}: source_products are required")
        if not archetype.lotus_idea_responsibility:
            errors.append(f"{archetype.archetype_id}: lotus_idea_responsibility is required")
        if not archetype.blockers:
            errors.append(f"{archetype.archetype_id}: blockers are required before promotion")
        errors.extend(
            _validate_evidence_refs(
                archetype.archetype_id, archetype.evidence_refs, repository_root
            )
        )
        errors.extend(_validate_scenarios(archetype.archetype_id, archetype.canonical_scenarios))

    high_cash = archetypes.get("high-cash-idle-liquidity")
    if high_cash is not None:
        if high_cash.implementation_status != "partially_implemented":
            errors.append("high-cash-idle-liquidity must remain partially_implemented")
        missing_products = sorted(REQUIRED_HIGH_CASH_PRODUCTS - set(high_cash.source_products))
        if missing_products:
            errors.append(
                "high-cash-idle-liquidity source_products missing: " + ", ".join(missing_products)
            )
        missing_evidence = sorted(REQUIRED_HIGH_CASH_EVIDENCE - set(high_cash.evidence_refs))
        if missing_evidence:
            errors.append(
                "high-cash-idle-liquidity evidence_refs missing: " + ", ".join(missing_evidence)
            )
    errors.extend(_validate_foundation_evidence(archetypes))

    for archetype_id, archetype in archetypes.items():
        if archetype_id == "high-cash-idle-liquidity":
            continue
        if archetype_id in FOUNDATION_ARCHETYPES:
            if archetype.implementation_status != "partially_implemented":
                errors.append(f"{archetype_id}: foundation archetype must be partially_implemented")
            continue
        if archetype.implementation_status not in PLANNED_ARCHETYPE_STATUSES:
            errors.append(f"{archetype_id}: non-initial archetypes must remain planned")
    return errors


def _validate_foundation_evidence(archetypes: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for archetype_id, required_evidence in (
        ("concentration-risk-review", REQUIRED_CONCENTRATION_EVIDENCE),
        ("underperformance-review", REQUIRED_UNDERPERFORMANCE_EVIDENCE),
        ("allocation-drift-mandate-review", REQUIRED_MANAGE_EVIDENCE),
        ("high-volatility-drawdown-review", REQUIRED_HIGH_VOLATILITY_EVIDENCE),
        ("missing-suitability-context", REQUIRED_MISSING_SUITABILITY_EVIDENCE),
        ("low-income-liquidity-shortfall", REQUIRED_LOW_INCOME_EVIDENCE),
        ("bond-maturity-reinvestment", REQUIRED_BOND_MATURITY_EVIDENCE),
        ("missing-benchmark-review", REQUIRED_MISSING_BENCHMARK_EVIDENCE),
        ("missing-risk-profile-review", REQUIRED_MISSING_RISK_PROFILE_EVIDENCE),
        ("mandate-restriction-review", REQUIRED_MANDATE_RESTRICTION_EVIDENCE),
    ):
        errors.extend(_validate_required_evidence(archetypes, archetype_id, required_evidence))
    return errors


def _validate_required_evidence(
    archetypes: dict[str, object],
    archetype_id: str,
    required_evidence: set[str],
) -> list[str]:
    archetype = archetypes.get(archetype_id)
    if archetype is None:
        return []
    evidence_refs = getattr(archetype, "evidence_refs", ())
    missing_evidence = sorted(required_evidence - set(evidence_refs))
    if not missing_evidence:
        return []
    return [f"{archetype_id} evidence_refs missing: " + ", ".join(missing_evidence)]


def _validate_evidence_refs(
    archetype_id: str,
    evidence_refs: tuple[str, ...],
    repository_root: Path,
) -> list[str]:
    errors: list[str] = []
    for ref in evidence_refs:
        if ref.startswith(("GET ", "POST ", "make ", "lotus-")):
            continue
        path = Path(ref)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{archetype_id}: evidence ref `{ref}` must stay relative")
            continue
        if not (repository_root / path).exists():
            errors.append(f"{archetype_id}: evidence ref `{ref}` is missing")
    return errors


def _validate_scenarios(
    archetype_id: str,
    scenarios: tuple[object, ...],
) -> list[str]:
    errors: list[str] = []
    if not scenarios:
        errors.append(f"{archetype_id}: canonical_scenarios are required")
    for scenario in scenarios:
        scenario_status = getattr(scenario, "scenario_status", "")
        if scenario_status not in SUPPORTED_SCENARIO_STATUSES:
            errors.append(f"{archetype_id}: unsupported scenario_status `{scenario_status}`")
        if getattr(scenario, "supported_feature_promoted", True):
            errors.append(f"{archetype_id}: scenario must not promote supported features")
        if not getattr(scenario, "required_evidence", ()):
            errors.append(f"{archetype_id}: scenario required_evidence is required")
        if not getattr(scenario, "remaining_blockers", ()):
            errors.append(f"{archetype_id}: scenario remaining_blockers are required")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate lotus-idea opportunity archetype and scenario contract posture."
    )
    parser.add_argument("--contract-path", type=Path, default=OPPORTUNITY_ARCHETYPE_CONTRACT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_opportunity_archetype_contract(contract_path=args.contract_path)
    if errors:
        print("\n".join(errors))
        return 1
    print("Opportunity archetype contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
