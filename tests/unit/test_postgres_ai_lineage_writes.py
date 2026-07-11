from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from app.domain.ai_lineage_persistence import AIExplanationLineageRecord
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.postgres_ai_lineage_writes import insert_ai_explanation_lineage_records
from tests.unit.test_postgres_repository import high_cash_candidate


def test_insert_ai_explanation_lineage_records_writes_each_lineage_record() -> None:
    candidate = high_cash_candidate()
    record = CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash="sha256:lineage-candidate",
        persisted_at_utc=candidate.created_at_utc,
        ai_explanation_lineage_records=(_lineage_record(candidate.candidate_id),),
    )
    cursor = RecordingCursor()

    insert_ai_explanation_lineage_records(cursor, record)

    assert len(cursor.executions) == 1
    query, params = cursor.executions[0]
    assert params is not None
    assert "INSERT INTO idea_ai_explanation_lineage" in query
    assert params[0] == "ai-request-001"
    assert params[1] == candidate.candidate_id
    assert params[11] == "lotus-idea.ai-output-integrity.v1"
    assert params[12] == f"sha256:{'1' * 64}"
    assert params[14] == "not_applicable_fallback"


def _lineage_record(candidate_id: str) -> AIExplanationLineageRecord:
    evaluated_at = datetime(2026, 6, 21, 10, 15, tzinfo=UTC)
    return AIExplanationLineageRecord(
        request_id="ai-request-001",
        candidate_id=candidate_id,
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
        requested_at_utc=evaluated_at,
        evaluated_at_utc=evaluated_at,
        grants_downstream_authority=False,
        lineage_hash=f"sha256:{'2' * 64}",
    )


class RecordingCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, Sequence[Any] | None]] = []

    def execute(self, query: str, params: Sequence[Any] | None = None) -> None:
        self.executions.append((query, params))

    def fetchall(self) -> Sequence[Any]:
        return []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None
