from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.domain.ai_governance import (
    AIOutputClaim,
    AIProposedAction,
    AIProposedActionType,
    AIWorkflowOutput,
)
from app.domain.lotus_ai_execution_digest import LotusAIExecutionOutputContent


def map_lotus_ai_idea_workflow_output(
    evidence: LotusAIExecutionOutputContent,
    *,
    request_id: str,
    workflow_pack_id: str,
    workflow_pack_version: str,
    verifier_ran_at_utc: datetime,
) -> AIWorkflowOutput:
    if evidence.status != "COMPLETED":
        raise ValueError("lotus-ai Idea execution must be completed")
    if evidence.output_label != "EXPLANATION_ONLY":
        raise ValueError("lotus-ai Idea execution output label is invalid")
    raw_output = evidence.structured_output.get("idea_workflow_output")
    if not isinstance(raw_output, Mapping):
        raise ValueError("lotus-ai Idea execution is missing idea_workflow_output")
    output_id = _text(raw_output, "output_id")
    explanation_text = _text(raw_output, "explanation_text")
    if explanation_text != evidence.message:
        raise ValueError("lotus-ai Idea execution message does not match workflow output")
    return AIWorkflowOutput(
        output_id=output_id,
        request_id=request_id,
        workflow_pack_id=workflow_pack_id,
        workflow_pack_version=workflow_pack_version,
        explanation_text=explanation_text,
        claims=_claims(raw_output.get("claims")),
        proposed_actions=_actions(raw_output.get("proposed_actions")),
        verifier_ran_at_utc=verifier_ran_at_utc,
    )


def _claims(value: object) -> tuple[AIOutputClaim, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("lotus-ai Idea workflow output claims are required")
    return tuple(
        AIOutputClaim(
            claim_id=_text(item, "claim_id"),
            claim_text=_text(item, "claim_text"),
            source_product_ids=_text_list(item, "source_product_ids"),
        )
        for item in _object_list(value, "claims")
    )


def _actions(value: object) -> tuple[AIProposedAction, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("lotus-ai Idea workflow output proposed actions are required")
    return tuple(
        AIProposedAction(
            action_type=AIProposedActionType(_text(item, "action_type")),
            action_label=_text(item, "action_label"),
        )
        for item in _object_list(value, "proposed_actions")
    )


def _object_list(value: list[object], label: str) -> tuple[Mapping[str, object], ...]:
    if any(not isinstance(item, Mapping) for item in value):
        raise ValueError(f"lotus-ai Idea workflow output {label} must contain objects")
    return tuple(item for item in value if isinstance(item, Mapping))


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"lotus-ai Idea workflow output {key} is required")
    return value.strip()


def _text_list(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"lotus-ai Idea workflow output {key} is required")
    values = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(values) != len(value):
        raise ValueError(f"lotus-ai Idea workflow output {key} contains invalid values")
    return values
