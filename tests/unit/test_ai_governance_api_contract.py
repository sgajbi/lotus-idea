from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.ai_governance import (
    AIExplanationEvaluationRequest,
    AIOutputClaimRequest,
    AIProposedActionRequest,
    AIWorkflowOutputRequest,
    AIWorkflowPackRequest,
)
from app.api.ai_governance_models import AIApprovedMetadataRequest
from app.main import app
from app.application.ai_governance import EvaluateAIExplanationToRepositoryCommand
from app.domain import (
    AIFallbackReason,
    AIExplanationCommand,
    AIProposedActionType,
    AIWorkflowPackRef,
    AIWorkflowPurpose,
)
from app.observability import IdeaOperation, OperationEvent, OperationOutcome

_CORE_PORTFOLIO_SNAPSHOT_SOURCE = "lotus-core:PortfolioStateSnapshot:v1"
_VERIFIER_RAN_AT_UTC = datetime(2026, 6, 21, 10, 12, 30, tzinfo=UTC)


def workflow_pack() -> AIWorkflowPackRequest:
    return AIWorkflowPackRequest(
        workflowPackId="lotus-ai:idea-explanation:v1",
        workflowPackVersion="v1",
        purpose=AIWorkflowPurpose.MISSING_EVIDENCE_CHECK,
        evaluationRef="lotus-ai:governed-verifier:v1",
    )


def test_ai_workflow_pack_request_rejects_blank_identity_fields() -> None:
    with pytest.raises(ValidationError):
        AIWorkflowPackRequest(
            workflowPackId=" ",
            workflowPackVersion="v1",
            purpose=AIWorkflowPurpose.MISSING_EVIDENCE_CHECK,
            evaluationRef="lotus-ai:governed-verifier:v1",
        )


def _valid_output_claim(claim_id: str = "claim-001") -> AIOutputClaimRequest:
    return AIOutputClaimRequest(
        claimId=claim_id,
        claimText="Source-backed claim",
        sourceProductIds=(_CORE_PORTFOLIO_SNAPSHOT_SOURCE,),
    )


def _valid_proposed_action() -> AIProposedActionRequest:
    return AIProposedActionRequest(
        actionType=AIProposedActionType.ADVISOR_REVIEW,
        actionLabel="Route to advisor review",
    )


def _valid_workflow_output_request(
    *,
    output_id: str = "ai-output-001",
    claims: tuple[AIOutputClaimRequest, ...] | None = None,
    verifier_ran_at_utc: datetime = _VERIFIER_RAN_AT_UTC,
) -> AIWorkflowOutputRequest:
    return AIWorkflowOutputRequest(
        outputId=output_id,
        explanationText="Source-backed explanation",
        claims=claims if claims is not None else (_valid_output_claim(),),
        proposedActions=(_valid_proposed_action(),),
        verifierRanAtUtc=verifier_ran_at_utc,
    )


def _assert_validation_error(
    invalid_request: Callable[[], object],
    *,
    match: str | None = None,
) -> None:
    expectation = (
        pytest.raises(ValidationError, match=match)
        if match is not None
        else pytest.raises(ValidationError)
    )
    with expectation:
        invalid_request()


def _assert_ai_output_claim_rejects_unsafe_shape() -> None:
    _assert_validation_error(
        lambda: AIOutputClaimRequest(
            claimId=" ",
            claimText="Source-backed claim",
            sourceProductIds=(_CORE_PORTFOLIO_SNAPSHOT_SOURCE,),
        )
    )
    _assert_validation_error(
        lambda: AIOutputClaimRequest(
            claimId="claim-001",
            claimText="Source-backed claim",
            sourceProductIds=(),
        )
    )
    _assert_validation_error(
        lambda: AIOutputClaimRequest(
            claimId="claim-001",
            claimText="Source-backed claim",
            sourceProductIds=(" ",),
        )
    )
    _assert_validation_error(
        lambda: AIOutputClaimRequest(
            claimId="claim-001",
            claimText="Source-backed claim",
            sourceProductIds=(
                _CORE_PORTFOLIO_SNAPSHOT_SOURCE,
                _CORE_PORTFOLIO_SNAPSHOT_SOURCE,
            ),
        ),
        match="sourceProductIds must be unique",
    )


def _assert_ai_workflow_output_rejects_duplicate_claim_ids() -> None:
    duplicate_claim = _valid_output_claim("claim-duplicate")
    _assert_validation_error(
        lambda: _valid_workflow_output_request(
            output_id="ai-output-duplicate-claims",
            claims=(duplicate_claim, duplicate_claim),
        ),
        match="claimIds must be unique",
    )


def _assert_ai_proposed_action_rejects_blank_label() -> None:
    _assert_validation_error(
        lambda: AIProposedActionRequest(
            actionType=AIProposedActionType.ADVISOR_REVIEW,
            actionLabel=" ",
        )
    )


def _assert_ai_workflow_output_rejects_unsafe_shape() -> None:
    _assert_validation_error(lambda: _valid_workflow_output_request(output_id=" "))
    _assert_validation_error(lambda: _valid_workflow_output_request(claims=()))
    _assert_validation_error(
        lambda: _valid_workflow_output_request(
            verifier_ran_at_utc=datetime(2026, 6, 21, 10, 12, 30)
        )
    )


def test_ai_workflow_output_request_rejects_unsafe_shape() -> None:
    _assert_ai_output_claim_rejects_unsafe_shape()
    _assert_ai_workflow_output_rejects_duplicate_claim_ids()
    _assert_ai_proposed_action_rejects_blank_label()
    _assert_ai_workflow_output_rejects_unsafe_shape()


