from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from app.application.bond_maturity_live_proof import (
    BOND_MATURITY_LIVE_BLOCKERS_CLEARED,
    bond_maturity_live_proof_is_valid,
)
from app.application.implementation_proof_capability_updates import apply_blocker_proof
from app.application.implementation_proof_models import ImplementationProofCapabilityReadiness
from app.application.proof_provenance import aggregate_proof_artifact_is_current
from app.application.high_volatility_live_proof import (
    HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED,
    high_volatility_live_proof_is_valid,
)
from app.application.core_benchmark_assignment_live_proof import (
    CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED,
    core_benchmark_assignment_live_proof_is_valid,
)
from app.application.core_portfolio_state_live_proof import (
    CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED,
    core_portfolio_state_live_proof_is_valid,
)
from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED,
    low_income_core_cashflow_live_proof_is_valid,
)
from app.application.manage_mandate_live_proof import (
    MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED,
    manage_mandate_live_proof_is_valid,
)
from app.application.mandate_restriction_live_proof import (
    MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED,
    mandate_restriction_live_proof_is_valid,
)
from app.application.mandate_restriction_source_product_proof import (
    MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED,
    mandate_restriction_source_product_proof_is_valid,
)
from app.application.missing_suitability_live_proof import (
    MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED,
    missing_suitability_live_proof_is_valid,
)
from app.application.missing_risk_profile_live_proof import (
    MISSING_RISK_PROFILE_LIVE_BLOCKERS_CLEARED,
    missing_risk_profile_live_proof_is_valid,
)
from app.application.missing_risk_profile_source_product_proof import (
    MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED,
    missing_risk_profile_source_product_proof_is_valid,
)
from app.application.missing_benchmark_live_proof import (
    MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED,
    missing_benchmark_live_proof_is_valid,
)
from app.application.missing_benchmark_performance_readiness_proof import (
    MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED,
    missing_benchmark_performance_readiness_proof_is_valid,
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
from app.application.source_ingestion_runtime_evidence.runtime_execution import (
    SOURCE_INGESTION_RUNTIME_BLOCKERS_SATISFIED,
)

OpportunityProofValidator = Callable[[Mapping[str, object]], bool]
OpportunityProofApplicator = Callable[
    [ImplementationProofCapabilityReadiness, str | None],
    ImplementationProofCapabilityReadiness,
]
OpportunityProofStep = tuple[
    Mapping[str, object] | None,
    OpportunityProofValidator,
    OpportunityProofApplicator,
    str | None,
]


def _apply_opportunity_archetype_proofs(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    source_ingestion_runtime_execution_current: bool,
    source_ingestion_runtime_execution_ref: str | None,
    evaluated_at_utc: datetime,
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
    core_portfolio_state_live_proof: Mapping[str, object] | None,
    core_portfolio_state_live_proof_ref: str | None,
    bond_maturity_live_proof: Mapping[str, object] | None,
    bond_maturity_live_proof_ref: str | None,
    low_income_core_cashflow_live_proof: Mapping[str, object] | None,
    low_income_core_cashflow_live_proof_ref: str | None,
    manage_mandate_live_proof: Mapping[str, object] | None,
    manage_mandate_live_proof_ref: str | None,
    mandate_restriction_live_proof: Mapping[str, object] | None,
    mandate_restriction_live_proof_ref: str | None,
    mandate_restriction_source_product_proof: Mapping[str, object] | None,
    mandate_restriction_source_product_proof_ref: str | None,
    missing_suitability_live_proof: Mapping[str, object] | None,
    missing_suitability_live_proof_ref: str | None,
    missing_risk_profile_source_product_proof: Mapping[str, object] | None,
    missing_risk_profile_source_product_proof_ref: str | None,
    missing_risk_profile_live_proof: Mapping[str, object] | None,
    missing_risk_profile_live_proof_ref: str | None,
    missing_benchmark_live_proof: Mapping[str, object] | None,
    missing_benchmark_live_proof_ref: str | None,
    missing_benchmark_performance_readiness_proof: Mapping[str, object] | None,
    missing_benchmark_performance_readiness_proof_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    capabilities = _apply_source_ingestion_runtime_execution(
        capabilities,
        source_ingestion_runtime_execution_current=source_ingestion_runtime_execution_current,
        source_ingestion_runtime_execution_ref=source_ingestion_runtime_execution_ref,
    )
    for proof, proof_is_valid, apply_proof, proof_ref in _opportunity_proof_steps(locals()):
        capabilities = _apply_valid_opportunity_proof(
            capabilities,
            proof=proof,
            proof_is_valid=proof_is_valid,
            apply_proof=apply_proof,
            proof_ref=proof_ref,
            evaluated_at_utc=evaluated_at_utc,
        )
    return capabilities


def _opportunity_proof_steps(scope: Mapping[str, object]) -> tuple[OpportunityProofStep, ...]:
    return (
        _proof_step(
            scope,
            "risk_concentration_live",
            risk_concentration_live_proof_is_valid,
            _apply_risk_concentration_live_proof,
        ),
        _proof_step(
            scope,
            "high_volatility_live",
            high_volatility_live_proof_is_valid,
            _apply_high_volatility_live_proof,
        ),
        _proof_step(
            scope,
            "risk_drawdown_live",
            risk_drawdown_live_proof_is_valid,
            _apply_risk_drawdown_live_proof,
        ),
        _proof_step(
            scope,
            "performance_underperformance_live",
            performance_underperformance_live_proof_is_valid,
            _apply_performance_underperformance_live_proof,
        ),
        _proof_step(
            scope,
            "core_benchmark_assignment_live",
            core_benchmark_assignment_live_proof_is_valid,
            _apply_core_benchmark_assignment_live_proof,
        ),
        _proof_step(
            scope,
            "core_portfolio_state_live",
            core_portfolio_state_live_proof_is_valid,
            _apply_core_portfolio_state_live_proof,
        ),
        _proof_step(
            scope,
            "bond_maturity_live",
            bond_maturity_live_proof_is_valid,
            _apply_bond_maturity_live_proof,
        ),
        _proof_step(
            scope,
            "low_income_core_cashflow_live",
            low_income_core_cashflow_live_proof_is_valid,
            _apply_low_income_core_cashflow_live_proof,
        ),
        _proof_step(
            scope,
            "manage_mandate_live",
            manage_mandate_live_proof_is_valid,
            _apply_manage_mandate_live_proof,
        ),
        _proof_step(
            scope,
            "mandate_restriction_live",
            mandate_restriction_live_proof_is_valid,
            _apply_mandate_restriction_live_proof,
        ),
        _proof_step(
            scope,
            "mandate_restriction_source_product",
            mandate_restriction_source_product_proof_is_valid,
            _apply_mandate_restriction_source_product_proof,
        ),
        _proof_step(
            scope,
            "missing_suitability_live",
            missing_suitability_live_proof_is_valid,
            _apply_missing_suitability_live_proof,
        ),
        _proof_step(
            scope,
            "missing_risk_profile_source_product",
            missing_risk_profile_source_product_proof_is_valid,
            _apply_missing_risk_profile_source_product_proof,
        ),
        _proof_step(
            scope,
            "missing_risk_profile_live",
            missing_risk_profile_live_proof_is_valid,
            _apply_missing_risk_profile_live_proof,
        ),
        _proof_step(
            scope,
            "missing_benchmark_live",
            missing_benchmark_live_proof_is_valid,
            _apply_missing_benchmark_live_proof,
        ),
        _proof_step(
            scope,
            "missing_benchmark_performance_readiness",
            missing_benchmark_performance_readiness_proof_is_valid,
            _apply_missing_benchmark_performance_readiness_proof,
        ),
    )


def _proof_step(
    scope: Mapping[str, object],
    name: str,
    proof_is_valid: OpportunityProofValidator,
    apply_proof: OpportunityProofApplicator,
) -> OpportunityProofStep:
    return (
        _payload(scope, f"{name}_proof"),
        proof_is_valid,
        apply_proof,
        _ref(scope, f"{name}_proof_ref"),
    )


def _apply_valid_opportunity_proof(
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    *,
    proof: Mapping[str, object] | None,
    proof_is_valid: Callable[[Mapping[str, object]], bool],
    apply_proof: Callable[
        [ImplementationProofCapabilityReadiness, str | None],
        ImplementationProofCapabilityReadiness,
    ],
    proof_ref: str | None,
    evaluated_at_utc: datetime,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if not proof or not proof_is_valid(proof):
        return capabilities
    if not aggregate_proof_artifact_is_current(
        proof,
        evaluated_at_utc=evaluated_at_utc,
        proof_ref=proof_ref,
    ):
        return capabilities
    return tuple(apply_proof(capability, proof_ref) for capability in capabilities)


def _apply_source_ingestion_runtime_execution(
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    *,
    source_ingestion_runtime_execution_current: bool,
    source_ingestion_runtime_execution_ref: str | None,
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    if not source_ingestion_runtime_execution_current:
        return capabilities
    return tuple(
        apply_blocker_proof(
            capability,
            capability_ids=("opportunity-archetype-scenarios",),
            blockers_cleared=SOURCE_INGESTION_RUNTIME_BLOCKERS_SATISFIED,
            proof_ref=source_ingestion_runtime_execution_ref,
        )
        for capability in capabilities
    )


def apply_opportunity_archetype_proofs_from_scope(
    *,
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...],
    source_ingestion_runtime_execution_current: bool,
    source_ingestion_runtime_execution_ref: str | None,
    evaluated_at_utc: datetime,
    scope: Mapping[str, object],
) -> tuple[ImplementationProofCapabilityReadiness, ...]:
    return _apply_opportunity_archetype_proofs(
        capabilities=capabilities,
        source_ingestion_runtime_execution_current=source_ingestion_runtime_execution_current,
        source_ingestion_runtime_execution_ref=source_ingestion_runtime_execution_ref,
        evaluated_at_utc=evaluated_at_utc,
        risk_concentration_live_proof=_payload(scope, "risk_concentration_live_proof"),
        risk_concentration_live_proof_ref=_ref(scope, "risk_concentration_live_proof_ref"),
        high_volatility_live_proof=_payload(scope, "high_volatility_live_proof"),
        high_volatility_live_proof_ref=_ref(scope, "high_volatility_live_proof_ref"),
        risk_drawdown_live_proof=_payload(scope, "risk_drawdown_live_proof"),
        risk_drawdown_live_proof_ref=_ref(scope, "risk_drawdown_live_proof_ref"),
        performance_underperformance_live_proof=_payload(
            scope, "performance_underperformance_live_proof"
        ),
        performance_underperformance_live_proof_ref=_ref(
            scope, "performance_underperformance_live_proof_ref"
        ),
        core_benchmark_assignment_live_proof=_payload(
            scope, "core_benchmark_assignment_live_proof"
        ),
        core_benchmark_assignment_live_proof_ref=_ref(
            scope, "core_benchmark_assignment_live_proof_ref"
        ),
        core_portfolio_state_live_proof=_payload(scope, "core_portfolio_state_live_proof"),
        core_portfolio_state_live_proof_ref=_ref(scope, "core_portfolio_state_live_proof_ref"),
        bond_maturity_live_proof=_payload(scope, "bond_maturity_live_proof"),
        bond_maturity_live_proof_ref=_ref(scope, "bond_maturity_live_proof_ref"),
        low_income_core_cashflow_live_proof=_payload(scope, "low_income_core_cashflow_live_proof"),
        low_income_core_cashflow_live_proof_ref=_ref(
            scope, "low_income_core_cashflow_live_proof_ref"
        ),
        manage_mandate_live_proof=_payload(scope, "manage_mandate_live_proof"),
        manage_mandate_live_proof_ref=_ref(scope, "manage_mandate_live_proof_ref"),
        mandate_restriction_live_proof=_payload(scope, "mandate_restriction_live_proof"),
        mandate_restriction_live_proof_ref=_ref(scope, "mandate_restriction_live_proof_ref"),
        mandate_restriction_source_product_proof=_payload(
            scope, "mandate_restriction_source_product_proof"
        ),
        mandate_restriction_source_product_proof_ref=_ref(
            scope, "mandate_restriction_source_product_proof_ref"
        ),
        missing_suitability_live_proof=_payload(scope, "missing_suitability_live_proof"),
        missing_suitability_live_proof_ref=_ref(scope, "missing_suitability_live_proof_ref"),
        missing_risk_profile_source_product_proof=_payload(
            scope, "missing_risk_profile_source_product_proof"
        ),
        missing_risk_profile_source_product_proof_ref=_ref(
            scope, "missing_risk_profile_source_product_proof_ref"
        ),
        missing_risk_profile_live_proof=_payload(scope, "missing_risk_profile_live_proof"),
        missing_risk_profile_live_proof_ref=_ref(scope, "missing_risk_profile_live_proof_ref"),
        missing_benchmark_live_proof=_payload(scope, "missing_benchmark_live_proof"),
        missing_benchmark_live_proof_ref=_ref(scope, "missing_benchmark_live_proof_ref"),
        missing_benchmark_performance_readiness_proof=_payload(
            scope, "missing_benchmark_performance_readiness_proof"
        ),
        missing_benchmark_performance_readiness_proof_ref=_ref(
            scope, "missing_benchmark_performance_readiness_proof_ref"
        ),
    )


def _payload(scope: Mapping[str, object], name: str) -> Mapping[str, object] | None:
    value = scope.get(name)
    if isinstance(value, Mapping):
        return value
    return None


def _ref(scope: Mapping[str, object], name: str) -> str | None:
    value = scope.get(name)
    if isinstance(value, str):
        return value
    return None


def _apply_risk_concentration_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    risk_concentration_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=RISK_CONCENTRATION_LIVE_BLOCKERS_CLEARED,
        proof_ref=risk_concentration_live_proof_ref,
    )


def _apply_high_volatility_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    high_volatility_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED,
        proof_ref=high_volatility_live_proof_ref,
    )


def _apply_risk_drawdown_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    risk_drawdown_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=RISK_DRAWDOWN_LIVE_BLOCKERS_CLEARED,
        proof_ref=risk_drawdown_live_proof_ref,
    )


