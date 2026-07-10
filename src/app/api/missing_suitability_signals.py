from __future__ import annotations

from datetime import date, datetime
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.caller_headers import CallerContextHeaders
from app.api.problem_details import service_unavailable_metadata
from app.api.runtime_dependencies import (
    AdvisePolicyEvaluationSourceRuntime,
    AdvisePolicyEvaluationSourceRuntimeBlocker,
)
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
    evaluate_source_signal,
    signal_problem_responses,
    source_authority_from_contracts,
)
from app.application.missing_suitability_signal import (
    EvaluateMissingSuitabilityContextFromAdviseCommand,
    EvaluateMissingSuitabilityContextSignalCommand,
    evaluate_missing_suitability_context_signal_from_advise,
    evaluate_missing_suitability_context_signal_command,
)
from app.domain import SourceSystem
from app.observability import emit_foundation_operation_event


def _is_advise_suitability_runtime_blocked(runtime: object) -> bool:
    return isinstance(runtime, AdvisePolicyEvaluationSourceRuntimeBlocker)


class EvaluateMissingSuitabilitySignalRequest(CamelModel):
    as_of_date: date = Field(
        ...,
        alias="asOfDate",
        description="Business date for the source-owned Advise policy-evaluation posture.",
        examples=["2026-06-21"],
    )
    evaluated_at_utc: datetime = Field(
        ...,
        alias="evaluatedAtUtc",
        description="UTC timestamp for deterministic evaluation.",
        examples=["2026-06-21T10:00:00Z"],
    )
    policy_ref: SourceRefRequest | None = Field(
        default=None,
        alias="policyRef",
        description="Source-owned Advise policy-evaluation posture reference.",
    )
    evaluation_status: str | None = Field(
        default=None,
        alias="evaluationStatus",
        description="Source-owned policy-evaluation status such as PENDING_REVIEW, BLOCKED, or READY.",
        examples=["PENDING_REVIEW"],
    )
    open_requirement_count: int | None = Field(
        default=None,
        alias="openRequirementCount",
        ge=0,
        description="Count of source-reported open suitability, disclosure, consent, or policy requirements.",
    )
    blocked_requirement_count: int | None = Field(
        default=None,
        alias="blockedRequirementCount",
        ge=0,
        description="Count of source-reported blocked policy requirements.",
    )
    sign_off_status: str | None = Field(
        default=None,
        alias="signOffStatus",
        description="Source-owned advisor, compliance, or client sign-off posture.",
        examples=["PENDING_REVIEW"],
    )
    sign_off_blocker_count: int | None = Field(
        default=None,
        alias="signOffBlockerCount",
        ge=0,
        description="Count of source-reported sign-off blockers.",
    )
    client_ready_publication: str | None = Field(
        default=None,
        alias="clientReadyPublication",
        description="Source-owned client-publication posture. Must remain BLOCKED for review candidates.",
        examples=["BLOCKED"],
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
        examples=["idea_missing_suitability_context_existing"],
    )

    @field_validator("evaluated_at_utc")
    @classmethod
    def _evaluated_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="evaluatedAtUtc")

    def to_command(self) -> EvaluateMissingSuitabilityContextSignalCommand:
        return EvaluateMissingSuitabilityContextSignalCommand(
            as_of_date=self.as_of_date,
            evaluation_status=self.evaluation_status,
            open_requirement_count=self.open_requirement_count,
            blocked_requirement_count=self.blocked_requirement_count,
            sign_off_status=self.sign_off_status,
            sign_off_blocker_count=self.sign_off_blocker_count,
            client_ready_publication=self.client_ready_publication,
            policy_ref=self.policy_ref.to_domain() if self.policy_ref is not None else None,
            evaluated_at_utc=self.evaluated_at_utc,
            entitlement_allowed=self.entitlement_allowed,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
        )


class EvaluateMissingSuitabilityFromSourceRequest(CamelModel):
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
        description="Business date for the source-owned Advise policy-evaluation posture.",
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
        examples=["idea_missing_suitability_context_existing"],
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
    ) -> EvaluateMissingSuitabilityContextFromAdviseCommand:
        return EvaluateMissingSuitabilityContextFromAdviseCommand(
            evaluation_id=self.evaluation_id,
            as_of_date=self.as_of_date,
            evaluated_at_utc=self.evaluated_at_utc,
            access_scope=(self.access_scope.to_domain() if self.access_scope is not None else None),
            duplicate_of_candidate_id=self.duplicate_of_candidate_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )


class EvaluateMissingSuitabilitySignalResponse(SignalEvaluationResponse):
    pass


