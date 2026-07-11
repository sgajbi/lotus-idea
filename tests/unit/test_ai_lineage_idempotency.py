from __future__ import annotations

from dataclasses import dataclass

from app.domain.ai_lineage_idempotency import (
    ai_explanation_lineage_by_request_id,
    record_ai_explanation_lineage_request_with_idempotency,
)
from app.domain.ai_lineage_persistence import (
    AIExplanationLineagePersistenceDecision,
    AIExplanationLineagePersistenceResult,
    AIExplanationLineageRecord,
)
from app.domain.ai_governance import AIFallbackReason, AIExplanationResult
from app.domain.idempotency import IdempotencyRecord
from app.domain.persistence import CandidatePersistenceRecord
from tests.unit.test_ai_governance import EVALUATED_AT, candidate, command
from app.domain import build_ai_explanation_request, deterministic_ai_fallback


def test_ai_lineage_request_idempotency_returns_conflict_without_recording_lineage() -> None:
    idempotency_records = {
        "ai-lineage-key": IdempotencyRecord(
            key="ai-lineage-key",
            payload_hash="different-payload-hash",
        )
    }
    persisted_record = _candidate_record()
    record_calls = 0

    def record_lineage(result: AIExplanationResult) -> AIExplanationLineagePersistenceResult:
        nonlocal record_calls
        del result
        record_calls += 1
        raise AssertionError("conflict must not record lineage")

    result = record_ai_explanation_lineage_request_with_idempotency(
        _ai_result(),
        idempotency_key="ai-lineage-key",
        payload={"requestId": "changed"},
        idempotency_records=idempotency_records,
        idempotency_candidates={},
        record_for_idempotency_key=lambda key: persisted_record,
        record_lineage=record_lineage,
    )

    assert result.decision is AIExplanationLineagePersistenceDecision.CONFLICT
    assert result.record == persisted_record
    assert result.lineage_record is None
    assert record_calls == 0


def test_ai_lineage_request_idempotency_rejects_blank_key() -> None:
    result = _ai_result()

    try:
        record_ai_explanation_lineage_request_with_idempotency(
            result,
            idempotency_key=" ",
            payload={"requestId": "ai-request-001"},
            idempotency_records={},
            idempotency_candidates={},
            record_for_idempotency_key=lambda key: {"key": key},
            record_lineage=lambda lineage_result: AIExplanationLineagePersistenceResult(
                decision=AIExplanationLineagePersistenceDecision.ACCEPTED,
                record=None,
            ),
        )
    except ValueError as exc:
        assert str(exc) == "idempotency_key is required"
    else:
        raise AssertionError("blank AI lineage idempotency keys must fail closed")


def test_ai_lineage_lookup_returns_none_when_request_id_is_absent() -> None:
    carrier = LineageCarrier(
        ai_explanation_lineage_records=(
            AIExplanationLineageRecord(
                request_id="ai-request-present",
                candidate_id="idea-ai-001",
                evidence_packet_id="iep-ai-001",
                evidence_content_hash="sha256:evidence",
                workflow_pack_id="lotus-ai:idea-explanation:v1",
                workflow_pack_version="v1",
                purpose="advisor_review",
                posture="fallback_used",
                verifier_outcome="fallback",
                fallback_used=True,
                fallback_reason="ai_unavailable",
                reason_codes=("ai_unavailable",),
                output_id=None,
                claim_ids=(),
                proposed_action_types=(),
                action_policy_version="lotus-idea.ai-action-content-policy.v1",
                output_integrity_version="lotus-idea.ai-output-integrity.v1",
                output_content_digest=f"sha256:{'1' * 64}",
                execution_provenance_posture="not_applicable_fallback",
                actor_subject="advisor-001",
                requested_at_utc=EVALUATED_AT,
                evaluated_at_utc=EVALUATED_AT,
                grants_downstream_authority=False,
                lineage_hash=f"sha256:{'2' * 64}",
            ),
        )
    )

    assert ai_explanation_lineage_by_request_id(carrier, "missing") is None


@dataclass(frozen=True)
class LineageCarrier:
    ai_explanation_lineage_records: tuple[AIExplanationLineageRecord, ...]


def _ai_result() -> AIExplanationResult:
    request = build_ai_explanation_request(candidate(), command())
    return deterministic_ai_fallback(
        request,
        fallback_reason=AIFallbackReason.AI_UNAVAILABLE,
        occurred_at_utc=EVALUATED_AT,
    )


def _candidate_record() -> CandidatePersistenceRecord:
    candidate_record = candidate()
    return CandidatePersistenceRecord(
        candidate=candidate_record,
        evidence_hash="sha256:ai-lineage-candidate",
        persisted_at_utc=EVALUATED_AT,
    )