def _apply_performance_underperformance_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    performance_underperformance_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=PERFORMANCE_UNDERPERFORMANCE_LIVE_BLOCKERS_CLEARED,
        proof_ref=performance_underperformance_live_proof_ref,
    )


def _apply_core_benchmark_assignment_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    core_benchmark_assignment_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED,
        proof_ref=core_benchmark_assignment_live_proof_ref,
    )


def _apply_core_portfolio_state_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    core_portfolio_state_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED,
        proof_ref=core_portfolio_state_live_proof_ref,
    )


def _apply_bond_maturity_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    bond_maturity_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=BOND_MATURITY_LIVE_BLOCKERS_CLEARED,
        proof_ref=bond_maturity_live_proof_ref,
    )


def _apply_low_income_core_cashflow_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    low_income_core_cashflow_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED,
        proof_ref=low_income_core_cashflow_live_proof_ref,
    )


def _apply_manage_mandate_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    manage_mandate_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED,
        proof_ref=manage_mandate_live_proof_ref,
    )


def _apply_mandate_restriction_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    mandate_restriction_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED,
        proof_ref=mandate_restriction_live_proof_ref,
    )


def _apply_mandate_restriction_source_product_proof(
    capability: ImplementationProofCapabilityReadiness,
    mandate_restriction_source_product_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED,
        proof_ref=mandate_restriction_source_product_proof_ref,
    )


def _apply_missing_suitability_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_suitability_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED,
        proof_ref=missing_suitability_live_proof_ref,
    )


def _apply_missing_risk_profile_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_risk_profile_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_RISK_PROFILE_LIVE_BLOCKERS_CLEARED,
        proof_ref=missing_risk_profile_live_proof_ref,
    )


def _apply_missing_risk_profile_source_product_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_risk_profile_source_product_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED,
        proof_ref=missing_risk_profile_source_product_proof_ref,
    )


def _apply_missing_benchmark_live_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_benchmark_live_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED,
        proof_ref=missing_benchmark_live_proof_ref,
    )


def _apply_missing_benchmark_performance_readiness_proof(
    capability: ImplementationProofCapabilityReadiness,
    missing_benchmark_performance_readiness_proof_ref: str | None,
) -> ImplementationProofCapabilityReadiness:
    return apply_blocker_proof(
        capability,
        capability_ids=("opportunity-archetype-scenarios",),
        blockers_cleared=MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED,
        proof_ref=missing_benchmark_performance_readiness_proof_ref,
    )
