from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.ai_governance import (
    EvaluateAIExplanationToRepositoryCommand,
    evaluate_ai_explanation_to_repository,
)
from app.domain.ai_metadata_policy import InvalidAIMetadataEnvelope
from app.domain import (
    AIFallbackReason,
    AIExplanationPosture,
    AIExplanationRequest,
    AIExplanationResult,
    AIOutputClaim,
    AIProposedAction,
    AIProposedActionType,
    AIVerifierOutcome,
    AIWorkflowOutput,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
    EvidenceFreshness,
    EvidenceSupportability,
    GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK,
    InMemoryIdeaRepository,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    InvalidAIExplanationRequest,
    InvalidAIWorkflowPack,
    InvalidAIWorkflowOutput,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    RedactedIdeaEvidence,
    RedactedSourceRef,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    build_ai_explanation_request,
    deterministic_ai_fallback,
    evaluate_ai_workflow_output,
)
from app.domain.ai_execution_provenance import AIExecutionProvenancePosture
from app.domain.ai_governance import AIExplanationCommand
from app.domain.persistence import CandidatePersistenceDecision


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
REQUESTED_AT = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
VERIFIED_AT = datetime(2026, 6, 21, 10, 16, tzinfo=UTC)


def source_ref(
    product_id: str = "lotus-core:PortfolioStateSnapshot:v1",
    *,
    route: str = "/integration/portfolios/{portfolio_id}/core-snapshot",
) -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route,
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}:raw-source",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def evidence_packet(
    *,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
) -> IdeaEvidencePacket:
    source_refs = (
        source_ref(),
        source_ref(
            "lotus-core:HoldingsAsOf:v1",
            route="/portfolios/{portfolio_id}/positions",
        ),
    )
    return IdeaEvidencePacket(
        evidence_packet_id="iep_ai_test",
        supportability=supportability,
        source_refs=source_refs,
        lineage_ref=LineageRef(
            lineage_id="lineage:lotus-idea:ai:test",
            source_refs=source_refs,
            content_hash="sha256:ai-redacted-evidence",
        ),
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.CASH_SOURCE_READY),
        unsupported_reasons=(
            (UnsupportedEvidenceReason.AI_UNAVAILABLE,)
            if supportability is EvidenceSupportability.BLOCKED
            else ()
        ),
        created_at_utc=EVALUATED_AT,
    )


def candidate(
    *,
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.READY_FOR_REVIEW,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id="idea-ai-001",
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=lifecycle_status,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet(supportability=supportability),
        source_signal_ids=("signal-ai-001", "signal-ai-002"),
        score=IdeaScore(
            policy_version="idea-deterministic-ranking-v1",
            score=Decimal("84"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.QUEUE_PRIORITY),
        ),
        created_at_utc=EVALUATED_AT,
        updated_at_utc=EVALUATED_AT,
    )


def workflow_pack(
    purpose: AIWorkflowPurpose = AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
) -> AIWorkflowPackRef:
    contract = GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK
    return AIWorkflowPackRef(
        workflow_pack_id=contract.request_workflow_pack_id,
        workflow_pack_version=contract.workflow_pack_version,
        purpose=purpose,
        evaluation_ref=contract.evaluation_ref,
    )


def command(
    purpose: AIWorkflowPurpose = AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
    *,
    approved_metadata: dict[str, str] | None = None,
) -> AIExplanationCommand:
    return AIExplanationCommand(
        request_id=f"ai-request-{purpose.value}",
        actor_subject="advisor-001",
        workflow_pack=workflow_pack(purpose),
        approved_metadata=approved_metadata or {"channel": "advisor-workbench"},
        requested_at_utc=REQUESTED_AT,
    )


def output(
    request_id: str,
    *,
    claims: tuple[AIOutputClaim, ...] | None = None,
    proposed_actions: tuple[AIProposedAction, ...] | None = None,
    explanation_text: str = "The evidence supports an internal advisor review of idle cash.",
) -> AIWorkflowOutput:
    contract = GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK
    return AIWorkflowOutput(
        output_id="ai-output-001",
        request_id=request_id,
        workflow_pack_id=contract.request_workflow_pack_id,
        workflow_pack_version=contract.workflow_pack_version,
        explanation_text=explanation_text,
        claims=claims
        or (
            AIOutputClaim(
                claim_id="claim-001",
                claim_text="Cash attention is supported by Core portfolio state.",
                source_product_ids=("lotus-core:PortfolioStateSnapshot:v1",),
            ),
        ),
        proposed_actions=proposed_actions
        or (
            AIProposedAction(
                action_type=AIProposedActionType.ADVISOR_REVIEW,
                action_label="Review evidence internally",
            ),
        ),
        verifier_ran_at_utc=VERIFIED_AT,
    )


