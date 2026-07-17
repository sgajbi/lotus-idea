from __future__ import annotations

from collections.abc import Callable
from typing import Any

from endpoint_ai_contracts import (
    validate_ai_evaluation_success_contract,
    validate_ai_readiness_success_contract,
)
from endpoint_allocation_drift_signal_contracts import (
    validate_allocation_drift_evaluation_success_contract,
    validate_source_backed_allocation_drift_evaluation_success_contract,
)
from endpoint_bond_maturity_signal_contracts import (
    validate_bond_maturity_evaluation_success_contract,
    validate_source_backed_bond_maturity_evaluation_success_contract,
)
from endpoint_candidate_state_contracts import (
    validate_candidate_evidence_replay_success_contract,
    validate_candidate_lifecycle_success_contract,
)
from endpoint_conversion_workflow_contracts import (
    validate_conversion_intent_success_contract,
    validate_conversion_outcome_success_contract,
)
from endpoint_concentration_risk_signal_contracts import (
    validate_concentration_risk_evaluation_success_contract,
    validate_source_backed_concentration_risk_evaluation_success_contract,
)
from endpoint_drawdown_review_signal_contracts import (
    validate_drawdown_review_evaluation_success_contract,
    validate_source_backed_drawdown_review_evaluation_success_contract,
)
from endpoint_high_cash_signal_contracts import (
    validate_high_cash_evaluation_success_contract,
    validate_high_cash_persistence_success_contract,
    validate_source_backed_high_cash_evaluation_success_contract,
)
from endpoint_high_volatility_signal_contracts import (
    validate_high_volatility_evaluation_success_contract,
    validate_source_backed_high_volatility_evaluation_success_contract,
)
from endpoint_low_income_signal_contracts import (
    validate_low_income_evaluation_success_contract,
    validate_source_backed_low_income_evaluation_success_contract,
)
from endpoint_mandate_restriction_signal_contracts import (
    validate_mandate_restriction_evaluation_success_contract,
    validate_source_backed_mandate_restriction_evaluation_success_contract,
)
from endpoint_report_evidence_contracts import validate_report_evidence_pack_success_contract
from endpoint_review_workflow_contracts import (
    validate_feedback_success_contract,
    validate_review_action_success_contract,
)
from endpoint_underperformance_signal_contracts import (
    validate_source_backed_underperformance_evaluation_success_contract,
    validate_underperformance_evaluation_success_contract,
)


NamedSuccessValidator = Callable[
    [dict[str, Any], dict[str, Any] | None],
    list[str],
]

NAMED_SUCCESS_VALIDATORS: tuple[NamedSuccessValidator, ...] = (
    validate_ai_evaluation_success_contract,
    validate_ai_readiness_success_contract,
    validate_candidate_lifecycle_success_contract,
    validate_candidate_evidence_replay_success_contract,
    validate_allocation_drift_evaluation_success_contract,
    validate_source_backed_allocation_drift_evaluation_success_contract,
    validate_high_cash_evaluation_success_contract,
    validate_source_backed_high_cash_evaluation_success_contract,
    validate_high_cash_persistence_success_contract,
    validate_low_income_evaluation_success_contract,
    validate_source_backed_low_income_evaluation_success_contract,
    validate_bond_maturity_evaluation_success_contract,
    validate_source_backed_bond_maturity_evaluation_success_contract,
    validate_underperformance_evaluation_success_contract,
    validate_source_backed_underperformance_evaluation_success_contract,
    validate_concentration_risk_evaluation_success_contract,
    validate_source_backed_concentration_risk_evaluation_success_contract,
    validate_drawdown_review_evaluation_success_contract,
    validate_source_backed_drawdown_review_evaluation_success_contract,
    validate_high_volatility_evaluation_success_contract,
    validate_source_backed_high_volatility_evaluation_success_contract,
    validate_mandate_restriction_evaluation_success_contract,
    validate_source_backed_mandate_restriction_evaluation_success_contract,
    validate_conversion_intent_success_contract,
    validate_conversion_outcome_success_contract,
    validate_review_action_success_contract,
    validate_feedback_success_contract,
    validate_report_evidence_pack_success_contract,
)


def validate_named_success_contracts(
    endpoint: dict[str, Any],
    openapi_spec: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    for validator in NAMED_SUCCESS_VALIDATORS:
        errors.extend(validator(endpoint, openapi_spec))
    return errors


__all__ = ["NAMED_SUCCESS_VALIDATORS", "validate_named_success_contracts"]
