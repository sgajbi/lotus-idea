from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

from fastapi import FastAPI, Header, Path, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.caller_headers import caller_context_from_headers
from app.api.repository_state import get_idea_repository
from app.application.ai_governance import (
    AIExplanationEvaluationDecision,
    AIExplanationReadinessSnapshot,
    EvaluateAIExplanationToRepositoryCommand,
    build_ai_explanation_readiness_snapshot,
    evaluate_ai_explanation_to_repository,
)
from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIExplanationPosture,
    AIExplanationResult,
    AIOutputClaim,
    AIProposedAction,
    AIProposedActionType,
    AIVerifierOutcome,
    AIWorkflowOutput,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    InvalidAIExplanationRequest,
    InvalidAIWorkflowOutput,
    RedactedIdeaEvidence,
    RedactedSourceRef,
    SourceSystem,
)
from app.errors import ProblemDetails, problem_response
from app.observability import (
    IdeaOperation,
    OperationEvent,
    OperationOutcome,
    OperationSupportability,
    emit_foundation_operation_event,
    emit_operation_event,
)
from app.security.caller_context import CallerContext, PermissionDeniedError


class RouteMetadata(TypedDict):
    path: str
    operation_id: str
    summary: str
    description: str
    status_code: int
    response_model: type[BaseModel]
    tags: list[str | Enum]
    responses: dict[int | str, dict[str, Any]]


_AI_EXPLANATION_CAPABILITY = "idea.ai-explanation.evaluate"
_AI_EXPLANATION_READINESS_CAPABILITY = "idea.ai-explanation.readiness.read"


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class AIWorkflowPackRequest(CamelModel):
    workflow_pack_id: str = Field(..., alias="workflowPackId")
    workflow_pack_version: str = Field(..., alias="workflowPackVersion")
    purpose: AIWorkflowPurpose
    evaluation_ref: str = Field(..., alias="evaluationRef")

    @field_validator("workflow_pack_id", "workflow_pack_version", "evaluation_ref")
    @classmethod
    def _workflow_pack_field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("workflow pack fields cannot be blank")
        return value

    def to_domain(self) -> AIWorkflowPackRef:
        return AIWorkflowPackRef(
            workflow_pack_id=self.workflow_pack_id,
            workflow_pack_version=self.workflow_pack_version,
            purpose=self.purpose,
            evaluation_ref=self.evaluation_ref,
        )


