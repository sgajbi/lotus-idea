from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIExplanationResult,
    AIWorkflowOutput,
    IdeaRepositorySnapshot,
    build_ai_explanation_request,
    deterministic_ai_fallback,
    evaluate_ai_workflow_output,
)


class AIExplanationEvaluationDecision(StrEnum):
    ACCEPTED = "accepted"
    NOT_FOUND = "not_found"


class AIExplanationRepository(Protocol):
    def snapshot(self) -> IdeaRepositorySnapshot: ...


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
