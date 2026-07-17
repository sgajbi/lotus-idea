from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    build_source_ref_request,
    return_or_raise_example_evidence,
    serialize_signal_evaluation,
)
from app.api.underperformance_signals import (
    EvaluateUnderperformanceSignalRequest,
    EvaluateUnderperformanceSignalResponse,
)
from app.api.signal_models import SourceRefRequest
from app.application.underperformance_signal import (
    EvaluateUnderperformanceFromPerformanceCommand,
    evaluate_underperformance_signal_command,
    evaluate_underperformance_signal_from_performance,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.performance_sources import (
    PerformanceSourceUnavailable,
    PerformanceUnderperformanceEvidence,
    PerformanceUnderperformanceEvidenceRequest,
    PerformanceUnderperformanceSourcePort,
)


UNDERPERFORMANCE_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/underperformance/evaluate"
UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/underperformance/evaluate-from-source"
)
UNDERPERFORMANCE_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Material active underperformance creates an advisor-review candidate",
    "blocked": "Incomplete, stale, denied, or unavailable Performance evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "Active return above the attention threshold creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_PERFORMANCE
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def build_underperformance_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_underperformance_existing"
        ),
        "notEligible": _caller_evaluation_response(active_return=Decimal("-0.001")),
    }


def build_source_backed_underperformance_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=PerformanceSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_underperformance_existing"
        ),
        "notEligible": _source_evaluation_response(active_return=Decimal("-0.001")),
    }


def apply_underperformance_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            UNDERPERFORMANCE_EVALUATE_OPERATION_PATH,
            build_underperformance_evaluation_response_examples(),
        ),
        (
            UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_underperformance_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                UNDERPERFORMANCE_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    active_return: Decimal = Decimal("-0.0125"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateUnderperformanceSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        sourceReportedActiveReturn=active_return,
        benchmarkContextAvailable=True,
        performanceRef=_performance_ref(freshness=freshness),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_underperformance_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    active_return: Decimal = Decimal("-0.0125"),
    duplicate_of_candidate_id: str | None = None,
    source_error: PerformanceSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_underperformance_signal_from_performance(
        EvaluateUnderperformanceFromPerformanceCommand(
            portfolio_id=_PORTFOLIO_ID,
            as_of_date=_AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
            reporting_currency="USD",
        ),
        performance_source=_ExamplePerformanceUnderperformanceSource(
            evidence=_performance_evidence(active_return),
            error=source_error,
        ),
    )
    return _serialized(result)


def _performance_evidence(active_return: Decimal) -> PerformanceUnderperformanceEvidence:
    return PerformanceUnderperformanceEvidence(
        source_reported_active_return=active_return,
        benchmark_context_available=True,
        performance_ref=_performance_ref().to_domain(),
        performance_diagnostic="example_not_exposed",
        entitlement_allowed=True,
    )


def _performance_ref(
    *, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRefRequest:
    return build_source_ref_request(
        "lotus-performance:ReturnsSeriesBundle:v1",
        source_system=SourceSystem.LOTUS_PERFORMANCE,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
        data_quality_status="ready",
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateUnderperformanceSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExamplePerformanceUnderperformanceSource(PerformanceUnderperformanceSourcePort):
    evidence: PerformanceUnderperformanceEvidence
    error: PerformanceSourceUnavailable | None = None

    def fetch_underperformance_evidence(
        self, request: PerformanceUnderperformanceEvidenceRequest
    ) -> PerformanceUnderperformanceEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "UNDERPERFORMANCE_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "UNDERPERFORMANCE_EVALUATE_OPERATION_PATH",
    "UNDERPERFORMANCE_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_underperformance_signal_openapi_examples",
    "build_source_backed_underperformance_evaluation_response_examples",
    "build_underperformance_evaluation_response_examples",
]
