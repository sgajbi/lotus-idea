from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.application.ai_governance import (
    AIExplanationEvaluationDecision,
    EvaluateAIExplanationToRepositoryCommand,
    evaluate_ai_explanation_to_repository,
)
from app.application.lotus_ai_idea_explanation_request import (
    build_lotus_ai_idea_explanation_input,
)
from app.domain.ai_execution_provenance import (
    AIExecutionProvenancePosture,
    AIWorkflowProvenanceRejectionReason,
    UntrustedAIWorkflowOutput,
)
from app.domain.ai_governance import (
    AIExplanationCommand,
    AIFallbackReason,
    build_ai_explanation_request,
)
from app.domain.lotus_ai_execution_digest import (
    LotusAIExecutionOutputContent,
    lotus_ai_input_evidence_sha256,
    lotus_ai_output_content_sha256,
)
from app.domain.lotus_ai_run_attestation import (
    LotusAIAttestationKeyDiscovery,
    LotusAIAttestationPublicKey,
    LotusAIRunAttestationClaims,
    LotusAIRunAttestationEnvelope,
    LotusAIRunAttestationSignature,
)
from app.domain.persistence import InMemoryIdeaRepository
from tests.unit.test_ai_governance import command
from tests.unit.test_idea_persistence import EVALUATED_AT, high_cash_candidate


VERIFIED_AT = datetime(2026, 7, 11, 10, 5, tzinfo=UTC)
CALLER_TENANT_IDS = ("tenant-sg-001",)


def test_attested_application_path_verifies_maps_and_persists_receipt() -> None:
    repository, explanation_command, candidate_id = _repository_and_command()
    execution_output = _execution_output()
    envelope = _attestation(
        repository=repository,
        candidate_id=candidate_id,
        explanation_command=explanation_command,
        execution_output=execution_output,
    )
    signature_verifier = RecordingSignatureVerifier()

    result = evaluate_ai_explanation_to_repository(
        EvaluateAIExplanationToRepositoryCommand(
            candidate_id=candidate_id,
            explanation=explanation_command,
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
            idempotency_key="attested-explanation-001",
            idempotency_payload={"request_id": explanation_command.request_id},
            producer_run_id=envelope.claims.run_id,
            producer_execution_output=execution_output,
            run_attestation=envelope,
            caller_tenant_ids=CALLER_TENANT_IDS,
        ),
        repository=repository,
        attestation_key_source=StaticKeySource(),
        signature_verifier=signature_verifier,
        verification_clock=lambda: VERIFIED_AT,
    )

    assert result.decision is AIExplanationEvaluationDecision.ACCEPTED
    assert result.explanation_result is not None
    assert result.explanation_result.execution_provenance_posture is (
        AIExecutionProvenancePosture.LOTUS_AI_ATTESTATION_VERIFIED
    )
    assert result.explanation_result.fallback_used is False
    assert signature_verifier.call_count == 1
    assert result.lineage_persistence_result is not None
    lineage = result.lineage_persistence_result.lineage_record
    assert lineage is not None
    assert lineage.attestation_receipt is not None
    assert lineage.attestation_receipt.run_id == envelope.claims.run_id


def test_attested_application_path_fails_before_write_when_keys_are_unavailable() -> None:
    repository, explanation_command, candidate_id = _repository_and_command()
    execution_output = _execution_output()
    envelope = _attestation(
        repository=repository,
        candidate_id=candidate_id,
        explanation_command=explanation_command,
        execution_output=execution_output,
    )

    with pytest.raises(UntrustedAIWorkflowOutput, match="verification failed") as raised:
        evaluate_ai_explanation_to_repository(
            EvaluateAIExplanationToRepositoryCommand(
                candidate_id=candidate_id,
                explanation=explanation_command,
                fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
                idempotency_key="attested-explanation-001",
                idempotency_payload={"request_id": explanation_command.request_id},
                producer_run_id=envelope.claims.run_id,
                producer_execution_output=execution_output,
                run_attestation=envelope,
                caller_tenant_ids=CALLER_TENANT_IDS,
            ),
            repository=repository,
            attestation_key_source=UnavailableKeySource(),
            signature_verifier=RecordingSignatureVerifier(),
            verification_clock=lambda: VERIFIED_AT,
        )

    assert raised.value.reason is (
        AIWorkflowProvenanceRejectionReason.ATTESTATION_VERIFICATION_FAILED
    )
    persisted = repository.snapshot().candidate_records[candidate_id]
    assert persisted.ai_explanation_lineage_records == ()


def test_attested_command_classifies_incomplete_bundle_before_repository_access() -> None:
    _, explanation_command, candidate_id = _repository_and_command()

    with pytest.raises(UntrustedAIWorkflowOutput) as raised:
        EvaluateAIExplanationToRepositoryCommand(
            candidate_id=candidate_id,
            explanation=explanation_command,
            fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
            idempotency_key="attested-explanation-incomplete-001",
            idempotency_payload={"request_id": explanation_command.request_id},
            producer_run_id="packrun_idea_explanation_request-001",
        )

    assert raised.value.reason is (
        AIWorkflowProvenanceRejectionReason.INCOMPLETE_ATTESTATION_BUNDLE
    )


def _repository_and_command() -> tuple[InMemoryIdeaRepository, AIExplanationCommand, str]:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:attested-ai:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    explanation_command = replace(command(), request_id="request-001")
    return repository, explanation_command, persisted.record.candidate.candidate_id


