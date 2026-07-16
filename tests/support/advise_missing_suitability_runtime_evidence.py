from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from app.application.advise_missing_suitability_runtime_evidence import (
    EvaluateAdviseMissingSuitability,
    build_advise_missing_suitability_runtime_execution,
    evaluate_advise_missing_suitability,
)
from app.ports.advise_sources import (
    AdvisePolicyEvaluationRuntimeEvidence,
)
from tests.support.advise_policy_runtime_evidence import (
    AuthoritativeAdvisePolicyEvaluationSource,
)


class AuthoritativeAdviseMissingSuitabilitySource(AuthoritativeAdvisePolicyEvaluationSource):
    def __init__(
        self,
        *,
        tenant_id: str = "tenant-a",
        portfolio_id: str = "portfolio-a",
        context_missing: bool = True,
        runtime_mutation: Callable[
            [AdvisePolicyEvaluationRuntimeEvidence], AdvisePolicyEvaluationRuntimeEvidence
        ]
        | None = None,
    ) -> None:
        self.context_missing = context_missing
        super().__init__(
            diagnostic=(
                "advise_policy_requirements_open"
                if self.context_missing
                else "advise_policy_context_available"
            ),
            workflow_review_required=context_missing,
            tenant_id=tenant_id,
            portfolio_id=portfolio_id,
            runtime_mutation=runtime_mutation,
        )


def valid_advise_missing_suitability_runtime_evidence(
    *,
    evaluated_at_utc: datetime,
    as_of_date: date | None = None,
    context_missing: bool = True,
) -> dict[str, Any]:
    result = evaluate_advise_missing_suitability(
        EvaluateAdviseMissingSuitability(
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
        advise_source=AuthoritativeAdviseMissingSuitabilitySource(context_missing=context_missing),
    )
    return build_advise_missing_suitability_runtime_execution(
        generated_at_utc=evaluated_at_utc,
        result=result,
    )