class AIOutputClaimRequest(CamelModel):
    claim_id: str = Field(..., alias="claimId")
    claim_text: str = Field(..., alias="claimText")
    source_product_ids: tuple[str, ...] = Field(..., alias="sourceProductIds")

    @field_validator("claim_id", "claim_text")
    @classmethod
    def _claim_field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("claim fields cannot be blank")
        return value

    @field_validator("source_product_ids")
    @classmethod
    def _source_product_ids_must_not_be_empty_or_blank(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not value:
            raise ValueError("sourceProductIds is required")
        if any(not product_id.strip() for product_id in value):
            raise ValueError("sourceProductIds cannot contain blank values")
        return tuple(value)

    def to_domain(self) -> AIOutputClaim:
        return AIOutputClaim(
            claim_id=self.claim_id,
            claim_text=self.claim_text,
            source_product_ids=self.source_product_ids,
        )


class AIProposedActionRequest(CamelModel):
    action_type: AIProposedActionType = Field(..., alias="actionType")
    action_label: str = Field(..., alias="actionLabel")

    @field_validator("action_label")
    @classmethod
    def _action_label_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("actionLabel is required")
        return value

    def to_domain(self) -> AIProposedAction:
        return AIProposedAction(action_type=self.action_type, action_label=self.action_label)


class AIWorkflowOutputRequest(CamelModel):
    output_id: str = Field(..., alias="outputId")
    explanation_text: str = Field(..., alias="explanationText")
    claims: tuple[AIOutputClaimRequest, ...]
    proposed_actions: tuple[AIProposedActionRequest, ...] = Field(..., alias="proposedActions")
    verifier_ran_at_utc: datetime = Field(..., alias="verifierRanAtUtc")

    @field_validator("output_id", "explanation_text")
    @classmethod
    def _output_field_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("output fields cannot be blank")
        return value

    @field_validator("claims", "proposed_actions")
    @classmethod
    def _non_empty_tuple(cls, value: tuple[Any, ...]) -> tuple[Any, ...]:
        if not value:
            raise ValueError("AI output lists cannot be empty")
        return tuple(value)

    @field_validator("verifier_ran_at_utc")
    @classmethod
    def _verifier_time_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verifierRanAtUtc must be timezone-aware")
        return value

    def to_domain(
        self,
        *,
        request_id: str,
        workflow_pack: AIWorkflowPackRequest,
    ) -> AIWorkflowOutput:
        return AIWorkflowOutput(
            output_id=self.output_id,
            request_id=request_id,
            workflow_pack_id=workflow_pack.workflow_pack_id,
            workflow_pack_version=workflow_pack.workflow_pack_version,
            explanation_text=self.explanation_text,
            claims=tuple(claim.to_domain() for claim in self.claims),
            proposed_actions=tuple(action.to_domain() for action in self.proposed_actions),
            verifier_ran_at_utc=self.verifier_ran_at_utc,
        )


class AIExplanationEvaluationRequest(CamelModel):
    request_id: str = Field(..., alias="requestId")
    workflow_pack: AIWorkflowPackRequest = Field(..., alias="workflowPack")
    approved_metadata: dict[str, str] = Field(default_factory=dict, alias="approvedMetadata")
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    fallback_reason: AIFallbackReason = Field(
        default=AIFallbackReason.AI_UNAVAILABLE,
        alias="fallbackReason",
    )
    workflow_output: AIWorkflowOutputRequest | None = Field(default=None, alias="workflowOutput")

    @field_validator("request_id")
    @classmethod
    def _request_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requestId is required")
        return value

    @field_validator("requested_at_utc")
    @classmethod
    def _requested_at_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("requestedAtUtc must be timezone-aware")
        return value

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
    ) -> EvaluateAIExplanationToRepositoryCommand:
        return EvaluateAIExplanationToRepositoryCommand(
            candidate_id=candidate_id,
            explanation=AIExplanationCommand(
                request_id=self.request_id,
                actor_subject=caller.subject,
                workflow_pack=self.workflow_pack.to_domain(),
                approved_metadata=self.approved_metadata,
                requested_at_utc=self.requested_at_utc,
            ),
            fallback_reason=self.fallback_reason,
            workflow_output=(
                self.workflow_output.to_domain(
                    request_id=self.request_id,
                    workflow_pack=self.workflow_pack,
                )
                if self.workflow_output is not None
                else None
            ),
        )


class AIWorkflowPackResponse(CamelModel):
    workflow_pack_id: str = Field(..., alias="workflowPackId")
    workflow_pack_version: str = Field(..., alias="workflowPackVersion")
    purpose: AIWorkflowPurpose
    evaluation_ref: str = Field(..., alias="evaluationRef")
    source_authority: SourceSystem = Field(SourceSystem.LOTUS_AI, alias="sourceAuthority")

    @classmethod
    def from_domain(cls, workflow_pack: AIWorkflowPackRef) -> "AIWorkflowPackResponse":
        return cls(
            workflowPackId=workflow_pack.workflow_pack_id,
            workflowPackVersion=workflow_pack.workflow_pack_version,
            purpose=workflow_pack.purpose,
            evaluationRef=workflow_pack.evaluation_ref,
            sourceAuthority=SourceSystem.LOTUS_AI,
        )


class RedactedSourceRefResponse(CamelModel):
    product_id: str = Field(..., alias="productId")
    source_system: SourceSystem = Field(..., alias="sourceSystem")
    product_version: str = Field(..., alias="productVersion")
    as_of_date: str = Field(..., alias="asOfDate")
    freshness: str
    data_quality_status: str = Field(..., alias="dataQualityStatus")

    @classmethod
    def from_domain(cls, source_ref: RedactedSourceRef) -> "RedactedSourceRefResponse":
        return cls(
            productId=source_ref.product_id,
            sourceSystem=source_ref.source_system,
            productVersion=source_ref.product_version,
            asOfDate=source_ref.as_of_date.isoformat(),
            freshness=source_ref.freshness.value,
            dataQualityStatus=source_ref.data_quality_status,
        )


class RedactedIdeaEvidenceResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    evidence_content_hash: str = Field(..., alias="evidenceContentHash")
    supportability: str
    source_refs: tuple[RedactedSourceRefResponse, ...] = Field(..., alias="sourceRefs")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    unsupported_reasons: tuple[str, ...] = Field(..., alias="unsupportedReasons")
    score_policy_version: str | None = Field(default=None, alias="scorePolicyVersion")
    score: str | None = None
    source_signal_count: int = Field(..., alias="sourceSignalCount")

    @classmethod
    def from_domain(cls, evidence: RedactedIdeaEvidence) -> "RedactedIdeaEvidenceResponse":
        return cls(
            candidateId=evidence.candidate_id,
            family=evidence.family.value,
            lifecycleStatus=evidence.lifecycle_status.value,
            reviewPosture=evidence.review_posture.value,
            evidencePacketId=evidence.evidence_packet_id,
            evidenceContentHash=evidence.evidence_content_hash,
            supportability=evidence.supportability.value,
            sourceRefs=tuple(
                RedactedSourceRefResponse.from_domain(source_ref)
                for source_ref in evidence.source_refs
            ),
            reasonCodes=tuple(reason.value for reason in evidence.reason_codes),
            unsupportedReasons=tuple(reason.value for reason in evidence.unsupported_reasons),
            scorePolicyVersion=evidence.score_policy_version,
            score=str(evidence.score) if evidence.score is not None else None,
            sourceSignalCount=evidence.source_signal_count,
        )


class AIWorkflowOutputSummaryResponse(CamelModel):
    output_id: str = Field(..., alias="outputId")
    claim_ids: tuple[str, ...] = Field(..., alias="claimIds")
    proposed_action_types: tuple[AIProposedActionType, ...] = Field(
        ...,
        alias="proposedActionTypes",
    )
    verifier_ran_at_utc: datetime = Field(..., alias="verifierRanAtUtc")

    @classmethod
    def from_domain(cls, output: AIWorkflowOutput) -> "AIWorkflowOutputSummaryResponse":
        return cls(
            outputId=output.output_id,
            claimIds=tuple(claim.claim_id for claim in output.claims),
            proposedActionTypes=tuple(action.action_type for action in output.proposed_actions),
            verifierRanAtUtc=output.verifier_ran_at_utc,
        )


class AIExplanationEvaluationResponse(CamelModel):
    request_id: str = Field(..., alias="requestId")
    candidate_id: str = Field(..., alias="candidateId")
    workflow_pack: AIWorkflowPackResponse = Field(..., alias="workflowPack")
    posture: AIExplanationPosture
    verifier_outcome: AIVerifierOutcome = Field(..., alias="verifierOutcome")
    explanation_text: str = Field(..., alias="explanationText")
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")
    fallback_used: bool = Field(..., alias="fallbackUsed")
    fallback_reason: AIFallbackReason | None = Field(default=None, alias="fallbackReason")
    grants_downstream_authority: bool = Field(False, alias="grantsDownstreamAuthority")
    audit_event_type: str = Field(..., alias="auditEventType")
    redacted_evidence: RedactedIdeaEvidenceResponse = Field(..., alias="redactedEvidence")
    verified_output: AIWorkflowOutputSummaryResponse | None = Field(
        default=None,
        alias="verifiedOutput",
    )
    approved_metadata_keys: tuple[str, ...] = Field(..., alias="approvedMetadataKeys")
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    lotus_ai_runtime_executed: bool = Field(False, alias="lotusAiRuntimeExecuted")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        result: AIExplanationResult,
    ) -> "AIExplanationEvaluationResponse":
        return cls(
            requestId=result.request.request_id,
            candidateId=result.request.redacted_evidence.candidate_id,
            workflowPack=AIWorkflowPackResponse.from_domain(result.request.workflow_pack),
            posture=result.posture,
            verifierOutcome=result.verifier_outcome,
            explanationText=result.explanation_text,
            reasonCodes=tuple(reason.value for reason in result.reason_codes),
            fallbackUsed=result.fallback_used,
            fallbackReason=result.fallback_reason,
            grantsDownstreamAuthority=result.grants_downstream_authority,
            auditEventType=result.audit_event.event_type,
            redactedEvidence=RedactedIdeaEvidenceResponse.from_domain(
                result.request.redacted_evidence
            ),
            verifiedOutput=(
                AIWorkflowOutputSummaryResponse.from_domain(result.output)
                if result.output is not None
                else None
            ),
            approvedMetadataKeys=tuple(sorted(result.request.approved_metadata.keys())),
            durableStorageBacked=False,
            lotusAiRuntimeExecuted=False,
            supportedFeaturePromoted=False,
        )


