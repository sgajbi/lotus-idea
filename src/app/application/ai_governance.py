from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Callable, Mapping

from app.application.candidate_lookup import candidate_record_by_id
from app.domain.ai_action_policy import AI_ACTION_POLICY_VERSION
from app.domain.ai_execution_provenance import (
    AI_EXECUTION_PROVENANCE_POLICY_VERSION,
    AIWorkflowProvenanceRejectionReason,
    AIWorkflowOutputTrustPolicy,
    UntrustedAIWorkflowOutput,
)
from app.domain.ai_metadata_policy import AI_METADATA_ENVELOPE_VERSION
from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIExplanationLineagePersistenceDecision,
    AIExplanationLineagePersistenceResult,
    AIExplanationResult,
    AIWorkflowOutput,
    build_ai_explanation_request,
    deterministic_ai_fallback,
    evaluate_ai_workflow_output,
)
from app.ports.idea_repository import AIExplanationRepository
from app.ports.lotus_ai_attestation import LotusAIAttestationKeySource
from app.domain.lotus_ai_execution_digest import (
    LotusAIExecutionOutputContent,
    lotus_ai_input_evidence_sha256,
    lotus_ai_output_content_sha256,
)
from app.domain.lotus_ai_run_attestation import (
    ExpectedLotusAIRunAttestation,
    LotusAIRunAttestationEnvelope,
)
from app.application.lotus_ai_idea_explanation_output import (
    map_lotus_ai_idea_workflow_output,
)
from app.application.lotus_ai_idea_explanation_request import (
    build_lotus_ai_idea_explanation_input,
)
from app.application.lotus_ai_run_attestation_verification import (
    LotusAIAttestationSignatureVerifier,
    verify_lotus_ai_run_attestation,
)
from app.domain.ai_execution_provenance import AIExecutionProvenancePosture


class AIExplanationEvaluationDecision(StrEnum):
    ACCEPTED = "accepted"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class AIExplanationReadinessSnapshot:
    repository: str
    source_authority: str
    workflow_authority: str
    readiness_status: str
    supportability_status: str
    certification_ready: bool
    deterministic_fallback_available: bool
    verifier_available: bool
    redacted_evidence_envelope_available: bool
    unsupported_claim_blocking_available: bool
    forbidden_action_blocking_available: bool
    action_content_policy_version: str
    lotus_ai_run_attestation_available: bool
    production_like_attestation_required: bool
    local_test_unattested_fixture_allowed: bool
    execution_provenance_policy_version: str
    metadata_envelope_version: str
    durable_ai_lineage_store_backed: bool
    model_risk_operations_contract_available: bool
    model_risk_dashboard_contract_available: bool
    model_risk_alert_contract_available: bool
    model_risk_dashboard_certified: bool
    model_risk_alert_certified: bool
    lotus_ai_runtime_executed: bool
    certification_blockers: tuple[str, ...]
    supported_feature_promoted: bool


@dataclass(frozen=True)
class EvaluateAIExplanationToRepositoryCommand:
    candidate_id: str
    explanation: AIExplanationCommand
    fallback_reason: AIFallbackReason
    idempotency_key: str
    idempotency_payload: Mapping[str, Any]
    workflow_output: AIWorkflowOutput | None = None
    producer_run_id: str | None = None
    producer_execution_output: LotusAIExecutionOutputContent | None = None
    run_attestation: LotusAIRunAttestationEnvelope | None = None
    workflow_output_trust_policy: AIWorkflowOutputTrustPolicy = (
        AIWorkflowOutputTrustPolicy.LOTUS_AI_ATTESTATION_REQUIRED
    )

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if (
            self.workflow_output is not None
            and self.workflow_output_trust_policy
            is AIWorkflowOutputTrustPolicy.LOTUS_AI_ATTESTATION_REQUIRED
        ):
            raise UntrustedAIWorkflowOutput(
                "production-like workflow output requires verified lotus-ai provenance",
                reason=AIWorkflowProvenanceRejectionReason.PROVENANCE_REQUIRED,
            )
        attested_values = (
            self.producer_run_id,
            self.producer_execution_output,
            self.run_attestation,
        )
        if any(value is not None for value in attested_values) and not all(
            value is not None for value in attested_values
        ):
            raise UntrustedAIWorkflowOutput(
                "lotus-ai run id, execution output, and attestation must be provided together",
                reason=AIWorkflowProvenanceRejectionReason.INCOMPLETE_ATTESTATION_BUNDLE,
            )
        if self.run_attestation is not None and self.workflow_output is not None:
            raise UntrustedAIWorkflowOutput(
                "attested lotus-ai output cannot be combined with caller-mapped workflow output",
                reason=AIWorkflowProvenanceRejectionReason.CONFLICTING_OUTPUT_SOURCES,
            )


@dataclass(frozen=True)
class AIExplanationWorkflowResult:
    decision: AIExplanationEvaluationDecision
    explanation_result: AIExplanationResult | None
    lineage_persistence_result: AIExplanationLineagePersistenceResult | None = None


