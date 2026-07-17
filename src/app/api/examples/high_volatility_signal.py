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
from app.api.high_volatility_signals import (
    EvaluateHighVolatilitySignalRequest,
    EvaluateHighVolatilitySignalResponse,
)
from app.api.signal_models import SourceRefRequest
from app.application.high_volatility_signal import (
    EvaluateHighVolatilityFromRiskCommand,
    evaluate_high_volatility_signal_command,
    evaluate_high_volatility_signal_from_risk,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.risk_sources import (
    RiskSourceUnavailable,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
    RiskVolatilitySourcePort,
)


HIGH_VOLATILITY_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/high-volatility/evaluate"
HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/high-volatility/evaluate-from-source"
)
HIGH_VOLATILITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Material volatility creates an advisor-review candidate",
    "blocked": "Incomplete, stale, denied, or unavailable Risk evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "Volatility below the policy threshold creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_RISK
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def build_high_volatility_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_high_volatility_existing"
        ),
        "notEligible": _caller_evaluation_response(source_reported_volatility=Decimal("8.50")),
    }


def build_source_backed_high_volatility_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=RiskSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_high_volatility_existing"
        ),
        "notEligible": _source_evaluation_response(source_reported_volatility=Decimal("8.50")),
    }


def apply_high_volatility_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            HIGH_VOLATILITY_EVALUATE_OPERATION_PATH,
            build_high_volatility_evaluation_response_examples(),
        ),
        (
            HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_high_volatility_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                HIGH_VOLATILITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    source_reported_volatility: Decimal = Decimal("14.25"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateHighVolatilitySignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        sourceReportedVolatility=source_reported_volatility,
        riskSupportabilityState="ready",
        riskRef=_risk_ref(freshness=freshness),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_high_volatility_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    source_reported_volatility: Decimal = Decimal("14.25"),
    duplicate_of_candidate_id: str | None = None,
    source_error: RiskSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_high_volatility_signal_from_risk(
        EvaluateHighVolatilityFromRiskCommand(
            portfolio_id=_PORTFOLIO_ID,
            as_of_date=_AS_OF_DATE,
            period_name="YTD",
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        risk_source=_ExampleRiskVolatilitySource(
            evidence=_volatility_evidence(
                source_reported_volatility=source_reported_volatility,
            ),
            error=source_error,
        ),
    )
    return _serialized(result)


def _volatility_evidence(
    *,
    source_reported_volatility: Decimal,
) -> RiskVolatilityEvidence:
    return RiskVolatilityEvidence(
        source_reported_volatility=source_reported_volatility,
        risk_supportability_state="ready",
        risk_ref=_risk_ref().to_domain(),
        risk_diagnostic="example_not_exposed",
        entitlement_allowed=True,
    )


def _risk_ref(*, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRefRequest:
    return build_source_ref_request(
        "lotus-risk:RiskMetricsReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
        data_quality_status="ready",
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateHighVolatilitySignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleRiskVolatilitySource(RiskVolatilitySourcePort):
    evidence: RiskVolatilityEvidence
    error: RiskSourceUnavailable | None = None

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "HIGH_VOLATILITY_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "HIGH_VOLATILITY_EVALUATE_OPERATION_PATH",
    "HIGH_VOLATILITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_high_volatility_signal_openapi_examples",
    "build_high_volatility_evaluation_response_examples",
    "build_source_backed_high_volatility_evaluation_response_examples",
]