def _execution_output() -> LotusAIExecutionOutputContent:
    message = "The evidence supports an internal advisor review of idle cash."
    return LotusAIExecutionOutputContent(
        status="COMPLETED",
        output_label="EXPLANATION_ONLY",
        message=message,
        structured_output={
            "idea_workflow_output": {
                "output_id": "output-001",
                "explanation_text": message,
                "claims": [
                    {
                        "claim_id": "claim-001",
                        "claim_text": "Cash attention is supported by Core portfolio state.",
                        "source_product_ids": ["lotus-core:PortfolioStateSnapshot:v1"],
                    }
                ],
                "proposed_actions": [
                    {
                        "action_type": "advisor_review",
                        "action_label": "Review evidence internally",
                    }
                ],
            }
        },
    )


def _attestation(
    *,
    repository: InMemoryIdeaRepository,
    candidate_id: str,
    explanation_command: AIExplanationCommand,
    execution_output: LotusAIExecutionOutputContent,
) -> LotusAIRunAttestationEnvelope:
    candidate_record = repository.snapshot().candidate_records[candidate_id]
    request = build_ai_explanation_request(candidate_record.candidate, explanation_command)
    claims = LotusAIRunAttestationClaims(
        schema_version="lotus-ai.workflow-run-attestation.v1",
        issuer="lotus-ai",
        audience="lotus-idea",
        run_id="packrun_idea_explanation_request-001",
        consumer_request_id=request.request_id,
        replay_nonce="a" * 64,
        workflow_pack_id="idea_explanation.pack",
        workflow_pack_version="v1",
        registration_ref="idea_explanation.pack@v1",
        evaluator_id="idea-explanation-guardrails",
        evaluator_policy_version="idea-explanation-policy.v1",
        provider_id="text.openai",
        provider_mode="openai",
        model_id="gpt-5.4",
        model_version="2026-06-01",
        model_risk_status="approved",
        model_risk_approval_ref="model-risk://lotus-ai/gpt-5.4/2026-06-01",
        input_evidence_sha256=lotus_ai_input_evidence_sha256(
            build_lotus_ai_idea_explanation_input(request)
        ),
        output_content_sha256=lotus_ai_output_content_sha256(execution_output),
        issued_at_utc=VERIFIED_AT - timedelta(seconds=5),
        execution_started_at_utc=VERIFIED_AT - timedelta(seconds=10),
        execution_completed_at_utc=VERIFIED_AT - timedelta(seconds=6),
        expires_at_utc=VERIFIED_AT + timedelta(minutes=5),
        stubbed=False,
        supportability_status="READY",
    )
    return LotusAIRunAttestationEnvelope(
        claims=claims,
        signature=LotusAIRunAttestationSignature(
            algorithm="EdDSA",
            key_id="attestation-key-1",
            rotation_epoch=1,
            signature_base64url="c2lnbmF0dXJl",
        ),
        key_discovery_path="/.well-known/lotus-ai-workflow-attestation-keys",
        canonical_claims=_canonical_claims(claims),
    )


def _canonical_claims(claims: LotusAIRunAttestationClaims) -> dict[str, object]:
    return {
        "schema_version": claims.schema_version,
        "issuer": claims.issuer,
        "audience": claims.audience,
        "run_id": claims.run_id,
        "consumer_request_id": claims.consumer_request_id,
        "replay_nonce": claims.replay_nonce,
        "workflow_pack_id": claims.workflow_pack_id,
        "workflow_pack_version": claims.workflow_pack_version,
        "registration_ref": claims.registration_ref,
        "evaluator_id": claims.evaluator_id,
        "evaluator_policy_version": claims.evaluator_policy_version,
        "provider_id": claims.provider_id,
        "provider_mode": claims.provider_mode,
        "model_id": claims.model_id,
        "model_version": claims.model_version,
        "model_risk_status": claims.model_risk_status,
        "model_risk_approval_ref": claims.model_risk_approval_ref,
        "input_evidence_sha256": claims.input_evidence_sha256,
        "output_content_sha256": claims.output_content_sha256,
        "issued_at_utc": claims.issued_at_utc.isoformat().replace("+00:00", "Z"),
        "execution_started_at_utc": claims.execution_started_at_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "execution_completed_at_utc": claims.execution_completed_at_utc.isoformat().replace(
            "+00:00", "Z"
        ),
        "expires_at_utc": claims.expires_at_utc.isoformat().replace("+00:00", "Z"),
        "stubbed": claims.stubbed,
        "supportability_status": claims.supportability_status,
    }


class StaticKeySource:
    def get_key_discovery(self) -> LotusAIAttestationKeyDiscovery:
        return LotusAIAttestationKeyDiscovery(
            schema_version="lotus-ai.workflow-run-attestation-keys.v1",
            issuer="lotus-ai",
            keys=(
                LotusAIAttestationPublicKey(
                    key_id="attestation-key-1",
                    algorithm="EdDSA",
                    curve="Ed25519",
                    public_key_base64url="cHVibGljLWtleQ",
                    rotation_epoch=1,
                    status="active",
                    not_before_utc=VERIFIED_AT - timedelta(days=1),
                    not_after_utc=VERIFIED_AT + timedelta(days=1),
                ),
            ),
        )


class UnavailableKeySource:
    def get_key_discovery(self) -> LotusAIAttestationKeyDiscovery:
        raise RuntimeError("key service unavailable")


class RecordingSignatureVerifier:
    def __init__(self) -> None:
        self.call_count = 0

    def verify(
        self,
        *,
        public_key_base64url: str,
        signature_base64url: str,
        canonical_payload: bytes,
    ) -> None:
        assert public_key_base64url
        assert signature_base64url
        assert canonical_payload
        self.call_count += 1
