from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.api.ai_governance_models import AIExplanationEvaluationResponse


AI_EXPLANATION_SUCCESS_EXAMPLE_SUMMARIES = {
    "unattestedLocalTestFixture": "Explicit non-production local/test workflow fixture",
    "verifiedAttestedOutput": "Production-like output with verified Lotus AI run attestation",
    "deterministicFallback": "Deterministic fallback without AI runtime execution",
    "blockedUnsupportedClaim": "Workflow output blocked for an unsupported evidence claim",
    "blockedForbiddenAction": "Workflow output blocked for a forbidden action type",
    "blockedUnsafeActionContent": "Workflow output blocked for unsafe action content",
}
AI_EXPLANATION_OPERATION_PATH = "/api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate"


def build_ai_explanation_evaluation_examples() -> dict[str, dict[str, Any]]:
    local_fixture = _validated_response(_local_fixture_payload())

    verified_attested = deepcopy(local_fixture)
    verified_attested.update(
        {
            "requestId": "attested-api-request-001",
            "executionProvenancePosture": "lotus_ai_attestation_verified",
            "providerRetentionConfirmationRecorded": True,
            "durableStorageBacked": True,
            "lotusAiRuntimeExecuted": True,
        }
    )

    deterministic_fallback = deepcopy(local_fixture)
    deterministic_fallback.update(
        {
            "requestId": "ai-explanation-fallback-001",
            "posture": "fallback_used",
            "verifierOutcome": "not_run",
            "explanationText": (
                "AI explanation is unavailable. Use deterministic evidence: high_cash, "
                "supportability ready, reason codes high_cash_ratio, review_required."
            ),
            "reasonCodes": ["ai_fallback_used"],
            "fallbackUsed": True,
            "fallbackReason": "ai_unavailable",
            "outputContentDigest": f"sha256:{'b' * 64}",
            "executionProvenancePosture": "not_applicable_fallback",
            "verifiedOutput": None,
        }
    )
    deterministic_fallback["workflowPack"]["purpose"] = "missing_evidence_check"

    blocked_unsupported_claim = _blocked_example(
        local_fixture,
        request_id="ai-explanation-blocked-unsupported-claim-001",
        posture="blocked_unsupported_claim",
        verifier_outcome="failed_unsupported_claim",
        explanation_text=(
            "AI explanation was blocked because one or more claims lacked approved "
            "evidence bindings."
        ),
        reason_code="ai_unsupported_claim_blocked",
        output_digest_character="c",
        proposed_action_types=["advisor_review"],
    )
    blocked_forbidden_action = _blocked_example(
        local_fixture,
        request_id="ai-explanation-blocked-forbidden-action-001",
        posture="blocked_forbidden_action",
        verifier_outcome="failed_forbidden_action",
        explanation_text=(
            "AI explanation was blocked because it proposed an action outside the "
            "Idea authority boundary."
        ),
        reason_code="ai_forbidden_action_blocked",
        output_digest_character="d",
        proposed_action_types=["final_investment_recommendation"],
    )
    blocked_unsafe_action_content = _blocked_example(
        local_fixture,
        request_id="ai-explanation-blocked-action-content-001",
        posture="blocked_forbidden_action",
        verifier_outcome="failed_action_content",
        explanation_text=(
            "AI explanation was blocked because proposed action content violated "
            "the governed action policy."
        ),
        reason_code="ai_action_content_blocked",
        output_digest_character="e",
        proposed_action_types=["advisor_review"],
    )

    return {
        "unattestedLocalTestFixture": local_fixture,
        "verifiedAttestedOutput": _validated_response(verified_attested),
        "deterministicFallback": _validated_response(deterministic_fallback),
        "blockedUnsupportedClaim": blocked_unsupported_claim,
        "blockedForbiddenAction": blocked_forbidden_action,
        "blockedUnsafeActionContent": blocked_unsafe_action_content,
    }


def build_ai_explanation_openapi_examples() -> dict[str, dict[str, Any]]:
    examples = build_ai_explanation_evaluation_examples()
    return {
        name: {
            "summary": AI_EXPLANATION_SUCCESS_EXAMPLE_SUMMARIES[name],
            "value": value,
        }
        for name, value in examples.items()
    }


def apply_ai_explanation_openapi_examples(
    openapi_schema: dict[str, Any],
) -> dict[str, Any]:
    operation = openapi_schema["paths"][AI_EXPLANATION_OPERATION_PATH]["post"]
    operation["responses"]["200"]["content"]["application/json"]["examples"] = (
        build_ai_explanation_openapi_examples()
    )
    return openapi_schema


def _blocked_example(
    local_fixture: dict[str, Any],
    *,
    request_id: str,
    posture: str,
    verifier_outcome: str,
    explanation_text: str,
    reason_code: str,
    output_digest_character: str,
    proposed_action_types: list[str],
) -> dict[str, Any]:
    payload = deepcopy(local_fixture)
    payload.update(
        {
            "requestId": request_id,
            "posture": posture,
            "verifierOutcome": verifier_outcome,
            "explanationText": explanation_text,
            "reasonCodes": [reason_code],
            "outputContentDigest": f"sha256:{output_digest_character * 64}",
        }
    )
    payload["verifiedOutput"]["groundedClaims"] = []
    payload["verifiedOutput"]["proposedActionTypes"] = proposed_action_types
    return _validated_response(payload)


def _validated_response(payload: dict[str, Any]) -> dict[str, Any]:
    return AIExplanationEvaluationResponse.model_validate(payload).model_dump(
        mode="json",
        by_alias=True,
    )


def _local_fixture_payload() -> dict[str, Any]:
    return {
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
        "explanationText": "Cash weight is above idle-liquidity policy threshold.",
        "reasonCodes": ["ai_verifier_passed"],
        "fallbackUsed": False,
        "fallbackReason": None,
        "grantsDownstreamAuthority": False,
        "auditEventType": "idea.ai_explanation.evaluated",
        "outputIntegrityVersion": "lotus-idea.ai-output-integrity.v1",
        "outputContentDigest": f"sha256:{'a' * 64}",
        "executionProvenancePosture": "unattested_local_test_fixture",
        "executionProvenancePolicyVersion": ("lotus-idea.ai-execution-provenance-policy.v1"),
        "metadataEnvelopeVersion": "lotus-idea.ai-metadata-envelope.v1",
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
            "actionPolicyVersion": "lotus-idea.ai-action-content-policy.v1",
            "claimGroundingPolicyVersion": "lotus-idea.ai-claim-grounding-policy.v1",
            "groundedClaims": [
                {
                    "claimId": "claim-001",
                    "claimText": "Cash weight is above idle-liquidity policy threshold.",
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
                }
            ],
        },
        "approvedMetadataKeys": ["channel"],
        "aiLineageRecorded": True,
        "aiLineagePersistenceDecision": "accepted",
        "providerRetentionConfirmationRecorded": False,
        "durableStorageBacked": False,
        "lotusAiRuntimeExecuted": False,
        "supportedFeaturePromoted": False,
    }


__all__ = [
    "AI_EXPLANATION_OPERATION_PATH",
    "AI_EXPLANATION_SUCCESS_EXAMPLE_SUMMARIES",
    "apply_ai_explanation_openapi_examples",
    "build_ai_explanation_evaluation_examples",
    "build_ai_explanation_openapi_examples",
]
