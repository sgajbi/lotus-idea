from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from app.application.candidate_lookup import candidate_record_by_id
from app.domain.ai_action_policy import AI_ACTION_POLICY_VERSION
from app.domain.ai_execution_provenance import (
    AI_EXECUTION_PROVENANCE_POLICY_VERSION,
    AIWorkflowOutputTrustPolicy,
    UntrustedAIWorkflowOutput,
)
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
                "production-like workflow output requires verified lotus-ai provenance"
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
        lotus_ai_run_attestation_available=False,
        production_like_attestation_required=True,
        local_test_unattested_fixture_allowed=True,
        execution_provenance_policy_version=AI_EXECUTION_PROVENANCE_POLICY_VERSION,
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
            "lotus_ai_run_attestation_contract_missing",
            "certified_runtime_trust_telemetry_missing",
            "workbench_product_proof_missing",
        ),
        supported_feature_promoted=False,
    )


def evaluate_ai_explanation_to_repository(
    command: EvaluateAIExplanationToRepositoryCommand,
    *,
    repository: AIExplanationRepository,
) -> AIExplanationWorkflowResult:
    record = candidate_record_by_id(repository, command.candidate_id)
    if record is None:
        return AIExplanationWorkflowResult(
            decision=AIExplanationEvaluationDecision.NOT_FOUND,
            explanation_result=None,
        )

    explanation_request = build_ai_explanation_request(record.candidate, command.explanation)
    if command.workflow_output is None:
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