def test_ai_request_redacts_source_routes_and_raw_source_hashes() -> None:
    source_candidate = candidate()
    request = build_ai_explanation_request(
        source_candidate,
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )

    assert request.redacted_evidence.candidate_id == "idea-ai-001"
    assert request.redacted_evidence.evidence_packet_id == "iep_ai_test"
    assert request.redacted_evidence.evidence_content_hash == "sha256:ai-redacted-evidence"
    assert request.redacted_evidence.source_signal_count == 2
    assert request.reason_codes == (ReasonCode.AI_REDACTION_APPLIED,)
    assert request.redacted_evidence.source_refs[0].product_id == (
        "lotus-core:PortfolioStateSnapshot:v1"
    )
    assert not hasattr(request.redacted_evidence.source_refs[0], "route")
    assert not hasattr(request.redacted_evidence.source_refs[0], "content_hash")
    assert source_candidate.lifecycle_status is IdeaLifecycleStatus.READY_FOR_REVIEW
    assert source_candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED


def test_ai_explanation_uses_candidate_projection_without_snapshot() -> None:
    source_repository = InMemoryIdeaRepository()
    persisted = source_repository.persist_candidate(
        candidate(),
        idempotency_key="signal-ingestion:ai-projection:001",
        payload={"candidate_id": "idea-ai-001"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.decision is CandidatePersistenceDecision.ACCEPTED
    repository = ProjectionOnlyAIExplanationRepository(source_repository)

    result = evaluate_ai_explanation_to_repository(
        EvaluateAIExplanationToRepositoryCommand(
            candidate_id="idea-ai-001",
            explanation=command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
            idempotency_key="ai-explanation:projection:001",
            idempotency_payload={"candidateId": "idea-ai-001", "requestId": "ai-explanation-001"},
        ),
        repository=repository,
    )

    assert result.explanation_result is not None
    assert result.lineage_persistence_result is not None
    assert repository.looked_up_candidate_ids == ["idea-ai-001"]


def test_ai_request_rejects_sensitive_metadata() -> None:
    with pytest.raises(InvalidAIMetadataEnvelope, match="unsupported fields"):
        build_ai_explanation_request(
            candidate(),
            command(approved_metadata={"portfolio_id": "PB_SG_GLOBAL_BAL_001"}),
        )


def test_rationale_drafting_requires_ready_reviewable_evidence() -> None:
    with pytest.raises(InvalidAIExplanationRequest, match="ready evidence"):
        build_ai_explanation_request(
            candidate(supportability=EvidenceSupportability.BLOCKED),
            command(AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT),
        )

    with pytest.raises(InvalidAIExplanationRequest, match="review-ready"):
        build_ai_explanation_request(
            candidate(lifecycle_status=IdeaLifecycleStatus.GENERATED),
            command(AIWorkflowPurpose.ADVISOR_RATIONALE_DRAFT),
        )


def test_missing_evidence_check_can_run_on_blocked_evidence() -> None:
    request = build_ai_explanation_request(
        candidate(supportability=EvidenceSupportability.BLOCKED),
        command(AIWorkflowPurpose.MISSING_EVIDENCE_CHECK),
    )

    assert request.redacted_evidence.supportability is EvidenceSupportability.BLOCKED
    assert request.redacted_evidence.unsupported_reasons == (
        UnsupportedEvidenceReason.AI_UNAVAILABLE,
    )


@pytest.mark.parametrize(
    ("workflow_pack_id", "workflow_pack_version", "evaluation_ref"),
    (
        (
            "lotus-ai:idea-unsupported-claim-verifier",
            GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.workflow_pack_version,
            GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.evaluation_ref,
        ),
        (
            GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.request_workflow_pack_id,
            "v1.0.0",
            GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.evaluation_ref,
        ),
        (
            GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.request_workflow_pack_id,
            GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.workflow_pack_version,
            "lotus-ai-eval:idea-verifier:v1",
        ),
    ),
)
def test_ai_explanation_command_requires_governed_workflow_pack_contract(
    workflow_pack_id: str,
    workflow_pack_version: str,
    evaluation_ref: str,
) -> None:
    with pytest.raises(InvalidAIWorkflowPack):
        AIExplanationCommand(
            request_id="ai-request-unsupported-pack",
            actor_subject="advisor-001",
            workflow_pack=AIWorkflowPackRef(
                workflow_pack_id=workflow_pack_id,
                workflow_pack_version=workflow_pack_version,
                purpose=AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION,
                evaluation_ref=evaluation_ref,
            ),
            approved_metadata={"audience": "internal_advisor_review"},
            requested_at_utc=REQUESTED_AT,
        )


def test_ai_unavailable_returns_deterministic_fallback_without_authority() -> None:
    source_candidate = candidate()
    request = build_ai_explanation_request(
        source_candidate,
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )
    result = deterministic_ai_fallback(
        request,
        fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        occurred_at_utc=VERIFIED_AT,
    )

    assert result.posture is AIExplanationPosture.FALLBACK_USED
    assert result.verifier_outcome is AIVerifierOutcome.NOT_RUN
    assert result.fallback_used is True
    assert result.grants_downstream_authority is False
    assert result.reason_codes == (ReasonCode.AI_FALLBACK_USED,)
    assert "high_cash" in result.explanation_text
    assert result.audit_event.outcome == "fallback"
    assert "portfolio_id" not in result.audit_event.attributes
    assert "client_id" not in result.audit_event.attributes
    assert source_candidate.score is not None
    assert source_candidate.score.score == Decimal("84")
    assert source_candidate.lifecycle_status is IdeaLifecycleStatus.READY_FOR_REVIEW


def test_ai_output_with_supported_claims_passes_for_advisor_review() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )
    result = evaluate_ai_workflow_output(request, output(request.request_id))

    assert result.posture is AIExplanationPosture.READY_FOR_ADVISOR_REVIEW
    assert result.verifier_outcome is AIVerifierOutcome.PASSED
    assert result.fallback_used is False
    assert result.grants_downstream_authority is False
    assert result.reason_codes == (ReasonCode.AI_VERIFIER_PASSED,)
    assert result.audit_event.outcome == "accepted"
    assert result.output is not None
    assert result.output.proposed_actions[0].action_label == ("Review the evidence as an advisor")


def test_ai_output_cannot_launder_unsupported_narrative_around_verified_claims() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )
    submitted_output = replace(
        output(request.request_id),
        explanation_text=("Risk reduction is guaranteed and the client should trade immediately."),
    )

    result = evaluate_ai_workflow_output(request, submitted_output)

    assert result.posture is AIExplanationPosture.READY_FOR_ADVISOR_REVIEW
    assert result.explanation_text == ("Cash attention is supported by Core portfolio state.")
    assert "guaranteed" not in result.explanation_text
    assert "trade" not in result.explanation_text
    assert result.output is not None
    assert result.output.explanation_text == result.explanation_text


