from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.api.drawdown_review_signals import (
    EvaluateDrawdownReviewSignalRequest,
    EvaluateDrawdownReviewSignalResponse,
)
from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    build_source_ref_request,
    return_or_raise_example_evidence,
    serialize_signal_evaluation,
)
from app.api.signal_models import SourceRefRequest
from app.application.drawdown_review_signal import (
    EvaluateDrawdownReviewFromRiskCommand,
    evaluate_drawdown_review_signal_command,
    evaluate_drawdown_review_signal_from_risk,
)
from app.domain import (
    DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY,
    EvidenceFreshness,
    SignalEvaluationResult,
    SourceSystem,
)
from app.ports.risk_sources import (
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
    RiskDrawdownSourcePort,
    RiskSourceUnavailable,
)


DRAWDOWN_REVIEW_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/drawdown-review/evaluate"
DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/drawdown-review/evaluate-from-source"
)
DRAWDOWN_REVIEW_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Material drawdown creates an advisor-review candidate",
    "blocked": "Incomplete, stale, denied, or unavailable Risk evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "Drawdown below the policy threshold creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_RISK
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def build_drawdown_review_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_drawdown_review_existing"
        ),
        "notEligible": _caller_evaluation_response(source_reported_max_drawdown=Decimal("-0.025")),
    }


def build_source_backed_drawdown_review_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=RiskSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_drawdown_review_existing"
        ),
        "notEligible": _source_evaluation_response(source_reported_max_drawdown=Decimal("-0.025")),
    }


def apply_drawdown_review_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            DRAWDOWN_REVIEW_EVALUATE_OPERATION_PATH,
            build_drawdown_review_evaluation_response_examples(),
        ),
        (
            DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_drawdown_review_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                DRAWDOWN_REVIEW_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    source_reported_max_drawdown: Decimal = Decimal("-0.1245"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateDrawdownReviewSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        sourceReportedMaxDrawdown=source_reported_max_drawdown,
        riskSupportabilityState="ready",
        drawdownRef=_drawdown_ref(freshness=freshness),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_drawdown_review_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    source_reported_max_drawdown: Decimal = Decimal("-0.1245"),
    duplicate_of_candidate_id: str | None = None,
    source_error: RiskSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_drawdown_review_signal_from_risk(
        EvaluateDrawdownReviewFromRiskCommand(
            portfolio_id=_PORTFOLIO_ID,
            as_of_date=_AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        risk_source=_ExampleRiskDrawdownSource(
            evidence=_drawdown_evidence(
                source_reported_max_drawdown=source_reported_max_drawdown,
            ),
            error=source_error,
        ),
    )
    return _serialized(result)


def _drawdown_evidence(
    *,
    source_reported_max_drawdown: Decimal,
) -> RiskDrawdownEvidence:
    return RiskDrawdownEvidence(
        source_reported_max_drawdown=source_reported_max_drawdown,
        risk_supportability_state="ready",
        risk_ref=_drawdown_ref().to_domain(),
        risk_diagnostic="example_not_exposed",
        entitlement_allowed=True,
    )


def _drawdown_ref(*, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRefRequest:
    return build_source_ref_request(
        DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.source_product_id,
        source_system=SourceSystem.LOTUS_RISK,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
        data_quality_status="ready",
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateDrawdownReviewSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleRiskDrawdownSource(RiskDrawdownSourcePort):
    evidence: RiskDrawdownEvidence
    error: RiskSourceUnavailable | None = None

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "DRAWDOWN_REVIEW_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "DRAWDOWN_REVIEW_EVALUATE_OPERATION_PATH",
    "DRAWDOWN_REVIEW_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_drawdown_review_signal_openapi_examples",
    "build_drawdown_review_evaluation_response_examples",
    "build_source_backed_drawdown_review_evaluation_response_examples",
]
