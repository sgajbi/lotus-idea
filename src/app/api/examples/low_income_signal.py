from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import partial
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    build_core_source_ref_request,
    return_or_raise_example_evidence,
    serialize_signal_evaluation,
)
from app.api.low_income_signals import (
    EvaluateLowIncomeSignalRequest,
    EvaluateLowIncomeSignalResponse,
)
from app.application.low_income_signal import (
    EvaluateLowIncomeFromCoreCommand,
    evaluate_low_income_signal_command,
    evaluate_low_income_signal_from_core,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreLowIncomeSourcePort,
    CoreSourceUnavailable,
)


LOW_INCOME_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/low-income/evaluate"
LOW_INCOME_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/low-income/evaluate-from-source"
)
LOW_INCOME_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Projected liquidity shortfall creates an advisor-review candidate",
    "blocked": "Incomplete, stale, denied, or unavailable Core evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "Projected cashflow above the materiality threshold creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_CORE
_TENANT_ID = "tenant-a"
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
_QUALIFYING_CASHFLOW = Decimal("-12500")
_NON_QUALIFYING_CASHFLOW = Decimal("-500")


def build_low_income_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(
            projected_cumulative_cashflow=_QUALIFYING_CASHFLOW,
        ),
        "blocked": _caller_evaluation_response(
            projected_cumulative_cashflow=_QUALIFYING_CASHFLOW,
            freshness=EvidenceFreshness.STALE,
        ),
        "suppressed": _caller_evaluation_response(
            projected_cumulative_cashflow=_QUALIFYING_CASHFLOW,
            duplicate_of_candidate_id="idea_low_income_existing",
        ),
        "notEligible": _caller_evaluation_response(
            projected_cumulative_cashflow=_NON_QUALIFYING_CASHFLOW,
        ),
    }


def build_source_backed_low_income_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _source_evaluation_response(
            projected_cumulative_cashflow=_QUALIFYING_CASHFLOW,
        ),
        "blocked": _source_evaluation_response(source_error=CoreSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            projected_cumulative_cashflow=_QUALIFYING_CASHFLOW,
            duplicate_of_candidate_id="idea_low_income_existing",
        ),
        "notEligible": _source_evaluation_response(
            projected_cumulative_cashflow=_NON_QUALIFYING_CASHFLOW,
        ),
    }


def apply_low_income_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            LOW_INCOME_EVALUATE_OPERATION_PATH,
            build_low_income_evaluation_response_examples(),
        ),
        (
            LOW_INCOME_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_low_income_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                LOW_INCOME_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    projected_cumulative_cashflow: Decimal,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = _evaluation_request(
        projected_cumulative_cashflow=projected_cumulative_cashflow,
        freshness=freshness,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_low_income_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    projected_cumulative_cashflow: Decimal = _QUALIFYING_CASHFLOW,
    duplicate_of_candidate_id: str | None = None,
    source_error: CoreSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_low_income_signal_from_core(
        EvaluateLowIncomeFromCoreCommand(
            portfolio_id=_PORTFOLIO_ID,
            tenant_id=_TENANT_ID,
            as_of_date=_AS_OF_DATE,
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        core_source=_ExampleCoreLowIncomeSource(
            evidence=_core_evidence(projected_cumulative_cashflow),
            error=source_error,
        ),
    )
    return _serialized(result)


def _evaluation_request(
    *,
    projected_cumulative_cashflow: Decimal,
    freshness: EvidenceFreshness,
    duplicate_of_candidate_id: str | None,
) -> EvaluateLowIncomeSignalRequest:
    return EvaluateLowIncomeSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        sourceReportedMinProjectedCumulativeCashflow=projected_cumulative_cashflow,
        cashMovementCount=4,
        cashMovementRef=_source_ref(
            "lotus-core:PortfolioCashMovementSummary:v1",
            freshness=freshness,
        ),
        cashflowProjectionRef=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1",
            freshness=freshness,
        ),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )


def _core_evidence(projected_cumulative_cashflow: Decimal) -> CoreLowIncomeEvidence:
    return CoreLowIncomeEvidence(
        source_reported_min_projected_cumulative_cashflow=projected_cumulative_cashflow,
        cash_movement_count=4,
        cash_movement_ref=_source_ref("lotus-core:PortfolioCashMovementSummary:v1").to_domain(),
        cashflow_projection_ref=_source_ref(
            "lotus-core:PortfolioCashflowProjection:v1"
        ).to_domain(),
    )


_source_ref = partial(
    build_core_source_ref_request,
    as_of_date=_AS_OF_DATE,
    generated_at_utc=_EVALUATED_AT,
)


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateLowIncomeSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleCoreLowIncomeSource(CoreLowIncomeSourcePort):
    evidence: CoreLowIncomeEvidence
    error: CoreSourceUnavailable | None = None

    def fetch_low_income_evidence(
        self, request: CoreLowIncomeEvidenceRequest
    ) -> CoreLowIncomeEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "LOW_INCOME_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "LOW_INCOME_EVALUATE_OPERATION_PATH",
    "LOW_INCOME_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_low_income_signal_openapi_examples",
    "build_low_income_evaluation_response_examples",
    "build_source_backed_low_income_evaluation_response_examples",
]