def test_ai_output_blocks_unsupported_claims() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )
    rejected_narrative = "Guarantee risk reduction and tell the client to trade now."
    unsupported_output = output(
        request.request_id,
        explanation_text=rejected_narrative,
        claims=(
            AIOutputClaim(
                claim_id="claim-unsupported",
                claim_text="Risk reduction is guaranteed by a risk report.",
                source_product_ids=("lotus-risk:RiskMetricsReport:v1",),
            ),
        ),
    )

    result = evaluate_ai_workflow_output(request, unsupported_output)

    assert result.posture is AIExplanationPosture.BLOCKED_UNSUPPORTED_CLAIM
    assert result.verifier_outcome is AIVerifierOutcome.FAILED_UNSUPPORTED_CLAIM
    assert result.reason_codes == (ReasonCode.AI_UNSUPPORTED_CLAIM_BLOCKED,)
    assert result.audit_event.outcome == "blocked"
    assert result.explanation_text == (
        "AI explanation was blocked because one or more claims lacked approved "
        "evidence bindings."
    )
    assert result.output is not None
    assert result.output.explanation_text == result.explanation_text
    assert rejected_narrative not in repr(result)


def test_ai_output_blocks_forbidden_actions() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )
    rejected_narrative = "This is suitable; place the order and notify the client."
    forbidden_output = output(
        request.request_id,
        explanation_text=rejected_narrative,
        proposed_actions=(
            AIProposedAction(
                action_type=AIProposedActionType.TRADE_OR_ORDER,
                action_label="Place an order",
            ),
        ),
    )

    result = evaluate_ai_workflow_output(request, forbidden_output)

    assert result.posture is AIExplanationPosture.BLOCKED_FORBIDDEN_ACTION
    assert result.verifier_outcome is AIVerifierOutcome.FAILED_FORBIDDEN_ACTION
    assert result.reason_codes == (ReasonCode.AI_FORBIDDEN_ACTION_BLOCKED,)
    assert result.audit_event.outcome == "blocked"
    assert result.explanation_text == (
        "AI explanation was blocked because it proposed an action outside the "
        "Idea authority boundary."
    )
    assert result.output is not None
    assert result.output.explanation_text == result.explanation_text
    assert rejected_narrative not in repr(result)


