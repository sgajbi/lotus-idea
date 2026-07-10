from __future__ import annotations

from datetime import date, datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.problem_details import (
    problem_details_response as problem_response,
    service_unavailable_metadata,
)
from app.api.runtime_dependencies import AdvisePolicyEvaluationSourceRuntimeBlocker
from app.api.runtime_dependencies import (
    build_advise_policy_evaluation_source_runtime_from_environment as _build_advise_policy_evaluation_source_runtime_from_environment,
)
from app.api.signal_models import (
    ReviewAccessScopeRequest,
    SignalEvaluationResponse,
    SourceRefRequest,
)
from app.api.temporal_validation import require_timezone_aware
from app.api.signal_api_support import (
    RouteMetadata,
    SignalSourceRefContract,
    evaluate_caller_supplied_signal,
    emit_signal_evaluation_event,
    signal_permission_problem_or_none,
    signal_problem_responses,
    source_authority_from_contracts,
    close_signal_source_runtime,
)
from app.application.missing_risk_profile_signal import (
    EvaluateMissingRiskProfileFromAdviseCommand,
    EvaluateMissingRiskProfileSignalCommand,
    evaluate_missing_risk_profile_signal_from_advise,
    evaluate_missing_risk_profile_signal_command,
)
from app.domain import SourceSystem
from app.observability import IdeaOperation, OperationOutcome, emit_foundation_operation_event


class EvaluateMissingRiskProfileSignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned risk-profile posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    risk_profile_ref: SourceRefRequest | None = Field(
        default=None,
        alias="riskProfileRef",
        description="Source-owned Advise risk-profile or policy-evaluation posture reference.",
    )
    risk_profile_status: str | None = Field(
        default=None,
        alias="riskProfileStatus",
        description="Source-owned risk-profile posture such as MISSING, STALE, EXPIRED, REVIEW_DUE, or CURRENT.",
        examples=["STALE"],
    )
    risk_profile_effective_for_as_of_date: bool | None = Field(
        default=None,
        alias="riskProfileEffectiveForAsOfDate",
        description="Whether the source reports the risk profile is effective for the business date.",
    )
    risk_profile_review_due: bool | None = Field(
        default=None,
        alias="riskProfileReviewDue",
        description="Whether the source reports a risk-profile review is due.",
    )
    access_scope: ReviewAccessScopeRequest | None = Field(
        default=None,
        alias="accessScope",
        description="Optional review access scope carried onto created candidates.",
    )
    entitlement_allowed: bool = Field(
        default=True,
        alias="entitlementAllowed",
        description="Whether upstream caller/source entitlement already allowed this evidence for evaluation.",
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_missing_risk_profile_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateMissingRiskProfileSignalCommand:
        return EvaluateMissingRiskProfileSignalCommand(
            as_of_date=self.as_of_date,
            risk_profile_ref=(
                self.risk_profile_ref.to_domain() if self.risk_profile_ref is not None else None
            ),
            risk_profile_status=self.risk_profile_status,
            risk_profile_effective_for_as_of_date=self.risk_profile_effective_for_as_of_date,
            risk_profile_review_due=self.risk_profile_review_due,
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateMissingRiskProfileFromSourceRequest(CamelModel):
    evaluation_id: str = Field(
        ...,
        alias="evaluationId",
        min_length=1,
        description="Lotus Advise policy-evaluation workflow identifier to fetch.",
        examples=["pev_001"],
    )
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Advise risk-profile posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    access_scope: ReviewAccessScopeRequest | None = Field(
        default=None,
        alias="accessScope",
        description="Optional review access scope checked against caller entitlement before source access.",
    )
    duplicate_of_candidate_id: str | None = Field(
        default=None,
        alias="duplicateOfCandidateId",
        description="Existing candidate identity when upstream duplicate detection found a prior candidate.",
        examples=["idea_missing_risk_profile_existing"],
    )

    @field_validator("evaluation_id")
    @classmethod
    def _evaluation_id_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("evaluationId is required")
        return cleaned

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(
        self,
        *,
        correlation_id: str | None,
        trace_id: str | None,
    ) -> EvaluateMissingRiskProfileFromAdviseCommand:
        return EvaluateMissingRiskProfileFromAdviseCommand(
            evaluation_id=self.evaluation_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateMissingRiskProfileSignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_missing_risk_profile_signal(
    request: EvaluateMissingRiskProfileSignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingRiskProfileSignalResponse | JSONResponse:
    source_contracts = _source_ref_contracts(request)
    source_authority = source_authority_from_contracts(source_contracts)
    return evaluate_caller_supplied_signal(
        caller=caller,
        source_authority=source_authority,
        source_contracts=source_contracts,
        requested_access_scope=(
            request.access_scope.to_domain() if request.access_scope is not None else None
        ),
        command_factory=request.to_command,
        evaluator=evaluate_missing_risk_profile_signal_command,
        response_factory=EvaluateMissingRiskProfileSignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_missing_risk_profile_signal_from_source(
    request: Request,
    signal_request: EvaluateMissingRiskProfileFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingRiskProfileSignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_ADVISE.value
    permission_problem = signal_permission_problem_or_none(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=(
            signal_request.access_scope.to_domain()
            if signal_request.access_scope is not None
            else None
        ),
        emit_event=emit_foundation_operation_event,
    )
    if permission_problem is not None:
        return permission_problem

    runtime = _build_advise_policy_evaluation_source_runtime_from_environment()
    if isinstance(runtime, AdvisePolicyEvaluationSourceRuntimeBlocker):
        emit_foundation_operation_event(
            IdeaOperation.SIGNAL_EVALUATION,
            OperationOutcome.BLOCKED,
            source_authority=source_authority,
            error_code=runtime.code,
        )
        return problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Advise source runtime is not configured for missing-risk-profile source evaluation.",
        )

    try:
        result = evaluate_missing_risk_profile_signal_from_advise(
            signal_request.to_command(
                correlation_id=_request_correlation_id(request),
                trace_id=_request_trace_id(request),
            ),
            advise_source=runtime.advise_source,
        )
        emit_signal_evaluation_event(
            result=result,
            source_authority=source_authority,
            emit_event=emit_foundation_operation_event,
        )
        return EvaluateMissingRiskProfileSignalResponse.from_domain(
            result,
            source_authority=source_authority,
        )
    finally:
        close_signal_source_runtime(
            runtime=runtime,
            source_authority=source_authority,
            emit_event=emit_foundation_operation_event,
        )


def _source_ref_contracts(
    request: EvaluateMissingRiskProfileSignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.risk_profile_ref,
            SourceSystem.LOTUS_ADVISE,
            ("lotus-advise:AdvisoryPolicyEvaluationRecord:v1",),
        ),
    )


MISSING_RISK_PROFILE_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-risk-profile/evaluate",
    "operation_id": "evaluateMissingRiskProfileIdeaSignal",
    "summary": "Evaluate a missing risk-profile idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Advise evidence for missing, stale, "
        "expired, or review-due risk-profile posture. The endpoint is a bounded API "
        "foundation; it does not fetch upstream sources, approve risk profiling, approve "
        "suitability, approve policy, publish client communication, certify a typed "
        "risk-profile data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingRiskProfileSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Missing risk-profile signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "missing_risk_profile",
                        "reasonCodes": ["missing_risk_profile", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_missing_risk_profile_8d57adbf52f7f5a7",
                            "family": "missing_risk_profile",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_missing_risk_profile_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "64",
                            "scorePolicyVersion": "missing-risk-profile-review-v1",
                            "sourceSignalIds": ["signal_missing_risk_profile_8d57adbf52f7f5a7"],
                            "sourceRefs": [
                                {
                                    "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
                                    "sourceSystem": "lotus-advise",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "generatedAtUtc": "2026-06-21T10:00:00Z",
                                    "dataQualityStatus": "quality_passed",
                                    "freshness": "current",
                                }
                            ],
                        },
                        "sourceAuthority": "lotus-advise",
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        **signal_problem_responses(),
    },
}


MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-risk-profile/evaluate-from-source",
    "operation_id": "evaluateMissingRiskProfileIdeaSignalFromSource",
    "summary": "Evaluate a missing risk-profile idea signal from Lotus Advise",
    "description": (
        "Fetches source-owned Lotus Advise policy-evaluation workflow posture "
        "through the configured Advise source adapter, then evaluates deterministic "
        "missing risk-profile review posture only when Advise emits explicit "
        "risk-profile diagnostic evidence. The endpoint does not persist candidates, "
        "approve risk profiling, approve suitability, approve policy, approve "
        "proposals, publish client communication, certify live source support, create "
        "Gateway/Workbench support, certify a typed risk-profile data product, or "
        "promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingRiskProfileSignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: MISSING_RISK_PROFILE_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Advise source runtime is not configured for missing-risk-profile source evaluation.",
            description="Advise source runtime configuration is missing or invalid.",
        ),
    },
}


def _request_correlation_id(request: Request) -> str | None:
    correlation_id = getattr(request.state, "correlation_id", None)
    return str(correlation_id) if correlation_id else None


def _request_trace_id(request: Request) -> str | None:
    trace_id = getattr(request.state, "trace_id", None)
    return str(trace_id) if trace_id else None


def register_missing_risk_profile_signal_routes(app: FastAPI) -> None:
    app.post(
        path=MISSING_RISK_PROFILE_EVALUATE_ROUTE["path"],
        operation_id=MISSING_RISK_PROFILE_EVALUATE_ROUTE["operation_id"],
        summary=MISSING_RISK_PROFILE_EVALUATE_ROUTE["summary"],
        description=MISSING_RISK_PROFILE_EVALUATE_ROUTE["description"],
        status_code=MISSING_RISK_PROFILE_EVALUATE_ROUTE["status_code"],
        response_model=MISSING_RISK_PROFILE_EVALUATE_ROUTE["response_model"],
        tags=MISSING_RISK_PROFILE_EVALUATE_ROUTE["tags"],
        responses=MISSING_RISK_PROFILE_EVALUATE_ROUTE["responses"],
    )(evaluate_missing_risk_profile_signal)
    app.post(
        path=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=MISSING_RISK_PROFILE_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_missing_risk_profile_signal_from_source)
