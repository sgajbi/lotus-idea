from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIExplanationResult,
    AIWorkflowOutput,
    build_ai_explanation_request,
    deterministic_ai_fallback,
    evaluate_ai_workflow_output,
)
from app.ports.idea_repository import AIExplanationRepository


class AIExplanationEvaluationDecision(StrEnum):
    ACCEPTED = "accepted"
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
    durable_ai_lineage_store_backed: bool
    lotus_ai_runtime_executed: bool
    certification_blockers: tuple[str, ...]
    supported_feature_promoted: bool


@dataclass(frozen=True)
class EvaluateAIExplanationToRepositoryCommand:
    candidate_id: str
    explanation: AIExplanationCommand
    fallback_reason: AIFallbackReason
    workflow_output: AIWorkflowOutput | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")


@dataclass(frozen=True)
class AIExplanationWorkflowResult:
    decision: AIExplanationEvaluationDecision
    explanation_result: AIExplanationResult | None


def build_ai_explanation_readiness_snapshot() -> AIExplanationReadinessSnapshot:
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
        durable_ai_lineage_store_backed=False,
        lotus_ai_runtime_executed=False,
        certification_blockers=(
            "lotus_ai_runtime_execution_missing",
            "durable_ai_lineage_store_missing",
            "workflow_pack_runtime_contract_not_certified",
            "model_risk_operations_dashboard_missing",
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
    snapshot = repository.snapshot()
    record = snapshot.candidate_records.get(command.candidate_id)
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

    return AIExplanationWorkflowResult(
        decision=AIExplanationEvaluationDecision.ACCEPTED,
        explanation_result=explanation_result,
    )