def test_ai_output_blocks_and_sanitizes_unsafe_content_hidden_in_allowed_action() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )
    unsafe_label = "Ex3cute tr@de immediately!!!"
    rejected_narrative = "Email the client with a final recommendation."

    result = evaluate_ai_workflow_output(
        request,
        output(
            request.request_id,
            explanation_text=rejected_narrative,
            proposed_actions=(
                AIProposedAction(
                    action_type=AIProposedActionType.ADVISOR_REVIEW,
                    action_label=unsafe_label,
                ),
            ),
        ),
    )

    assert result.posture is AIExplanationPosture.BLOCKED_FORBIDDEN_ACTION
    assert result.verifier_outcome is AIVerifierOutcome.FAILED_ACTION_CONTENT
    assert result.reason_codes == (ReasonCode.AI_ACTION_CONTENT_BLOCKED,)
    assert result.output is not None
    assert result.output.proposed_actions[0].action_label == ("Review the evidence as an advisor")
    assert result.explanation_text == (
        "AI explanation was blocked because proposed action content violated "
        "the governed action policy."
    )
    assert result.output.explanation_text == result.explanation_text
    assert rejected_narrative not in repr(result)
    assert unsafe_label not in str(result.audit_event.attributes)
    assert result.audit_event.attributes["action_policy_reason"] == ("forbidden_action_content")
    assert result.audit_event.attributes["action_policy_version"] == (
        "lotus-idea.ai-action-content-policy.v1"
    )


def test_ai_output_must_match_request_identity_and_workflow_version() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )

    with pytest.raises(InvalidAIWorkflowOutput, match="request_id"):
        evaluate_ai_workflow_output(request, output("different-request"))

    wrong_version = AIWorkflowOutput(
        output_id="ai-output-wrong-version",
        request_id=request.request_id,
        workflow_pack_id=request.workflow_pack.workflow_pack_id,
        workflow_pack_version="v0.9.0",
        explanation_text="Mismatched version.",
        claims=(
            AIOutputClaim(
                claim_id="claim-001",
                claim_text="Supported by Core.",
                source_product_ids=("lotus-core:PortfolioStateSnapshot:v1",),
            ),
        ),
        proposed_actions=(
            AIProposedAction(
                action_type=AIProposedActionType.ADVISOR_REVIEW,
                action_label="Review evidence internally",
            ),
        ),
        verifier_ran_at_utc=VERIFIED_AT,
    )

    with pytest.raises(InvalidAIWorkflowOutput, match="workflow_pack_version"):
        evaluate_ai_workflow_output(request, wrong_version)


