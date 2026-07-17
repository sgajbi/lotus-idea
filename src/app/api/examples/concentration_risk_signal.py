from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.api.concentration_risk_signals import (
    EvaluateConcentrationRiskSignalRequest,
    EvaluateConcentrationRiskSignalResponse,
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
from app.application.concentration_risk_signal import (
    EvaluateConcentrationRiskFromRiskCommand,
    evaluate_concentration_risk_signal_command,
    evaluate_concentration_risk_signal_from_risk,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskConcentrationSourcePort,
    RiskSourceUnavailable,
)


CONCENTRATION_RISK_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/concentration-risk/evaluate"
CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/concentration-risk/evaluate-from-source"
)
CONCENTRATION_RISK_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Material concentration creates an advisor-review candidate",
    "blocked": "Incomplete, stale, denied, or unavailable Risk evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "Concentration below policy thresholds creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_RISK
_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def build_concentration_risk_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_concentration_existing"
        ),
        "notEligible": _caller_evaluation_response(
            top_position_weight=Decimal("0.05"),
            top_issuer_weight=Decimal("0.08"),
        ),
    }


def build_source_backed_concentration_risk_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=RiskSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_concentration_existing"
        ),
        "notEligible": _source_evaluation_response(
            top_position_weight=Decimal("0.05"),
            top_issuer_weight=Decimal("0.08"),
        ),
    }


def apply_concentration_risk_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            CONCENTRATION_RISK_EVALUATE_OPERATION_PATH,
            build_concentration_risk_evaluation_response_examples(),
        ),
        (
            CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_concentration_risk_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                CONCENTRATION_RISK_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    top_position_weight: Decimal = Decimal("0.18"),
    top_issuer_weight: Decimal = Decimal("0.24"),
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateConcentrationRiskSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        topPositionWeightCurrent=top_position_weight,
        topIssuerWeightCurrent=top_issuer_weight,
        issuerCoverageStatus="complete",
        concentrationRef=_concentration_ref(freshness=freshness),
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_concentration_risk_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    top_position_weight: Decimal = Decimal("0.22"),
    top_issuer_weight: Decimal = Decimal("0.27"),
    duplicate_of_candidate_id: str | None = None,
    source_error: RiskSourceUnavailable | None = None,
) -> dict[str, Any]:
    result = evaluate_concentration_risk_signal_from_risk(
        EvaluateConcentrationRiskFromRiskCommand(
            portfolio_id=_PORTFOLIO_ID,
            as_of_date=_AS_OF_DATE,
            evaluated_at_utc=_EVALUATED_AT,
            duplicate_of_candidate_id=duplicate_of_candidate_id,
        ),
        risk_source=_ExampleRiskConcentrationSource(
            evidence=_concentration_evidence(
                top_position_weight=top_position_weight,
                top_issuer_weight=top_issuer_weight,
            ),
            error=source_error,
        ),
    )
    return _serialized(result)


def _concentration_evidence(
    *,
    top_position_weight: Decimal,
    top_issuer_weight: Decimal,
) -> RiskConcentrationEvidence:
    return RiskConcentrationEvidence(
        top_position_weight_current=top_position_weight,
        top_issuer_weight_current=top_issuer_weight,
        issuer_coverage_status="complete",
        concentration_ref=_concentration_ref().to_domain(),
        concentration_diagnostic="example_not_exposed",
        entitlement_allowed=True,
    )


def _concentration_ref(
    *, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRefRequest:
    return build_source_ref_request(
        "lotus-risk:ConcentrationRiskReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        as_of_date=_AS_OF_DATE,
        generated_at_utc=_EVALUATED_AT,
        freshness=freshness,
        data_quality_status="quality_passed",
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateConcentrationRiskSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleRiskConcentrationSource(RiskConcentrationSourcePort):
    evidence: RiskConcentrationEvidence
    error: RiskSourceUnavailable | None = None

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "CONCENTRATION_RISK_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "CONCENTRATION_RISK_EVALUATE_OPERATION_PATH",
    "CONCENTRATION_RISK_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_concentration_risk_signal_openapi_examples",
    "build_concentration_risk_evaluation_response_examples",
    "build_source_backed_concentration_risk_evaluation_response_examples",
]