def build_ai_explanation_readiness_snapshot(
    *,
    durable_ai_lineage_store_backed: bool = False,
) -> AIExplanationReadinessSnapshot:
    return AIExplanationReadinessSnapshot(
        repository="lotus-idea",
        source_authority="lotus-idea",
        workflow_authority="lotus-ai",
        readiness_status="blocked",
        supportability_status="not_certified",
        certification_ready=False,
        deterministic_fallback_available=True,
        verifier_available=True,
        redacted_evidence_envelope_available=True,
        unsupported_claim_blocking_available=True,
        forbidden_action_blocking_available=True,
        action_content_policy_version=AI_ACTION_POLICY_VERSION,
        lotus_ai_run_attestation_available=True,
        production_like_attestation_required=True,
        local_test_unattested_fixture_allowed=True,
        execution_provenance_policy_version=AI_EXECUTION_PROVENANCE_POLICY_VERSION,
        metadata_envelope_version=AI_METADATA_ENVELOPE_VERSION,
        durable_ai_lineage_store_backed=durable_ai_lineage_store_backed,
        model_risk_operations_contract_available=True,
        model_risk_dashboard_contract_available=True,
        model_risk_alert_contract_available=True,
        model_risk_dashboard_certified=True,
        model_risk_alert_certified=True,
        lotus_ai_runtime_executed=False,
        certification_blockers=(
            "lotus_ai_runtime_execution_missing",
            "certified_ai_lineage_store_missing",
            "workflow_pack_runtime_contract_not_certified",
            "lotus_ai_run_attestation_mainline_proof_missing",
            "certified_runtime_trust_telemetry_missing",
            "workbench_product_proof_missing",
        ),
        supported_feature_promoted=False,
    )


def evaluate_ai_explanation_to_repository(
    command: EvaluateAIExplanationToRepositoryCommand,
    *,
    repository: AIExplanationRepository,
    attestation_key_source: LotusAIAttestationKeySource | None = None,
    signature_verifier: LotusAIAttestationSignatureVerifier | None = None,
    verification_clock: Callable[[], datetime] | None = None,
) -> AIExplanationWorkflowResult:
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return AIExplanationWorkflowResult(
            decision=AIExplanationEvaluationDecision.NOT_FOUND,
            explanation_result=None,
        )

    explanation_request = build_ai_explanation_request(record.candidate, command.explanation)
    attestation_receipt = None
    if command.run_attestation is not None:
        if attestation_key_source is None or signature_verifier is None:
            raise UntrustedAIWorkflowOutput(
                "lotus-ai attestation trust infrastructure is unavailable",
                reason=AIWorkflowProvenanceRejectionReason.TRUST_INFRASTRUCTURE_UNAVAILABLE,
            )
        assert command.producer_run_id is not None
        assert command.producer_execution_output is not None
        verified_at = (verification_clock or _utcnow)()
        input_evidence = build_lotus_ai_idea_explanation_input(explanation_request)
        try:
            attestation_receipt = verify_lotus_ai_run_attestation(
                envelope=command.run_attestation,
                key_discovery=attestation_key_source.get_key_discovery(),
                expected=ExpectedLotusAIRunAttestation(
                    run_id=command.producer_run_id,
                    consumer_request_id=explanation_request.request_id,
                    input_evidence_sha256=lotus_ai_input_evidence_sha256(input_evidence),
                    output_content_sha256=lotus_ai_output_content_sha256(
                        command.producer_execution_output
                    ),
                    verified_at_utc=verified_at,
                ),
                signature_verifier=signature_verifier,
            )
            workflow_output = map_lotus_ai_idea_workflow_output(
                command.producer_execution_output,
                request_id=explanation_request.request_id,
                workflow_pack_id=explanation_request.workflow_pack.workflow_pack_id,
                workflow_pack_version=explanation_request.workflow_pack.workflow_pack_version,
                verifier_ran_at_utc=verified_at,
            )
        except (RuntimeError, ValueError) as exc:
            raise UntrustedAIWorkflowOutput(
                "lotus-ai attestation verification failed",
                reason=AIWorkflowProvenanceRejectionReason.ATTESTATION_VERIFICATION_FAILED,
            ) from exc
        explanation_result = replace(
            evaluate_ai_workflow_output(explanation_request, workflow_output),
            execution_provenance_posture=(
                AIExecutionProvenancePosture.LOTUS_AI_ATTESTATION_VERIFIED
            ),
        )
    elif command.workflow_output is None:
        explanation_result = deterministic_ai_fallback(
            explanation_request,
            fallback_reason=command.fallback_reason,
            occurred_at_utc=command.explanation.requested_at_utc,
        )
    else:
        explanation_result = evaluate_ai_workflow_output(
            explanation_request,
            command.workflow_output,
        )

    lineage_persistence_result = repository.record_ai_explanation_lineage_request(
        explanation_result,
        idempotency_key=command.idempotency_key,
        payload=dict(command.idempotency_payload),
        attestation_receipt=attestation_receipt,
    )
    if (
        lineage_persistence_result.decision is AIExplanationLineagePersistenceDecision.CONFLICT
        and lineage_persistence_result.lineage_record is None
    ):
        return AIExplanationWorkflowResult(
            decision=AIExplanationEvaluationDecision.IDEMPOTENCY_CONFLICT,
            explanation_result=explanation_result,
            lineage_persistence_result=lineage_persistence_result,
        )

    return AIExplanationWorkflowResult(
        decision=AIExplanationEvaluationDecision.ACCEPTED,
        explanation_result=explanation_result,
        lineage_persistence_result=lineage_persistence_result,
    )


def _utcnow() -> datetime:
    return datetime.now(UTC)
