from __future__ import annotations

from collections.abc import Mapping

from app.application.implementation_proof_capability_updates import _apply_blocker_proof
from app.application.implementation_proof_models import ImplementationProofCapabilityReadiness
from app.application.high_volatility_live_proof import (
    HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED,
    high_volatility_live_proof_is_valid,
)
from app.application.core_benchmark_assignment_live_proof import (
    CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED,
    core_benchmark_assignment_live_proof_is_valid,
)
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED,
    low_income_core_cashflow_live_proof_is_valid,
)
from app.application.manage_mandate_live_proof import (
    MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED,
    manage_mandate_live_proof_is_valid,
)
from app.application.missing_suitability_live_proof import (
    MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED,
    missing_suitability_live_proof_is_valid,
)
from app.application.missing_risk_profile_live_proof import (
    MISSING_RISK_PROFILE_LIVE_BLOCKERS_CLEARED,
    missing_risk_profile_live_proof_is_valid,
)
from app.application.performance_underperformance_live_proof import (
    PERFORMANCE_UNDERPERFORMANCE_LIVE_BLOCKERS_CLEARED,
    performance_underperformance_live_proof_is_valid,
)
from app.application.risk_concentration_live_proof import (
    RISK_CONCENTRATION_LIVE_BLOCKERS_CLEARED,
    risk_concentration_live_proof_is_valid,
)
from app.application.risk_drawdown_live_proof import (
    RISK_DRAWDOWN_LIVE_BLOCKERS_CLEARED,
    risk_drawdown_live_proof_is_valid,
)
from app.application.source_ingestion_live_proof import HIGH_CASH_LIVE_CORE_BLOCKERS_CLEARED


def _apply_opportunity_archetype_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    source_ingestion_live_proof_valid: bool,
    source_ingestion_live_proof_ref: str | None,
    risk_concentration_live_proof: Mapping[str, object] | None,
    risk_concentration_live_proof_ref: str | None,
    high_volatility_live_proof: Mapping[str, object] | None,
    high_volatility_live_proof_ref: str | None,
    risk_drawdown_live_proof: Mapping[str, object] | None,
    risk_drawdown_live_proof_ref: str | None,
    performance_underperformance_live_proof: Mapping[str, object] | None,
    performance_underperformance_live_proof_ref: str | None,
    core_benchmark_assignment_live_proof: Mapping[str, object] | None,
    core_benchmark_assignment_live_proof_ref: str | None,
    low_income_core_cashflow_live_proof: Mapping[str, object] | None,
    low_income_core_cashflow_live_proof_ref: str | None,
    manage_mandate_live_proof: Mapping[str, object] | None,
    manage_mandate_live_proof_ref: str | None,
    missing_suitability_live_proof: Mapping[str, object] | None,
    missing_suitability_live_proof_ref: str | None,
    missing_risk_profile_live_proof: Mapping[str, object] | None,
    missing_risk_profile_live_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if source_ingestion_live_proof_valid:
        capabilities = tuple(
            _apply_blocker_proof(
                capability,
                capability_ids=("opportunity-archetype-scenarios",),
                blockers_cleared=HIGH_CASH_LIVE_CORE_BLOCKERS_CLEARED,
                proof_ref=source_ingestion_live_proof_ref,
            )
            for capability in capabilities
        )
    if risk_concentration_live_proof and risk_concentration_live_proof_is_valid(
        risk_concentration_live_proof
    ):
        capabilities = tuple(
            _apply_risk_concentration_live_proof(capability, risk_concentration_live_proof_ref)
            for capability in capabilities
        )
    if high_volatility_live_proof and high_volatility_live_proof_is_valid(
        high_volatility_live_proof
    ):
        capabilities = tuple(
            _apply_high_volatility_live_proof(capability, high_volatility_live_proof_ref)
            for capability in capabilities
        )
    if risk_drawdown_live_proof and risk_drawdown_live_proof_is_valid(risk_drawdown_live_proof):
        capabilities = tuple(
            _apply_risk_drawdown_live_proof(capability, risk_drawdown_live_proof_ref)
            for capability in capabilities
        )
    if performance_underperformance_live_proof and performance_underperformance_live_proof_is_valid(
        performance_underperformance_live_proof
    ):
        capabilities = tuple(
            _apply_performance_underperformance_live_proof(
                capability,
                performance_underperformance_live_proof_ref,
            )
            for capability in capabilities
        )
    if core_benchmark_assignment_live_proof and core_benchmark_assignment_live_proof_is_valid(
        core_benchmark_assignment_live_proof
    ):
        capabilities = tuple(
            _apply_core_benchmark_assignment_live_proof(
                capability,
                core_benchmark_assignment_live_proof_ref,
            )
            for capability in capabilities
        )
    if low_income_core_cashflow_live_proof and low_income_core_cashflow_live_proof_is_valid(
        low_income_core_cashflow_live_proof
    ):
        capabilities = tuple(
            _apply_low_income_core_cashflow_live_proof(
                capability,
                low_income_core_cashflow_live_proof_ref,
            )
            for capability in capabilities
        )
    if manage_mandate_live_proof and manage_mandate_live_proof_is_valid(manage_mandate_live_proof):
        capabilities = tuple(
            _apply_manage_mandate_live_proof(capability, manage_mandate_live_proof_ref)
            for capability in capabilities
        )
    if missing_suitability_live_proof and missing_suitability_live_proof_is_valid(
        missing_suitability_live_proof
    ):
        capabilities = tuple(
            _apply_missing_suitability_live_proof(
                capability,
                missing_suitability_live_proof_ref,
            )
            for capability in capabilities
        )
    if missing_risk_profile_live_proof and missing_risk_profile_live_proof_is_valid(
        missing_risk_profile_live_proof
    ):
        capabilities = tuple(
            _apply_missing_risk_profile_live_proof(
                capability,
                missing_risk_profile_live_proof_ref,
            )
            for capability in capabilities
        )
    return capabilities


def _apply_risk_concentration_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    risk_concentration_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=RISK_CONCENTRATION_LIVE_BLOCKERS_CLEARED,
        proof_ref=risk_concentration_live_proof_ref,
    )


def _apply_high_volatility_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    high_volatility_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED,
        proof_ref=high_volatility_live_proof_ref,
    )


def _apply_risk_drawdown_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    risk_drawdown_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=RISK_DRAWDOWN_LIVE_BLOCKERS_CLEARED,
        proof_ref=risk_drawdown_live_proof_ref,
    )


def _apply_performance_underperformance_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    performance_underperformance_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=PERFORMANCE_UNDERPERFORMANCE_LIVE_BLOCKERS_CLEARED,
        proof_ref=performance_underperformance_live_proof_ref,
    )


def _apply_core_benchmark_assignment_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    core_benchmark_assignment_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED,
        proof_ref=core_benchmark_assignment_live_proof_ref,
    )


def _apply_low_income_core_cashflow_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    low_income_core_cashflow_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED,
        proof_ref=low_income_core_cashflow_live_proof_ref,
    )


def _apply_manage_mandate_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    manage_mandate_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED,
        proof_ref=manage_mandate_live_proof_ref,
    )


def _apply_missing_suitability_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_suitability_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED,
        proof_ref=missing_suitability_live_proof_ref,
    )


def _apply_missing_risk_profile_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_risk_profile_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return _apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_RISK_PROFILE_LIVE_BLOCKERS_CLEARED,
        proof_ref=missing_risk_profile_live_proof_ref,
    )
