from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.api.base_model import CamelModel
from app.api.temporal_validation import require_timezone_aware
from app.domain.ai_action_policy import AI_ACTION_POLICY_VERSION
from app.domain.ai_execution_provenance import (
    AI_EXECUTION_PROVENANCE_POLICY_VERSION,
    AIExecutionProvenancePosture,
    AIWorkflowOutputTrustPolicy,
)
from app.domain.ai_explanation import AI_CLAIM_GROUNDING_POLICY_VERSION
from app.domain.ai_metadata_policy import AI_METADATA_ENVELOPE_VERSION
from app.application.ai_governance import (
    AIExplanationReadinessSnapshot,
    EvaluateAIExplanationToRepositoryCommand,
)
from app.domain import (
    AIExplanationCommand,
    AIExplanationPosture,
    AIExplanationResult,
    AIFallbackReason,
    AIOutputClaim,
    AIProposedAction,
    AIProposedActionType,
    AIVerifierOutcome,
    AIWorkflowOutput,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    RedactedIdeaEvidence,
    RedactedSourceRef,
    SourceSystem,
)
from app.security.caller_context import CallerContext
from app.integration.lotus_ai_attestation_contract import LotusAIProducerAttestation
from app.integration.lotus_ai_idea_explanation_output import LotusAIExecutionOutputEvidence
from app.integration.lotus_ai_provider_retention_contract import (
    LotusAIProviderRetentionConfirmation,
)


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
        if len(set(value)) != len(value):
            raise ValueError("sourceProductIds must be unique")
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

    @field_validator("claims")
    @classmethod
    def _claim_ids_must_be_unique(
        cls,
        value: tuple[AIOutputClaimRequest, ...],
    ) -> tuple[AIOutputClaimRequest, ...]:
        if len({claim.claim_id for claim in value}) != len(value):
            raise ValueError("claimIds must be unique")
        return value

    @field_validator("verifier_ran_at_utc")
    @classmethod
    def _verifier_time_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="verifierRanAtUtc")

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


class AIApprovedMetadataRequest(CamelModel):
    channel: str | None = None
    audience: str | None = None

    def to_mapping(self) -> dict[str, str]:
        return {
            key: value
            for key, value in self.model_dump(exclude_none=True).items()
            if isinstance(value, str)
        }