class AIExplanationReadinessResponse(CamelModel):
    repository: str
    source_authority: str = Field(..., alias="sourceAuthority")
    workflow_authority: str = Field(..., alias="workflowAuthority")
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    deterministic_fallback_available: bool = Field(..., alias="deterministicFallbackAvailable")
    verifier_available: bool = Field(..., alias="verifierAvailable")
    redacted_evidence_envelope_available: bool = Field(
        ...,
        alias="redactedEvidenceEnvelopeAvailable",
    )
    unsupported_claim_blocking_available: bool = Field(
        ...,
        alias="unsupportedClaimBlockingAvailable",
    )
    forbidden_action_blocking_available: bool = Field(
        ...,
        alias="forbiddenActionBlockingAvailable",
    )
    durable_ai_lineage_store_backed: bool = Field(..., alias="durableAiLineageStoreBacked")
    lotus_ai_runtime_executed: bool = Field(..., alias="lotusAiRuntimeExecuted")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: AIExplanationReadinessSnapshot,
    ) -> "AIExplanationReadinessResponse":
        return cls(
            repository=snapshot.repository,
            sourceAuthority=snapshot.source_authority,
            workflowAuthority=snapshot.workflow_authority,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            deterministicFallbackAvailable=snapshot.deterministic_fallback_available,
            verifierAvailable=snapshot.verifier_available,
            redactedEvidenceEnvelopeAvailable=snapshot.redacted_evidence_envelope_available,
            unsupportedClaimBlockingAvailable=snapshot.unsupported_claim_blocking_available,
            forbiddenActionBlockingAvailable=snapshot.forbidden_action_blocking_available,
            durableAiLineageStoreBacked=snapshot.durable_ai_lineage_store_backed,
            lotusAiRuntimeExecuted=snapshot.lotus_ai_runtime_executed,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


async def get_ai_explanation_readiness(
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> AIExplanationReadinessResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_ai_explanation_readiness_caller(caller)
    except PermissionDeniedError:
        _emit_ai_explanation_readiness_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to read idea AI explanation readiness.",
        )

    snapshot = build_ai_explanation_readiness_snapshot()
    _emit_ai_explanation_readiness_operation_event(OperationOutcome.BLOCKED)
    return AIExplanationReadinessResponse.from_domain(snapshot)


async def evaluate_ai_explanation(
    request: AIExplanationEvaluationRequest,
    candidate_id: str = Path(..., alias="candidateId"),
    x_caller_subject: str | None = Header(default=None, alias="X-Caller-Subject"),
    x_caller_roles: str | None = Header(default=None, alias="X-Caller-Roles"),
    x_caller_capabilities: str | None = Header(default=None, alias="X-Caller-Capabilities"),
) -> AIExplanationEvaluationResponse | JSONResponse:
    caller = caller_context_from_headers(
        subject=x_caller_subject,
        roles=x_caller_roles,
        capabilities=x_caller_capabilities,
    )
    try:
        _require_ai_explanation_caller(caller)
        result = evaluate_ai_explanation_to_repository(
            request.to_command(candidate_id=candidate_id, caller=caller),
            repository=get_idea_repository(),
        )
    except PermissionDeniedError:
        _emit_ai_explanation_operation_event(
            OperationOutcome.PERMISSION_DENIED,
            "permission_denied",
        )
        return problem_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code="permission_denied",
            title="Permission denied",
            detail="The caller is not permitted to evaluate idea AI explanations.",
        )
    except InvalidAIWorkflowOutput:
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_ai_output",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_ai_output",
            title="Invalid AI output",
            detail="The AI workflow output does not match the governed explanation request.",
        )
    except InvalidAIExplanationRequest as exc:
        return _invalid_ai_explanation_request_response(exc)
    except ValueError:
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_REQUEST,
            "invalid_request",
        )
        return problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="invalid_request",
            title="Invalid request",
            detail="Correct the AI explanation evaluation request and retry.",
        )

    if result.decision is AIExplanationEvaluationDecision.NOT_FOUND:
        _emit_ai_explanation_operation_event(
            OperationOutcome.NOT_FOUND,
            "candidate_not_found",
        )
        return problem_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code="candidate_not_found",
            title="Candidate not found",
            detail="The idea candidate was not found.",
        )
    assert result.explanation_result is not None
    _emit_ai_explanation_operation_event(
        _operation_outcome_from_ai_result(result.explanation_result)
    )
    return AIExplanationEvaluationResponse.from_domain(result.explanation_result)


def _require_ai_explanation_caller(caller: CallerContext) -> None:
    if not caller.has_capability(_AI_EXPLANATION_CAPABILITY):
        raise PermissionDeniedError(_AI_EXPLANATION_CAPABILITY)


