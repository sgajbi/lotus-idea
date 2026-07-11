from __future__ import annotations

from typing import Mapping

from app.domain.ai_governance import AIExplanationRequest, AIWorkflowPurpose
from app.domain.lotus_ai_execution_digest import LotusAIExecutionInputEvidence


_REQUESTED_OUTPUTS: Mapping[AIWorkflowPurpose, tuple[str, ...]] = {
    AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION: (
        "advisor_review_summary",
        "source_evidence_summary",
        "unsupported_claim_check",
    ),
    AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT: (
        "rationale_draft",
        "source_evidence_summary",
    ),
    AIWorkflowPurpose.MEETING_PREPARATION_DRAFT: (
        "advisor_review_summary",
        "evidence_gap_questions",
        "source_evidence_summary",
    ),
}

_FORBIDDEN_ACTIONS = (
    "approve_suitability",
    "contact_client",
    "invent_missing_evidence",
    "make_final_recommendation",
    "place_orders",
)

_UNSUPPORTED_CLAIMS = (
    "client_ready_publication",
    "final_investment_recommendation",
    "suitability_approval",
    "trade_or_order_action",
)


def build_lotus_ai_idea_explanation_input(
    request: AIExplanationRequest,
) -> LotusAIExecutionInputEvidence:
    evidence = request.redacted_evidence
    payload: dict[str, object] = {
        "redacted_evidence_packet": {
            "candidate_id": evidence.candidate_id,
            "family": evidence.family.value,
            "lifecycle_status": evidence.lifecycle_status.value,
            "review_posture": evidence.review_posture.value,
            "evidence_packet_id": evidence.evidence_packet_id,
            "evidence_content_hash": evidence.evidence_content_hash,
            "supportability": evidence.supportability.value,
            "score_policy_version": evidence.score_policy_version,
            "score": str(evidence.score) if evidence.score is not None else None,
            "source_signal_count": evidence.source_signal_count,
            "reason_codes": [reason.value for reason in evidence.reason_codes],
            "source_refs": [
                {
                    "source_system": source_ref.source_system.value,
                    "product_id": source_ref.product_id,
                    "product_version": source_ref.product_version,
                    "as_of_date": source_ref.as_of_date.isoformat(),
                    "freshness": source_ref.freshness.value,
                    "data_quality_status": source_ref.data_quality_status,
                }
                for source_ref in evidence.source_refs
            ],
        },
        "explanation_request": {
            "request_id": request.request_id,
            "workflow_pack_id": request.workflow_pack.workflow_pack_id,
            "workflow_pack_version": request.workflow_pack.workflow_pack_version,
            "purpose": request.purpose.value,
            "evaluation_ref": request.workflow_pack.evaluation_ref,
            "audience": request.approved_metadata.get("audience", "advisor"),
            "requested_outputs": list(_REQUESTED_OUTPUTS[request.purpose]),
        },
        "supportability": {
            "human_review_required": True,
            "client_ready_publication": "BLOCKED",
            "forbidden_actions": list(_FORBIDDEN_ACTIONS),
            "unsupported_claims": list(_UNSUPPORTED_CLAIMS),
        },
    }
    return LotusAIExecutionInputEvidence(
        task_id="explain.v1",
        context_summary=("Generate a review-gated Idea explanation from redacted source evidence."),
        context_payload=payload,
        source_refs=(f"lotus-idea:evidence-packet:{evidence.evidence_packet_id}",),
        expected_output_label="EXPLANATION_ONLY",
    )
