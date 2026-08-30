from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.api.allocation_drift_signals import (
    EvaluateAllocationDriftFromSourceRequest,
    EvaluateAllocationDriftSignalRequest,
)
from app.api.bond_maturity_signals import (
    EvaluateBondMaturityFromSourceRequest,
    EvaluateBondMaturitySignalRequest,
)
from app.api.concentration_risk_signals import (
    EvaluateConcentrationRiskFromSourceRequest,
    EvaluateConcentrationRiskSignalRequest,
)
from app.api.drawdown_review_signals import (
    EvaluateDrawdownReviewFromSourceRequest,
    EvaluateDrawdownReviewSignalRequest,
)
from app.api.high_volatility_signals import (
    EvaluateHighVolatilityFromSourceRequest,
    EvaluateHighVolatilitySignalRequest,
)
from app.api.idea_signal_models import (
    EvaluateHighCashFromSourceRequest,
    EvaluateHighCashSignalRequest,
    EvaluateMandateRestrictionFromSourceRequest,
    EvaluateMandateRestrictionSignalRequest,
)
from app.api.low_income_signals import (
    EvaluateLowIncomeFromSourceRequest,
    EvaluateLowIncomeSignalRequest,
)
from app.api.missing_benchmark_signals import (
    EvaluateMissingBenchmarkFromSourceRequest,
    EvaluateMissingBenchmarkSignalRequest,
)
from app.api.missing_risk_profile_signals import (
    EvaluateMissingRiskProfileFromSourceRequest,
    EvaluateMissingRiskProfileSignalRequest,
)
from app.api.missing_suitability_signals import (
    EvaluateMissingSuitabilityFromSourceRequest,
    EvaluateMissingSuitabilitySignalRequest,
)
from app.api.underperformance_signals import (
    EvaluateUnderperformanceFromSourceRequest,
    EvaluateUnderperformanceSignalRequest,
)


EVALUATION_REQUEST_MODELS = (
    EvaluateHighCashSignalRequest,
    EvaluateHighCashFromSourceRequest,
    EvaluateConcentrationRiskSignalRequest,
    EvaluateConcentrationRiskFromSourceRequest,
    EvaluateAllocationDriftSignalRequest,
    EvaluateAllocationDriftFromSourceRequest,
    EvaluateUnderperformanceSignalRequest,
    EvaluateUnderperformanceFromSourceRequest,
    EvaluateHighVolatilitySignalRequest,
    EvaluateHighVolatilityFromSourceRequest,
    EvaluateDrawdownReviewSignalRequest,
    EvaluateDrawdownReviewFromSourceRequest,
    EvaluateBondMaturitySignalRequest,
    EvaluateBondMaturityFromSourceRequest,
    EvaluateLowIncomeSignalRequest,
    EvaluateLowIncomeFromSourceRequest,
    EvaluateMissingBenchmarkSignalRequest,
    EvaluateMissingBenchmarkFromSourceRequest,
    EvaluateMissingRiskProfileSignalRequest,
    EvaluateMissingRiskProfileFromSourceRequest,
    EvaluateMissingSuitabilitySignalRequest,
    EvaluateMissingSuitabilityFromSourceRequest,
    EvaluateMandateRestrictionSignalRequest,
    EvaluateMandateRestrictionFromSourceRequest,
)


@pytest.mark.parametrize("request_model", EVALUATION_REQUEST_MODELS)
def test_signal_requests_do_not_accept_caller_asserted_duplicate_authority(
    request_model: type[BaseModel],
) -> None:
    schema = request_model.model_json_schema(by_alias=True)

    assert schema.get("additionalProperties") is False
    assert "duplicateOfCandidateId" not in schema["properties"]