def _require_ai_explanation_readiness_caller(caller: CallerContext) -> None:
    if not caller.has_role("operator") or not caller.has_capability(
        _AI_EXPLANATION_READINESS_CAPABILITY
    ):
        raise PermissionDeniedError(_AI_EXPLANATION_READINESS_CAPABILITY)


def _invalid_ai_explanation_request_response(exc: InvalidAIExplanationRequest) -> JSONResponse:
    message = str(exc)
    if message.startswith("rationale drafting requires"):
        _emit_ai_explanation_operation_event(
            OperationOutcome.INVALID_STATE,
            "ai_explanation_conflict",
        )
        return problem_response(
            status_code=status.HTTP_409_CONFLICT,
            code="ai_explanation_conflict",
            title="AI explanation conflict",
            detail="The requested AI explanation purpose is not valid for the current candidate state.",
        )
    _emit_ai_explanation_operation_event(
        OperationOutcome.INVALID_REQUEST,
        "invalid_request",
    )
    return problem_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="invalid_request",
        title="Invalid request",
        detail="Correct the AI explanation evaluation request and retry.",
    )


def _operation_outcome_from_ai_result(result: AIExplanationResult) -> OperationOutcome:
    if result.posture is AIExplanationPosture.READY_FOR_ADVISOR_REVIEW:
        return OperationOutcome.ACCEPTED
    if result.posture is AIExplanationPosture.FALLBACK_USED:
        return OperationOutcome.FALLBACK
    return OperationOutcome.BLOCKED


def _emit_ai_explanation_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
) -> None:
    emit_foundation_operation_event(
        IdeaOperation.AI_EXPLANATION,
        outcome,
        source_authority="lotus-idea",
        error_code=error_code,
    )


def _emit_ai_explanation_readiness_operation_event(
    outcome: OperationOutcome,
    error_code: str | None = None,
) -> None:
    emit_operation_event(
        OperationEvent(
            operation=IdeaOperation.AI_EXPLANATION_READINESS_READ,
            outcome=outcome,
            source_authority="lotus-ai",
            supportability_status=OperationSupportability.NOT_CERTIFIED,
            durable_storage_backed=False,
            supported_feature_promoted=False,
            error_code=error_code,
        )
    )


