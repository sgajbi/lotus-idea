from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.domain.ai_execution_provenance import AIExecutionProvenancePosture
from app.domain.ai_governance import (
    AIExplanationResult,
    build_ai_explanation_request,
    evaluate_ai_workflow_output,
)
from app.domain.ideas import IdeaCandidate
from app.domain.ai_lineage_persistence import AIExplanationLineagePersistenceDecision
from app.domain.lotus_ai_run_attestation import VerifiedLotusAIRunAttestationReceipt
from app.domain.persistence import InMemoryIdeaRepository
from tests.unit.test_ai_governance import command, output
from tests.unit.test_idea_persistence import EVALUATED_AT, high_cash_candidate


def test_repository_accepts_then_replays_identical_verified_receipt() -> None:
    repository, candidate = _repository_with_candidate()
    result = _verified_result(candidate, request_id="request-001")
    receipt = _receipt(request_id="request-001")

    accepted = repository.record_ai_explanation_lineage(result, attestation_receipt=receipt)
    replayed = repository.record_ai_explanation_lineage(result, attestation_receipt=receipt)

    assert accepted.decision is AIExplanationLineagePersistenceDecision.ACCEPTED
    assert replayed.decision is AIExplanationLineagePersistenceDecision.REPLAYED
    assert replayed.lineage_record is not None
    assert replayed.lineage_record.attestation_receipt == receipt


def test_repository_rejects_run_or_nonce_reuse_for_another_request_after_recovery() -> None:
    repository, candidate = _repository_with_candidate()
    first_result = _verified_result(candidate, request_id="request-001")
    first_receipt = _receipt(request_id="request-001")
    accepted = repository.record_ai_explanation_lineage(
        first_result, attestation_receipt=first_receipt
    )
    assert accepted.decision is AIExplanationLineagePersistenceDecision.ACCEPTED
    recovered = InMemoryIdeaRepository(repository.snapshot())
    second_result = _verified_result(candidate, request_id="request-002")

    reused_run = recovered.record_ai_explanation_lineage(
        second_result,
        attestation_receipt=replace(
            first_receipt,
            consumer_request_id="request-002",
            replay_nonce="b" * 64,
        ),
    )
    reused_nonce = recovered.record_ai_explanation_lineage(
        second_result,
        attestation_receipt=replace(
            first_receipt,
            run_id="packrun_idea_explanation_request-002",
            consumer_request_id="request-002",
        ),
    )

    assert reused_run.decision is AIExplanationLineagePersistenceDecision.CONFLICT
    assert reused_nonce.decision is AIExplanationLineagePersistenceDecision.CONFLICT


def test_lineage_builder_rejects_receipt_for_different_consumer_request() -> None:
    repository, candidate = _repository_with_candidate()
    result = _verified_result(candidate, request_id="request-001")

    try:
        repository.record_ai_explanation_lineage(
            result,
            attestation_receipt=_receipt(request_id="request-002"),
        )
    except ValueError as exc:
        assert "receipt request does not match" in str(exc)
    else:
        raise AssertionError("expected mismatched receipt request to fail")


def _repository_with_candidate() -> tuple[InMemoryIdeaRepository, IdeaCandidate]:
    candidate, refs = high_cash_candidate()
    repository = InMemoryIdeaRepository()
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="signal-ingestion:attestation-replay:001",
        payload={"source_hashes": [source_ref.content_hash for source_ref in refs]},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.record is not None
    return repository, persisted.record.candidate


def _verified_result(candidate: IdeaCandidate, *, request_id: str) -> AIExplanationResult:
    request = build_ai_explanation_request(
        candidate,
        replace(command(), request_id=request_id),
    )
    return replace(
        evaluate_ai_workflow_output(request, output(request_id)),
        execution_provenance_posture=AIExecutionProvenancePosture.LOTUS_AI_ATTESTATION_VERIFIED,
    )


def _receipt(*, request_id: str) -> VerifiedLotusAIRunAttestationReceipt:
    verified_at = datetime(2026, 7, 11, 10, 5, tzinfo=UTC)
    return VerifiedLotusAIRunAttestationReceipt(
        run_id="packrun_idea_explanation_request-001",
        consumer_request_id=request_id,
        replay_nonce="a" * 64,
        key_id="attestation-key-1",
        rotation_epoch=1,
        provider_id="text.openai",
        provider_mode="openai",
        model_id="gpt-5.4",
        model_version="2026-06-01",
        model_risk_approval_ref="model-risk://lotus-ai/gpt-5.4/2026-06-01",
        evaluator_id="idea-explanation-guardrails",
        evaluator_policy_version="idea-explanation-policy.v1",
        input_evidence_sha256="b" * 64,
        output_content_sha256="c" * 64,
        issued_at_utc=verified_at - timedelta(seconds=5),
        expires_at_utc=verified_at + timedelta(minutes=5),
        verified_at_utc=verified_at,
    )