async def evaluate_missing_suitability_signal(
    request: EvaluateMissingSuitabilitySignalRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingSuitabilitySignalResponse | JSONResponse:
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
        evaluator=evaluate_missing_suitability_context_signal_command,
        response_factory=EvaluateMissingSuitabilitySignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


async def evaluate_missing_suitability_signal_from_source(
    request: Request,
    signal_request: EvaluateMissingSuitabilityFromSourceRequest,
    caller: CallerContextHeaders,
) -> EvaluateMissingSuitabilitySignalResponse | JSONResponse:
    source_authority = SourceSystem.LOTUS_ADVISE.value
    return evaluate_source_signal(
        caller=caller,
        source_authority=source_authority,
        requested_access_scope=(
            signal_request.access_scope.to_domain()
            if signal_request.access_scope is not None
            else None
        ),
        runtime_factory=_build_advise_policy_evaluation_source_runtime_from_environment,
        is_runtime_blocked=_is_advise_suitability_runtime_blocked,
        blocked_detail="Advise source runtime is not configured for missing-suitability source evaluation.",
        command_factory=lambda runtime, _tenant_id: signal_request.to_command(
            correlation_id=_request_correlation_id(request),
            trace_id=_request_trace_id(request),
        ),
        evaluator=lambda command, runtime: evaluate_missing_suitability_context_signal_from_advise(
            command,
            advise_source=cast(AdvisePolicyEvaluationSourceRuntime, runtime).advise_source,
        ),
        response_factory=EvaluateMissingSuitabilitySignalResponse.from_domain,
        emit_event=emit_foundation_operation_event,
    )


def _source_ref_contracts(
    request: EvaluateMissingSuitabilitySignalRequest,
) -> tuple[SignalSourceRefContract, ...]:
    return (
        SignalSourceRefContract(
            request.policy_ref,
            SourceSystem.LOTUS_ADVISE,
            ("lotus-advise:AdvisoryPolicyEvaluationRecord:v1",),
        ),
    )


MISSING_SUITABILITY_EVALUATE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-suitability/evaluate",
    "operation_id": "evaluateMissingSuitabilityIdeaSignal",
    "summary": "Evaluate a missing suitability-context idea signal",
    "description": (
        "Evaluates caller-supplied, source-owned Advise policy-evaluation evidence "
        "for open suitability, disclosure, consent, approval, or sign-off context. "
        "The endpoint is a bounded API foundation; it does not fetch upstream sources, "
        "approve suitability, approve policy, approve proposals, publish client "
        "communication, certify a data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingSuitabilitySignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: {
            "description": "Missing suitability-context signal evaluation completed with candidate, blocked, suppressed, or not-eligible posture.",
            "content": {
                "application/json": {
                    "example": {
                        "outcome": "candidate_created",
                        "family": "missing_suitability_context",
                        "reasonCodes": ["suitability_context_missing", "review_required"],
                        "unsupportedReasons": [],
                        "candidate": {
                            "candidateId": "idea_missing_suitability_context_8d57adbf52f7f5a7",
                            "family": "missing_suitability_context",
                            "lifecycleStatus": "generated",
                            "reviewPosture": "compliance_review_required",
                            "evidencePacketId": "iep_missing_suitability_context_8d57adbf52f7f5a7",
                            "supportability": "ready",
                            "score": "68",
                            "scorePolicyVersion": "missing-suitability-context-review-v1",
                            "sourceSignalIds": [
                                "signal_missing_suitability_context_8d57adbf52f7f5a7"
                            ],
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


MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-signals/missing-suitability/evaluate-from-source",
    "operation_id": "evaluateMissingSuitabilityIdeaSignalFromSource",
    "summary": "Evaluate a missing suitability-context idea signal from Lotus Advise",
    "description": (
        "Fetches source-owned Lotus Advise policy-evaluation workflow posture "
        "through the configured Advise source adapter, then evaluates deterministic "
        "missing suitability-context review posture. The endpoint does not persist "
        "candidates, approve suitability, approve policy, approve proposals, publish "
        "client communication, certify live source support, create Gateway/Workbench "
        "support, certify a data product, or promote a supported business feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": EvaluateMissingSuitabilitySignalResponse,
    "tags": ["Idea Signals"],
    "responses": {
        200: MISSING_SUITABILITY_EVALUATE_ROUTE["responses"][200],
        **signal_problem_responses(),
        **service_unavailable_metadata(
            code="source_runtime_not_configured",
            title="Source runtime not configured",
            detail="Advise source runtime is not configured for missing-suitability source evaluation.",
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


def register_missing_suitability_signal_routes(app: FastAPI) -> None:
    app.post(
        path=MISSING_SUITABILITY_EVALUATE_ROUTE["path"],
        operation_id=MISSING_SUITABILITY_EVALUATE_ROUTE["operation_id"],
        summary=MISSING_SUITABILITY_EVALUATE_ROUTE["summary"],
        description=MISSING_SUITABILITY_EVALUATE_ROUTE["description"],
        status_code=MISSING_SUITABILITY_EVALUATE_ROUTE["status_code"],
        response_model=MISSING_SUITABILITY_EVALUATE_ROUTE["response_model"],
        tags=MISSING_SUITABILITY_EVALUATE_ROUTE["tags"],
        responses=MISSING_SUITABILITY_EVALUATE_ROUTE["responses"],
    )(evaluate_missing_suitability_signal)
    app.post(
        path=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["path"],
        operation_id=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["operation_id"],
        summary=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["summary"],
        description=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["description"],
        status_code=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["status_code"],
        response_model=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["response_model"],
        tags=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["tags"],
        responses=MISSING_SUITABILITY_EVALUATE_FROM_SOURCE_ROUTE["responses"],
    )(evaluate_missing_suitability_signal_from_source)
