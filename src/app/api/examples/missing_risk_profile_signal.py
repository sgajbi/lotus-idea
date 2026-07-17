from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    ExampleAdvisePolicyEvaluationSource,
    serialize_signal_evaluation,
)
from app.api.missing_risk_profile_signals import (
    EvaluateMissingRiskProfileFromSourceRequest,
    EvaluateMissingRiskProfileSignalRequest,
    EvaluateMissingRiskProfileSignalResponse,
)
from app.api.signal_models import SourceRefRequest
from app.application.missing_risk_profile_signal import (
    evaluate_missing_risk_profile_signal_command,
    evaluate_missing_risk_profile_signal_from_advise,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.advise_sources import AdvisePolicyEvaluationEvidence, AdviseSourceUnavailable


MISSING_RISK_PROFILE_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/missing-risk-profile/evaluate"
MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/missing-risk-profile/evaluate-from-source"
)
MISSING_RISK_PROFILE_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "A missing or stale client risk profile creates an advisor-review candidate",
    "blocked": "Stale, incomplete, denied, or unavailable Advise evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "A current client risk profile creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_ADVISE
_EVALUATION_ID = "pev_001"


def build_missing_risk_profile_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_missing_risk_profile_existing"
        ),
        "notEligible": _caller_evaluation_response(
            risk_profile_status="CURRENT",
            risk_profile_effective_for_as_of_date=True,
            risk_profile_review_due=False,
        ),
    }


def build_source_backed_missing_risk_profile_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=AdviseSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_missing_risk_profile_existing"
        ),
        "notEligible": _source_evaluation_response(advise_diagnostic="risk_profile_current"),
    }


def apply_missing_risk_profile_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            MISSING_RISK_PROFILE_EVALUATE_OPERATION_PATH,
            build_missing_risk_profile_evaluation_response_examples(),
        ),
        (
            MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_missing_risk_profile_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                MISSING_RISK_PROFILE_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    risk_profile_status: str = "STALE",
    risk_profile_effective_for_as_of_date: bool = False,
    risk_profile_review_due: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateMissingRiskProfileSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        riskProfileRef=_risk_profile_ref(freshness=freshness),
        riskProfileStatus=risk_profile_status,
        riskProfileEffectiveForAsOfDate=risk_profile_effective_for_as_of_date,
        riskProfileReviewDue=risk_profile_review_due,
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_missing_risk_profile_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    advise_diagnostic: str = "risk_profile_missing",
    duplicate_of_candidate_id: str | None = None,
    source_error: AdviseSourceUnavailable | None = None,
) -> dict[str, Any]:
    request = EvaluateMissingRiskProfileFromSourceRequest(
        evaluationId=_EVALUATION_ID,
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    result = evaluate_missing_risk_profile_signal_from_advise(
        request.to_command(correlation_id="corr-example", trace_id="trace-example"),
        advise_source=ExampleAdvisePolicyEvaluationSource(
            evidence=_advise_evidence(advise_diagnostic=advise_diagnostic),
            error=source_error,
        ),
    )
    return _serialized(result)


def _advise_evidence(*, advise_diagnostic: str) -> AdvisePolicyEvaluationEvidence:
    return AdvisePolicyEvaluationEvidence(
        evaluation_status="PENDING_REVIEW",
        open_requirement_count=0,
        blocked_requirement_count=0,
        sign_off_status="PENDING_REVIEW",
        sign_off_blocker_count=0,
        client_ready_publication="BLOCKED",
        policy_ref=_risk_profile_ref().to_domain(),
        advise_diagnostic=advise_diagnostic,
        entitlement_allowed=True,
    )


def _risk_profile_ref(
    *, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRefRequest:
    return SourceRefRequest(
        productId="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        sourceSystem=_SOURCE_AUTHORITY,
        productVersion="v1",
        route="/advisory/policy-evaluations/pev_001/risk-profile-posture",
        asOfDate=_AS_OF_DATE,
        generatedAtUtc=_EVALUATED_AT,
        contentHash="sha256:missing-risk-profile-review",
        dataQualityStatus="quality_passed",
        freshness=freshness,
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateMissingRiskProfileSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


__all__ = [
    "MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "MISSING_RISK_PROFILE_EVALUATE_OPERATION_PATH",
    "MISSING_RISK_PROFILE_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_missing_risk_profile_signal_openapi_examples",
    "build_missing_risk_profile_evaluation_response_examples",
    "build_source_backed_missing_risk_profile_evaluation_response_examples",
]
