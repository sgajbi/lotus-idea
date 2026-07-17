from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from app.api.examples.openapi import (
    apply_named_response_examples,
    build_named_openapi_examples,
)
from app.api.examples.signal_evaluation import (
    return_or_raise_example_evidence,
    serialize_signal_evaluation,
)
from app.api.idea_signal_models import (
    EvaluateMandateRestrictionFromSourceRequest,
    EvaluateMandateRestrictionSignalRequest,
    EvaluateMandateRestrictionSignalResponse,
)
from app.api.signal_models import SourceRefRequest
from app.application.mandate_restriction_signal import (
    evaluate_mandate_restriction_signal_command,
    evaluate_mandate_restriction_signal_from_advise,
)
from app.domain import EvidenceFreshness, SignalEvaluationResult, SourceSystem
from app.ports.advise_sources import (
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceUnavailable,
)


MANDATE_RESTRICTION_EVALUATE_OPERATION_PATH = "/api/v1/idea-signals/mandate-restriction/evaluate"
MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_OPERATION_PATH = (
    "/api/v1/idea-signals/mandate-restriction/evaluate-from-source"
)
MANDATE_RESTRICTION_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "candidateCreated": "A source-owned restriction posture creates a compliance-review candidate",
    "blocked": "Stale, incomplete, denied, or unavailable source evidence blocks evaluation",
    "suppressed": "A known duplicate suppresses candidate creation",
    "notEligible": "A clear mandate and restriction posture creates no candidate",
}

_AS_OF_DATE = date(2026, 6, 21)
_EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
_SOURCE_AUTHORITY = SourceSystem.LOTUS_ADVISE
_EVALUATION_ID = "pev_001"


def build_mandate_restriction_evaluation_response_examples() -> dict[str, dict[str, Any]]:
    return {
        "candidateCreated": _caller_evaluation_response(),
        "blocked": _caller_evaluation_response(freshness=EvidenceFreshness.STALE),
        "suppressed": _caller_evaluation_response(
            duplicate_of_candidate_id="idea_mandate_restriction_existing"
        ),
        "notEligible": _caller_evaluation_response(
            restriction_status="CLEAR",
            changed_since_last_review=False,
            actionability_blocked=False,
        ),
    }


def build_source_backed_mandate_restriction_evaluation_response_examples() -> dict[
    str, dict[str, Any]
]:
    return {
        "candidateCreated": _source_evaluation_response(),
        "blocked": _source_evaluation_response(source_error=AdviseSourceUnavailable()),
        "suppressed": _source_evaluation_response(
            duplicate_of_candidate_id="idea_mandate_restriction_existing"
        ),
        "notEligible": _source_evaluation_response(advise_diagnostic="policy_current"),
    }


def apply_mandate_restriction_signal_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    for operation_path, examples in (
        (
            MANDATE_RESTRICTION_EVALUATE_OPERATION_PATH,
            build_mandate_restriction_evaluation_response_examples(),
        ),
        (
            MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_OPERATION_PATH,
            build_source_backed_mandate_restriction_evaluation_response_examples(),
        ),
    ):
        apply_named_response_examples(
            openapi_schema,
            operation_path=operation_path,
            examples=build_named_openapi_examples(
                examples,
                MANDATE_RESTRICTION_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES,
            ),
        )
    return openapi_schema


def _caller_evaluation_response(
    *,
    restriction_status: str = "REVIEW_REQUIRED",
    changed_since_last_review: bool = True,
    actionability_blocked: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    duplicate_of_candidate_id: str | None = None,
) -> dict[str, Any]:
    request = EvaluateMandateRestrictionSignalRequest(
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        restrictionRef=_restriction_ref(freshness=freshness),
        restrictionStatus=restriction_status,
        changedSinceLastReview=changed_since_last_review,
        actionabilityBlocked=actionability_blocked,
        entitlementAllowed=True,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    return _serialized(evaluate_mandate_restriction_signal_command(request.to_command()))


def _source_evaluation_response(
    *,
    advise_diagnostic: str = "mandate_restriction_review_required",
    duplicate_of_candidate_id: str | None = None,
    source_error: AdviseSourceUnavailable | None = None,
) -> dict[str, Any]:
    request = EvaluateMandateRestrictionFromSourceRequest(
        evaluationId=_EVALUATION_ID,
        asOfDate=_AS_OF_DATE,
        evaluatedAtUtc=_EVALUATED_AT,
        duplicateOfCandidateId=duplicate_of_candidate_id,
    )
    result = evaluate_mandate_restriction_signal_from_advise(
        request.to_command(correlation_id="corr-example", trace_id="trace-example"),
        advise_source=_ExampleAdviseMandateRestrictionSource(
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
        policy_ref=_restriction_ref().to_domain(),
        advise_diagnostic=advise_diagnostic,
        entitlement_allowed=True,
    )


def _restriction_ref(
    *, freshness: EvidenceFreshness = EvidenceFreshness.CURRENT
) -> SourceRefRequest:
    return SourceRefRequest(
        productId="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
        sourceSystem=_SOURCE_AUTHORITY,
        productVersion="v1",
        route="/advisory/policy-evaluations/pev_001/restriction-posture",
        asOfDate=_AS_OF_DATE,
        generatedAtUtc=_EVALUATED_AT,
        contentHash="sha256:mandate-restriction-review",
        dataQualityStatus="quality_passed",
        freshness=freshness,
    )


def _serialized(result: SignalEvaluationResult) -> dict[str, Any]:
    return serialize_signal_evaluation(
        result,
        response_model=EvaluateMandateRestrictionSignalResponse,
        source_authority=_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True)
class _ExampleAdviseMandateRestrictionSource(AdviseOpportunitySourcePort):
    evidence: AdvisePolicyEvaluationEvidence
    error: AdviseSourceUnavailable | None = None

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        del request
        return return_or_raise_example_evidence(self.evidence, self.error)


__all__ = [
    "MANDATE_RESTRICTION_EVALUATE_FROM_SOURCE_OPERATION_PATH",
    "MANDATE_RESTRICTION_EVALUATE_OPERATION_PATH",
    "MANDATE_RESTRICTION_EVALUATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_mandate_restriction_signal_openapi_examples",
    "build_mandate_restriction_evaluation_response_examples",
    "build_source_backed_mandate_restriction_evaluation_response_examples",
]
