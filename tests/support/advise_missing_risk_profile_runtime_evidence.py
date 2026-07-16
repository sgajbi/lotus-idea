from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from app.application.advise_missing_risk_profile_runtime_evidence import (
    EvaluateAdviseMissingRiskProfile,
    build_advise_missing_risk_profile_runtime_execution,
    evaluate_advise_missing_risk_profile,
)
from app.ports.advise_sources import AdvisePolicyEvaluationRuntimeEvidence
from tests.support.advise_policy_runtime_evidence import (
    AuthoritativeAdvisePolicyEvaluationSource,
)


class AuthoritativeAdviseMissingRiskProfileSource(AuthoritativeAdvisePolicyEvaluationSource):
    def __init__(
        self,
        *,
        diagnostic: str = "risk_profile_missing",
        tenant_id: str = "tenant-a",
        portfolio_id: str = "portfolio-a",
        runtime_mutation: Callable[
            [AdvisePolicyEvaluationRuntimeEvidence], AdvisePolicyEvaluationRuntimeEvidence
        ]
        | None = None,
    ) -> None:
        super().__init__(
            diagnostic=diagnostic,
            workflow_review_required=diagnostic
            not in {
                "risk_profile_current",
                "client_risk_profile_current",
            },
            tenant_id=tenant_id,
            portfolio_id=portfolio_id,
            runtime_mutation=runtime_mutation,
        )


def valid_advise_missing_risk_profile_runtime_evidence(
    *,
    evaluated_at_utc: datetime,
    as_of_date: date | None = None,
    diagnostic: str = "risk_profile_missing",
) -> dict[str, Any]:
    result = evaluate_advise_missing_risk_profile(
        EvaluateAdviseMissingRiskProfile(
            tenant_id="tenant-a",
            book_id="book-a",
            portfolio_id="portfolio-a",
            client_id="client-a",
            evaluation_id="evaluation-a",
            as_of_date=as_of_date or evaluated_at_utc.date(),
            evaluated_at_utc=evaluated_at_utc,
            correlation_id="corr-advise",
            trace_id="trace-advise",
        ),
        advise_source=AuthoritativeAdviseMissingRiskProfileSource(diagnostic=diagnostic),
    )
    return build_advise_missing_risk_profile_runtime_execution(
        generated_at_utc=evaluated_at_utc,
        result=result,
    )