AI_EXPLANATION_READINESS_ROUTE: RouteMetadata = {
    "path": "/api/v1/ai-explanations/readiness",
    "operation_id": "getIdeaAIExplanationReadiness",
    "summary": "Get AI explanation readiness",
    "description": (
        "Returns source-safe operator readiness for the internal AI explanation foundation. "
        "The endpoint reports guardrail availability and certification blockers only; it does "
        "not invoke lotus-ai runtime workflows, expose prompts or provider payloads, disclose "
        "candidate evidence, grant downstream authority, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AIExplanationReadinessResponse,
    "tags": ["Operations", "Idea AI Governance"],
    "responses": {
        200: {
            "description": "AI explanation readiness posture returned.",
            "content": {
                "application/json": {
                    "example": {
                        "repository": "lotus-idea",
                        "sourceAuthority": "lotus-idea",
                        "workflowAuthority": "lotus-ai",
                        "readinessStatus": "blocked",
                        "supportabilityStatus": "not_certified",
                        "certificationReady": False,
                        "deterministicFallbackAvailable": True,
                        "verifierAvailable": True,
                        "redactedEvidenceEnvelopeAvailable": True,
                        "unsupportedClaimBlockingAvailable": True,
                        "forbiddenActionBlockingAvailable": True,
                        "durableAiLineageStoreBacked": False,
                        "lotusAiRuntimeExecuted": False,
                        "certificationBlockers": [
                            "lotus_ai_runtime_execution_missing",
                            "durable_ai_lineage_store_missing",
                            "workflow_pack_runtime_contract_not_certified",
                            "model_risk_operations_dashboard_missing",
                            "runtime_trust_telemetry_missing",
                            "workbench_product_proof_missing",
                        ],
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        403: {
            "model": ProblemDetails,
            "description": "Caller lacks AI explanation readiness permission.",
        },
    },
}


AI_EXPLANATION_ROUTE: RouteMetadata = {
    "path": "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate",
    "operation_id": "evaluateIdeaAIExplanation",
    "summary": "Evaluate an idea AI explanation",
    "description": (
        "Evaluates an internal AI explanation workflow result or deterministic fallback "
        "against a persisted idea candidate. The route applies redaction, source-product "
        "claim verification, forbidden-action blocking, and bounded operation telemetry. "
        "It does not call an AI provider, execute lotus-ai runtime workflows, persist "
        "durable audit records, grant downstream authority, or promote a supported feature."
    ),
    "status_code": status.HTTP_200_OK,
    "response_model": AIExplanationEvaluationResponse,
    "tags": ["Idea AI Governance"],
    "responses": {
        200: {
            "description": "AI explanation evaluation returned through the internal foundation.",
            "content": {
                "application/json": {
                    "example": {
                        "requestId": "ai-explanation-001",
                        "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                        "workflowPack": {
                            "workflowPackId": "lotus-ai:idea-explanation:v1",
                            "workflowPackVersion": "v1",
                            "purpose": "advisor_rationale_draft",
                            "evaluationRef": "lotus-ai:governed-verifier:v1",
                            "sourceAuthority": "lotus-ai",
                        },
                        "posture": "ready_for_advisor_review",
                        "verifierOutcome": "passed",
                        "explanationText": (
                            "Candidate has elevated idle cash and source-ready evidence "
                            "for advisor review."
                        ),
                        "reasonCodes": ["ai_verifier_passed"],
                        "fallbackUsed": False,
                        "fallbackReason": None,
                        "grantsDownstreamAuthority": False,
                        "auditEventType": "idea.ai_explanation.evaluated",
                        "redactedEvidence": {
                            "candidateId": "idea_high_cash_8d57adbf52f7f5a7",
                            "family": "high_cash",
                            "lifecycleStatus": "ready_for_review",
                            "reviewPosture": "advisor_review_required",
                            "evidencePacketId": "iep_high_cash_8d57adbf52f7f5a7",
                            "evidenceContentHash": "sha256:evidence-lineage",
                            "supportability": "ready",
                            "sourceRefs": [
                                {
                                    "productId": "lotus-core:PortfolioStateSnapshot:v1",
                                    "sourceSystem": "lotus-core",
                                    "productVersion": "v1",
                                    "asOfDate": "2026-06-21",
                                    "freshness": "current",
                                    "dataQualityStatus": "complete",
                                }
                            ],
                            "reasonCodes": ["high_cash_ratio", "review_required"],
                            "unsupportedReasons": [],
                            "scorePolicyVersion": "idle-liquidity-v1",
                            "score": "82",
                            "sourceSignalCount": 1,
                        },
                        "verifiedOutput": {
                            "outputId": "ai-output-001",
                            "claimIds": ["claim-001"],
                            "proposedActionTypes": ["advisor_review"],
                            "verifierRanAtUtc": "2026-06-21T10:12:00Z",
                        },
                        "approvedMetadataKeys": ["channel"],
                        "durableStorageBacked": False,
                        "lotusAiRuntimeExecuted": False,
                        "supportedFeaturePromoted": False,
                    }
                }
            },
        },
        400: {"model": ProblemDetails, "description": "Request validation failed."},
        403: {"model": ProblemDetails, "description": "Caller lacks AI explanation permission."},
        404: {"model": ProblemDetails, "description": "Candidate was not found."},
        409: {
            "model": ProblemDetails,
            "description": "Requested AI explanation purpose is invalid for candidate state.",
        },
    },
}


def register_ai_governance_routes(app: FastAPI) -> None:
    app.get(
        path=AI_EXPLANATION_READINESS_ROUTE["path"],
        operation_id=AI_EXPLANATION_READINESS_ROUTE["operation_id"],
        summary=AI_EXPLANATION_READINESS_ROUTE["summary"],
        description=AI_EXPLANATION_READINESS_ROUTE["description"],
        status_code=AI_EXPLANATION_READINESS_ROUTE["status_code"],
        response_model=AI_EXPLANATION_READINESS_ROUTE["response_model"],
        tags=AI_EXPLANATION_READINESS_ROUTE["tags"],
        responses=AI_EXPLANATION_READINESS_ROUTE["responses"],
    )(get_ai_explanation_readiness)
    app.post(
        path=AI_EXPLANATION_ROUTE["path"],
        operation_id=AI_EXPLANATION_ROUTE["operation_id"],
        summary=AI_EXPLANATION_ROUTE["summary"],
        description=AI_EXPLANATION_ROUTE["description"],
        status_code=AI_EXPLANATION_ROUTE["status_code"],
        response_model=AI_EXPLANATION_ROUTE["response_model"],
        tags=AI_EXPLANATION_ROUTE["tags"],
        responses=AI_EXPLANATION_ROUTE["responses"],
    )(evaluate_ai_explanation)
