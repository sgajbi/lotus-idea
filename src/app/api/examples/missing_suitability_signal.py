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
from app.api.missing_suitability_signals import (
    EvaluateMissingSuitabilityFromSourceRequest,
    EvaluateMissingSuitabilitySignalRequest,
    EvaluateMissingSuitabilitySignalResponse,
)
from app.api.signal_models import SourceRefRequest
from app.application.missing_suitability_signal import (
    evaluate_missing_suitability_context_signal_command,
    evaluate_missing_suitability_context_signal_from_advise,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.advise_sources import AdvisePolicyEvaluationEvidence, AdviseSourceUnavailable


MISSING_SUITABILITY_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/missing-suitability/evaluate"
MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/missing-suitability/evaluate-from-source"
)
MISSING_SUITABILITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "Open suitability or sign-off requirements create a compliance-review candidate",
    "blocked": "Stale, incomplete, denied, or unavailable Advise evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "A completed, signed-off workflow with no open requirements creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_ADVISE
_EVALUATION_ID = "pev_001"


def build_missing_suitability_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_missing_suitability_context_existing"
        ),
        "notEligible": _caller_evaluation_response(
            evaluation_status="COMPLETED",
            open_requirement_count=0,
            sign_off_status="APPROVED",
            sign_off_blocker_count=0,
        ),
    }


def build_source_backed_missing_suitability_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=AdviseSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_missing_suitability_context_existing"
        ),
        "notEligible": _source_evaluation_response(
            evaluation_status="COMPLETED",
            open_requirement_count=0,
            sign_off_status="APPROVED",
            sign_off_blocker_count=0,
        ),
    }


def apply_missing_suitability_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            MISSING_SUITABILITY_EVALUATE_OPERATION_PATH,
            build_missing_suitability_evaluation_response_examples(),
        ),
        (
            MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_missing_suitability_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                MISSING_SUITABILITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    evaluation_status: str = "PENDING_REVIEW",
    open_requirement_count: int = 2,
    sign_off_status: str = "PENDING_REVIEW",
    sign_off_blocker_count: int = 1,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateMissingSuitabilitySignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        policyRef=_policy_ref(freshness=freshness),
        evaluationStatus=evaluation_status,
        openRequirementCount=open_requirement_count,
        blockedRequirementCount=0,
        signOffStatus=sign_off_status,
        signOffBlockerCount=sign_off_blocker_count,
        clientReadyPublication="BLOCKED",
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_missing_suitability_context_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    evaluation_status: str = "PENDING_REVIEW",
    open_requirement_count: int = 2,
    sign_off_status: str = "PENDING_REVIEW",
    sign_off_blocker_count: int = 1,
    duplicate_of_candidate_id: str | None = None,
    source_error: AdviseSourceUnavailable | None = None,
) -> dict[str, Any]:
    request = EvaluateMissingSuitabilityFromSourceRequest(
        evaluationId=_EVALUATION_ID,
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    result = evaluate_missing_suitability_context_signal_from_advise(
        request.to_command(correlation_id="corr-example", trace_id="trace-example"),
        advise_source=ExampleAdvisePolicyEvaluationSource(
            evidence=_advise_evidence(
                evaluation_status=evaluation_status,
                open_requirement_count=open_requirement_count,
                sign_off_status=sign_off_status,
                sign_off_blocker_count=sign_off_blocker_count,
            ),
            error=source_error,
        ),
    )
    return _serialized(result)


def _advise_evidence(
    *,
    evaluation_status: str,
    open_requirement_count: int,
    sign_off_status: str,
    sign_off_blocker_count: int,
) -> AdvisePolicyEvaluationEvidence:
    return AdvisePolicyEvaluationEvidence(
        evaluation_status=evaluation_status,
        open_requirement_count=open_requirement_count,
        blocked_requirement_count=0,
        sign_off_status=sign_off_status,
        sign_off_blocker_count=sign_off_blocker_count,
        client_ready_publication="BLOCKED",
        policy_ref=_policy_ref().to_domain(),
        entitlement_allowed=True,
    )


def _policy_ref(*, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRefRequest:
    return SourceRefRequest(
        productId="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        sourceSystem=_SOURCE_AUTHORITY,
        productVersion="v1",
        route="/advisory/policy-evaluations/pev_001/workflow",
        asOfDate=_AS_OF_DATE,
        generatedAtUtc=_EVALUATED_AT,
        contentHash="sha256:missing-suitability-context-review",
        dataQualityStatus="quality_passed",
        freshness=freshness,
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateMissingSuitabilitySignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


__all__ = [
    "MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "MISSING_SUITABILITY_EVALUATE_OPERATION_PATH",
    "MISSING_SUITABILITY_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_missing_suitability_signal_openapi_examples",
    "build_missing_suitability_evaluation_response_examples",
    "build_source_backed_missing_suitability_evaluation_response_examples",
]