def test_ai_explanation_request_rejects_blank_request_id_and_naive_time() -> None:
    with pytest.raises(ValidationError):
        AIExplanationEvaluationRequest(
            requestId=" ",
            workflowPack=workflow_pack(),
            requestedAtUtc=datetime(2026, 6, 21, 10, 12, tzinfo=UTC),
        )


def test_ai_metadata_openapi_schema_is_closed_and_versioned_by_response_contract() -> None:
    with pytest.raises(ValidationError):
        AIApprovedMetadataRequest.model_validate({"customerEmail": "client@example.com"})

    schema = app.openapi()
    metadata_schema = schema["components"]["schemas"]["AIApprovedMetadataRequest"]
    assert metadata_schema["additionalProperties"] is False
    assert set(metadata_schema["properties"]) == {"channel", "audience"}
    evaluation_schema = schema["components"]["schemas"]["AIExplanationEvaluationResponse"]
    readiness_schema = schema["components"]["schemas"]["AIExplanationReadinessResponse"]
    assert "metadataEnvelopeVersion" in evaluation_schema["required"]
    assert "metadataEnvelopeVersion" in readiness_schema["required"]
    with pytest.raises(ValidationError):
        AIExplanationEvaluationRequest(
            requestId="ai-explanation-001",
            workflowPack=workflow_pack(),
            requestedAtUtc=datetime(2026, 6, 21, 10, 12),
        )


def test_ai_explanation_openapi_publishes_attestation_boundary() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate"][
        "post"
    ]

    assert "signed lotus-ai run attestation" in operation["description"]
    assert "does not call an AI provider" in operation["description"]
    request_schema = schema["components"]["schemas"]["AIExplanationEvaluationRequest"]
    assert {
        "producerRunId",
        "producerExecutionOutput",
        "runAttestation",
    } <= request_schema["properties"].keys()
    success_examples = operation["responses"]["200"]["content"]["application/json"]["examples"]
    assert set(success_examples) == {
        "unattestedLocalTestFixture",
        "verifiedAttestedOutput",
        "deterministicFallback",
        "blockedUnsupportedClaim",
        "blockedForbiddenAction",
        "blockedUnsafeActionContent",
    }
    assert (
        success_examples["unattestedLocalTestFixture"]["value"]["executionProvenancePosture"]
        == "unattested_local_test_fixture"
    )
    attested = success_examples["verifiedAttestedOutput"]["value"]
    assert attested["executionProvenancePosture"] == "lotus_ai_attestation_verified"
    assert attested["lotusAiRuntimeExecuted"] is True
    assert attested["grantsDownstreamAuthority"] is False
    assert attested["supportedFeaturePromoted"] is False
    fallback = success_examples["deterministicFallback"]["value"]
    assert fallback["posture"] == "fallback_used"
    assert fallback["executionProvenancePosture"] == "not_applicable_fallback"
    assert fallback["verifiedOutput"] is None
    assert fallback["grantsDownstreamAuthority"] is False
    blocked = success_examples["blockedUnsupportedClaim"]["value"]
    assert blocked["posture"] == "blocked_unsupported_claim"
    assert blocked["verifiedOutput"]["groundedClaims"] == []
    assert blocked["grantsDownstreamAuthority"] is False


def test_ai_explanation_application_command_rejects_blank_candidate() -> None:
    with pytest.raises(ValueError, match="candidate_id is required"):
        EvaluateAIExplanationToRepositoryCommand(
            candidate_id=" ",
            explanation=AIExplanationCommand(
                request_id="ai-explanation-001",
                actor_subject="advisor-001",
                workflow_pack=AIWorkflowPackRef(
                    workflow_pack_id="lotus-ai:idea-explanation:v1",
                    workflow_pack_version="v1",
                    purpose=AIWorkflowPurpose.MISSING_EVIDENCE_CHECK,
                    evaluation_ref="lotus-ai:governed-verifier:v1",
                ),
                approved_metadata={},
                requested_at_utc=datetime(2026, 6, 21, 10, 12, tzinfo=UTC),
            ),
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
            idempotency_key="ai-explanation:blank-candidate:001",
            idempotency_payload={
                "candidateId": " ",
                "requestId": "ai-explanation-001",
            },
        )


def test_ai_explanation_application_command_rejects_blank_idempotency_key() -> None:
    with pytest.raises(ValueError, match="idempotency_key is required"):
        EvaluateAIExplanationToRepositoryCommand(
            candidate_id="idea-ai-001",
            explanation=AIExplanationCommand(
                request_id="ai-explanation-001",
                actor_subject="advisor-001",
                workflow_pack=AIWorkflowPackRef(
                    workflow_pack_id="lotus-ai:idea-explanation:v1",
                    workflow_pack_version="v1",
                    purpose=AIWorkflowPurpose.MISSING_EVIDENCE_CHECK,
                    evaluation_ref="lotus-ai:governed-verifier:v1",
                ),
                approved_metadata={},
                requested_at_utc=datetime(2026, 6, 21, 10, 12, tzinfo=UTC),
            ),
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
            idempotency_key=" ",
            idempotency_payload={},
        )


def test_operation_event_rejects_blank_source_authority_and_error_code() -> None:
    with pytest.raises(ValueError, match="source_authority is required"):
        OperationEvent(
            operation=IdeaOperation.AI_EXPLANATION,
            outcome=OperationOutcome.FALLBACK,
            source_authority=" ",
        )
    with pytest.raises(ValueError, match="error_code cannot be blank"):
        OperationEvent(
            operation=IdeaOperation.AI_EXPLANATION,
            outcome=OperationOutcome.INVALID_REQUEST,
            error_code=" ",
        )