class AIExplanationEvaluationRequest(CamelModel):
    request_id: str = Field(..., alias="requestId")
    workflow_pack: AIWorkflowPackRequest = Field(..., alias="workflowPack")
    approved_metadata: AIApprovedMetadataRequest = Field(
        default_factory=AIApprovedMetadataRequest,
        alias="approvedMetadata",
    )
    requested_at_utc: datetime = Field(..., alias="requestedAtUtc")
    fallback_reason: AIFallbackReason = Field(
        default=AIFallbackReason.AI_UNAVAILABLE,
        alias="fallbackReason",
    )
    workflow_output: AIWorkflowOutputRequest | None = Field(default=None, alias="workflowOutput")
    producer_run_id: str | None = Field(default=None, alias="producerRunId")
    producer_execution_output: LotusAIExecutionOutputEvidence | None = Field(
        default=None, alias="producerExecutionOutput"
    )
    run_attestation: LotusAIProducerAttestation | None = Field(default=None, alias="runAttestation")
    provider_retention_confirmation: LotusAIProviderRetentionConfirmation | None = Field(
        default=None,
        alias="providerRetentionConfirmation",
    )

    @field_validator("request_id")
    @classmethod
    def _request_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requestId is required")
        return value

    @field_validator("requested_at_utc")
    @classmethod
    def _requested_at_must_be_aware(cls, value: datetime) -> datetime:
        return require_timezone_aware(value, field_name="requestedAtUtc")

    def to_command(
        self,
        *,
        candidate_id: str,
        caller: CallerContext,
        idempotency_key: str,
        allow_unattested_workflow_fixture: bool,
    ) -> EvaluateAIExplanationToRepositoryCommand:
        return EvaluateAIExplanationToRepositoryCommand(
            candidate_id=candidate_id,
            explanation=AIExplanationCommand(
                request_id=self.request_id,
                actor_subject=caller.subject,
                workflow_pack=self.workflow_pack.to_domain(),
                approved_metadata=self.approved_metadata.to_mapping(),
                requested_at_utc=self.requested_at_utc,
            ),
            fallback_reason=self.fallback_reason,
            idempotency_key=idempotency_key,
            idempotency_payload={
                "candidateId": candidate_id,
                "request": self.model_dump(mode="json", by_alias=True),
            },
            workflow_output=(
                self.workflow_output.to_domain(
                    request_id=self.request_id,
                    workflow_pack=self.workflow_pack,
                )
                if self.workflow_output is not None
                else None
            ),
            producer_run_id=self.producer_run_id,
            producer_execution_output=(
                self.producer_execution_output.to_domain()
                if self.producer_execution_output is not None
                else None
            ),
            run_attestation=(
                self.run_attestation.to_domain() if self.run_attestation is not None else None
            ),
            provider_retention_confirmation=(
                self.provider_retention_confirmation.to_domain()
                if self.provider_retention_confirmation is not None
                else None
            ),
            caller_tenant_ids=caller.entitlement_scope.tenant_ids,
            workflow_output_trust_policy=(
                AIWorkflowOutputTrustPolicy.UNATTESTED_LOCAL_TEST_FIXTURE_ALLOWED
                if allow_unattested_workflow_fixture
                else AIWorkflowOutputTrustPolicy.LOTUS_AI_ATTESTATION_REQUIRED
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


class GroundedAIClaimResponse(CamelModel):
    claim_id: str = Field(..., alias="claimId")
    claim_text: str = Field(..., alias="claimText")
    source_refs: tuple[RedactedSourceRefResponse, ...] = Field(..., alias="sourceRefs")

    @classmethod
    def from_domain(
        cls,
        claim: AIOutputClaim,
        evidence: RedactedIdeaEvidence,
    ) -> "GroundedAIClaimResponse":
        source_refs_by_product = {
            source_ref.product_id: source_ref for source_ref in evidence.source_refs
        }
        return cls(
            claimId=claim.claim_id,
            claimText=claim.claim_text,
            sourceRefs=tuple(
                RedactedSourceRefResponse.from_domain(source_refs_by_product[product_id])
                for product_id in claim.source_product_ids
            ),
        )


class AIWorkflowOutputSummaryResponse(CamelModel):
    output_id: str = Field(..., alias="outputId")
    claim_ids: tuple[str, ...] = Field(..., alias="claimIds")
    proposed_action_types: tuple[AIProposedActionType, ...] = Field(
        ...,
        alias="proposedActionTypes",
    )
    verifier_ran_at_utc: datetime = Field(..., alias="verifierRanAtUtc")
    action_policy_version: str = Field(..., alias="actionPolicyVersion")
    claim_grounding_policy_version: str = Field(
        ...,
        alias="claimGroundingPolicyVersion",
    )
    grounded_claims: tuple[GroundedAIClaimResponse, ...] = Field(
        ...,
        alias="groundedClaims",
    )

    @classmethod
    def from_domain(
        cls,
        output: AIWorkflowOutput,
        evidence: RedactedIdeaEvidence,
        *,
        include_grounding: bool,
    ) -> "AIWorkflowOutputSummaryResponse":
        return cls(
            outputId=output.output_id,
            claimIds=tuple(claim.claim_id for claim in output.claims),
            proposedActionTypes=tuple(action.action_type for action in output.proposed_actions),
            verifierRanAtUtc=output.verifier_ran_at_utc,
            actionPolicyVersion=AI_ACTION_POLICY_VERSION,
            claimGroundingPolicyVersion=AI_CLAIM_GROUNDING_POLICY_VERSION,
            groundedClaims=(
                tuple(
                    GroundedAIClaimResponse.from_domain(claim, evidence)
                    for claim in output.claims
                )
                if include_grounding
                else ()
            ),
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
    output_integrity_version: str = Field(..., alias="outputIntegrityVersion")
    output_content_digest: str = Field(..., alias="outputContentDigest")
    execution_provenance_posture: str = Field(..., alias="executionProvenancePosture")
    execution_provenance_policy_version: str = Field(
        ...,
        alias="executionProvenancePolicyVersion",
    )
    metadata_envelope_version: str = Field(..., alias="metadataEnvelopeVersion")
    redacted_evidence: RedactedIdeaEvidenceResponse = Field(..., alias="redactedEvidence")
    verified_output: AIWorkflowOutputSummaryResponse | None = Field(
        default=None,
        alias="verifiedOutput",
    )
    approved_metadata_keys: tuple[str, ...] = Field(..., alias="approvedMetadataKeys")
    ai_lineage_recorded: bool = Field(..., alias="aiLineageRecorded")
    ai_lineage_persistence_decision: str | None = Field(
        default=None,
        alias="aiLineagePersistenceDecision",
    )
    provider_retention_confirmation_recorded: bool = Field(
        False,
        alias="providerRetentionConfirmationRecorded",
    )
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    lotus_ai_runtime_executed: bool = Field(False, alias="lotusAiRuntimeExecuted")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        result: AIExplanationResult,
        *,
        ai_lineage_recorded: bool,
        ai_lineage_persistence_decision: str | None,
        durable_storage_backed: bool,
        provider_retention_confirmation_recorded: bool = False,
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
            outputIntegrityVersion=result.output_integrity.version,
            outputContentDigest=result.output_integrity.digest,
            executionProvenancePosture=result.execution_provenance_posture.value,
            executionProvenancePolicyVersion=AI_EXECUTION_PROVENANCE_POLICY_VERSION,
            metadataEnvelopeVersion=AI_METADATA_ENVELOPE_VERSION,
            redactedEvidence=RedactedIdeaEvidenceResponse.from_domain(
                result.request.redacted_evidence
            ),
            verifiedOutput=(
                AIWorkflowOutputSummaryResponse.from_domain(
                    result.output,
                    result.request.redacted_evidence,
                    include_grounding=(result.verifier_outcome is AIVerifierOutcome.PASSED),
                )
                if result.output is not None
                else None
            ),
            approvedMetadataKeys=tuple(sorted(result.request.approved_metadata.keys())),
            aiLineageRecorded=ai_lineage_recorded,
            aiLineagePersistenceDecision=ai_lineage_persistence_decision,
            durableStorageBacked=durable_storage_backed,
            providerRetentionConfirmationRecorded=provider_retention_confirmation_recorded,
            lotusAiRuntimeExecuted=(
                result.execution_provenance_posture
                is AIExecutionProvenancePosture.LOTUS_AI_ATTESTATION_VERIFIED
            ),
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
    action_content_policy_version: str = Field(..., alias="actionContentPolicyVersion")
    lotus_ai_run_attestation_available: bool = Field(
        ...,
        alias="lotusAiRunAttestationAvailable",
    )
    production_like_attestation_required: bool = Field(
        ...,
        alias="productionLikeAttestationRequired",
    )
    local_test_unattested_fixture_allowed: bool = Field(
        ...,
        alias="localTestUnattestedFixtureAllowed",
    )
    execution_provenance_policy_version: str = Field(
        ...,
        alias="executionProvenancePolicyVersion",
    )
    metadata_envelope_version: str = Field(..., alias="metadataEnvelopeVersion")
    durable_ai_lineage_store_backed: bool = Field(..., alias="durableAiLineageStoreBacked")
    model_risk_operations_contract_available: bool = Field(
        ...,
        alias="modelRiskOperationsContractAvailable",
    )
    model_risk_dashboard_contract_available: bool = Field(
        ...,
        alias="modelRiskDashboardContractAvailable",
    )
    model_risk_alert_contract_available: bool = Field(
        ...,
        alias="modelRiskAlertContractAvailable",
    )
    model_risk_dashboard_certified: bool = Field(..., alias="modelRiskDashboardCertified")
    model_risk_alert_certified: bool = Field(..., alias="modelRiskAlertCertified")
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
            actionContentPolicyVersion=snapshot.action_content_policy_version,
            lotusAiRunAttestationAvailable=snapshot.lotus_ai_run_attestation_available,
            productionLikeAttestationRequired=snapshot.production_like_attestation_required,
            localTestUnattestedFixtureAllowed=(snapshot.local_test_unattested_fixture_allowed),
            executionProvenancePolicyVersion=snapshot.execution_provenance_policy_version,
            metadataEnvelopeVersion=snapshot.metadata_envelope_version,
            durableAiLineageStoreBacked=snapshot.durable_ai_lineage_store_backed,
            modelRiskOperationsContractAvailable=(
                snapshot.model_risk_operations_contract_available
            ),
            modelRiskDashboardContractAvailable=(snapshot.model_risk_dashboard_contract_available),
            modelRiskAlertContractAvailable=snapshot.model_risk_alert_contract_available,
            modelRiskDashboardCertified=snapshot.model_risk_dashboard_certified,
            modelRiskAlertCertified=snapshot.model_risk_alert_certified,
            lotusAiRuntimeExecuted=snapshot.lotus_ai_runtime_executed,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


__all__ = [
    "AIExplanationEvaluationRequest",
    "AIExplanationEvaluationResponse",
    "AIExplanationReadinessResponse",
    "AIOutputClaimRequest",
    "AIProposedActionRequest",
    "AIWorkflowOutputRequest",
    "AIWorkflowOutputSummaryResponse",
    "AIWorkflowPackRequest",
    "AIWorkflowPackResponse",
    "GroundedAIClaimResponse",
    "RedactedIdeaEvidenceResponse",
    "RedactedSourceRefResponse",
]