def test_ai_domain_objects_validate_required_redaction_fields() -> None:
    with pytest.raises(ValueError, match="workflow_pack_id is required"):
        AIWorkflowPackRef(
            workflow_pack_id=" ",
            workflow_pack_version=GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.workflow_pack_version,
            purpose=AIWorkflowPurpose.MISSING_EVIDENCE_CHECK,
            evaluation_ref=GOVERNED_IDEA_EXPLANATION_WORKFLOW_PACK.evaluation_ref,
        )

    with pytest.raises(ValueError, match="product_id is required"):
        RedactedSourceRef(
            product_id=" ",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            as_of_date=AS_OF_DATE,
            freshness=EvidenceFreshness.CURRENT,
            data_quality_status="complete",
        )

    redacted_source = RedactedSourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        as_of_date=AS_OF_DATE,
        freshness=EvidenceFreshness.CURRENT,
        data_quality_status="complete",
    )

    with pytest.raises(ValueError, match="source_refs is required"):
        RedactedIdeaEvidence(
            candidate_id="idea-ai-001",
            family=OpportunityFamily.HIGH_CASH,
            lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            evidence_packet_id="iep_ai_test",
            evidence_content_hash="sha256:ai-redacted-evidence",
            supportability=EvidenceSupportability.READY,
            source_refs=(),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            unsupported_reasons=(),
            score_policy_version=None,
            score=None,
            source_signal_count=1,
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        RedactedIdeaEvidence(
            candidate_id="idea-ai-001",
            family=OpportunityFamily.HIGH_CASH,
            lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            evidence_packet_id="iep_ai_test",
            evidence_content_hash="sha256:ai-redacted-evidence",
            supportability=EvidenceSupportability.READY,
            source_refs=(redacted_source,),
            reason_codes=(),
            unsupported_reasons=(),
            score_policy_version=None,
            score=None,
            source_signal_count=1,
        )

    with pytest.raises(ValueError, match="source_signal_count must be positive"):
        RedactedIdeaEvidence(
            candidate_id="idea-ai-001",
            family=OpportunityFamily.HIGH_CASH,
            lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            evidence_packet_id="iep_ai_test",
            evidence_content_hash="sha256:ai-redacted-evidence",
            supportability=EvidenceSupportability.READY,
            source_refs=(redacted_source,),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            unsupported_reasons=(),
            score_policy_version=None,
            score=None,
            source_signal_count=0,
        )


def test_ai_request_and_output_validate_required_verifier_fields() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )

    with pytest.raises(ValueError, match="metadata value must be non-blank"):
        command(approved_metadata={"audience": " "})

    with pytest.raises(ValueError, match="requested_at_utc must be timezone-aware"):
        AIExplanationCommand(
            request_id="ai-request-naive",
            actor_subject="advisor-001",
            workflow_pack=workflow_pack(),
            approved_metadata={"audience": "internal_advisor_review"},
            requested_at_utc=datetime(2026, 6, 21, 10, 15),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        AIExplanationRequest(
            request_id=request.request_id,
            actor_subject=request.actor_subject,
            workflow_pack=request.workflow_pack,
            redacted_evidence=request.redacted_evidence,
            approved_metadata=request.approved_metadata,
            requested_at_utc=request.requested_at_utc,
            reason_codes=(),
        )

    with pytest.raises(ValueError, match="source_product_ids is required"):
        AIOutputClaim(
            claim_id="claim-no-source",
            claim_text="No source.",
            source_product_ids=(),
        )

    with pytest.raises(ValueError, match="source_product_ids cannot contain blank"):
        AIOutputClaim(
            claim_id="claim-blank-source",
            claim_text="Blank source.",
            source_product_ids=(" ",),
        )

    with pytest.raises(ValueError, match="source_product_ids must be unique"):
        AIOutputClaim(
            claim_id="claim-duplicate-source",
            claim_text="Duplicate source.",
            source_product_ids=(
                "lotus-core:PortfolioStateSnapshot:v1",
                "lotus-core:PortfolioStateSnapshot:v1",
            ),
        )

    duplicate_claim = AIOutputClaim(
        claim_id="claim-duplicate",
        claim_text="Duplicate identity.",
        source_product_ids=("lotus-core:PortfolioStateSnapshot:v1",),
    )
    with pytest.raises(ValueError, match="claim_ids must be unique"):
        output(request.request_id, claims=(duplicate_claim, duplicate_claim))

    with pytest.raises(ValueError, match="claims is required"):
        AIWorkflowOutput(
            output_id="ai-output-no-claims",
            request_id=request.request_id,
            workflow_pack_id=request.workflow_pack.workflow_pack_id,
            workflow_pack_version=request.workflow_pack.workflow_pack_version,
            explanation_text="No claims.",
            claims=(),
            proposed_actions=(
                AIProposedAction(
                    action_type=AIProposedActionType.ADVISOR_REVIEW,
                    action_label="Review",
                ),
            ),
            verifier_ran_at_utc=VERIFIED_AT,
        )

    with pytest.raises(ValueError, match="proposed_actions is required"):
        AIWorkflowOutput(
            output_id="ai-output-no-actions",
            request_id=request.request_id,
            workflow_pack_id=request.workflow_pack.workflow_pack_id,
            workflow_pack_version=request.workflow_pack.workflow_pack_version,
            explanation_text="No actions.",
            claims=(
                AIOutputClaim(
                    claim_id="claim-001",
                    claim_text="Supported by Core.",
                    source_product_ids=("lotus-core:PortfolioStateSnapshot:v1",),
                ),
            ),
            proposed_actions=(),
            verifier_ran_at_utc=VERIFIED_AT,
        )


def test_ai_result_and_output_identity_validation_fail_closed() -> None:
    request = build_ai_explanation_request(
        candidate(),
        command(AIWorkflowPurpose.UNSUPPORTED_CLAIM_VERIFICATION),
    )

    with pytest.raises(ValueError, match="fallback_reason is required"):
        fallback = deterministic_ai_fallback(
            request,
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
            occurred_at_utc=VERIFIED_AT,
        )
        AIExplanationResult(
            request=request,
            posture=AIExplanationPosture.FALLBACK_USED,
            verifier_outcome=AIVerifierOutcome.NOT_RUN,
            explanation_text="Fallback without reason.",
            reason_codes=(ReasonCode.AI_FALLBACK_USED,),
            audit_event=fallback.audit_event,
            output_integrity=fallback.output_integrity,
            execution_provenance_posture=fallback.execution_provenance_posture,
        )

    with pytest.raises(ValueError, match="fallback_reason requires fallback posture"):
        accepted = evaluate_ai_workflow_output(request, output(request.request_id))
        AIExplanationResult(
            request=request,
            posture=AIExplanationPosture.READY_FOR_ADVISOR_REVIEW,
            verifier_outcome=AIVerifierOutcome.PASSED,
            explanation_text="Ready with invalid fallback reason.",
            reason_codes=(ReasonCode.AI_VERIFIER_PASSED,),
            audit_event=accepted.audit_event,
            output_integrity=accepted.output_integrity,
            execution_provenance_posture=accepted.execution_provenance_posture,
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        )

    fallback = deterministic_ai_fallback(
        request,
        fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        occurred_at_utc=VERIFIED_AT,
    )
    accepted = evaluate_ai_workflow_output(request, output(request.request_id))
    with pytest.raises(ValueError, match="fallback result requires not-applicable"):
        replace(
            fallback,
            execution_provenance_posture=(
                AIExecutionProvenancePosture.UNATTESTED_LOCAL_TEST_FIXTURE
            ),
        )
    with pytest.raises(ValueError, match="evaluated workflow output requires"):
        replace(
            accepted,
            execution_provenance_posture=(AIExecutionProvenancePosture.NOT_APPLICABLE_FALLBACK),
        )
    with pytest.raises(ValueError, match="reason_codes is required"):
        replace(accepted, reason_codes=())

    wrong_pack = AIWorkflowOutput(
        output_id="ai-output-wrong-pack",
        request_id=request.request_id,
        workflow_pack_id="lotus-ai:different-pack",
        workflow_pack_version=request.workflow_pack.workflow_pack_version,
        explanation_text="Mismatched workflow pack.",
        claims=(
            AIOutputClaim(
                claim_id="claim-001",
                claim_text="Supported by Core.",
                source_product_ids=("lotus-core:PortfolioStateSnapshot:v1",),
            ),
        ),
        proposed_actions=(
            AIProposedAction(
                action_type=AIProposedActionType.ADVISOR_REVIEW,
                action_label="Review evidence internally",
            ),
        ),
        verifier_ran_at_utc=VERIFIED_AT,
    )

    with pytest.raises(InvalidAIWorkflowOutput, match="workflow_pack_id"):
        evaluate_ai_workflow_output(request, wrong_pack)


class ProjectionOnlyAIExplanationRepository:
    def __init__(self, repository: InMemoryIdeaRepository) -> None:
        self._repository = repository
        self.looked_up_candidate_ids: list[str] = []

    def candidate_record_by_id(self, candidate_id: str) -> Any:
        self.looked_up_candidate_ids.append(candidate_id)
        return self._repository.candidate_record_by_id(candidate_id)

    def record_ai_explanation_lineage(self, *args: Any, **kwargs: Any) -> Any:
        return self._repository.record_ai_explanation_lineage(*args, **kwargs)

    def record_ai_explanation_lineage_request(self, *args: Any, **kwargs: Any) -> Any:
        return self._repository.record_ai_explanation_lineage_request(*args, **kwargs)

    def snapshot(self) -> Any:
        raise AssertionError("AI explanation candidate lookup must not hydrate a full snapshot")
