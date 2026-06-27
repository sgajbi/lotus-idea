from __future__ import annotations

from collections.abc import Mapping

from app.application.implementation_proof_capability_updates import _apply_blocker_proof
from app.application.implementation_proof_models import ImplementationProofCapabilityReadiness
from app.application.high_volatility_live_proof import (
    HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED,
    high_volatility_live_proof_is_valid,
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
