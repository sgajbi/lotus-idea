from __future__ import annotations

from psycopg.types.json import Jsonb

from app.domain.ai_lineage_persistence import AIExplanationLineageRecord
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.postgres_codecs import ai_explanation_lineage_to_json
from app.infrastructure.postgres_protocols import PostgresCursor


def insert_ai_explanation_lineage_records(
    cursor: PostgresCursor,
    record: CandidatePersistenceRecord,
) -> None:
    candidate_id = record.candidate.candidate_id
    for lineage_record in record.ai_explanation_lineage_records:
        insert_ai_explanation_lineage_record(cursor, candidate_id, lineage_record)


def insert_ai_explanation_lineage_record(
    cursor: PostgresCursor,
    candidate_id: str,
    lineage_record: AIExplanationLineageRecord,
) -> None:
    cursor.execute(
        """
        INSERT INTO idea_ai_explanation_lineage (
            ai_explanation_request_id, candidate_id, evidence_packet_id,
            evidence_content_hash, workflow_pack_id, workflow_pack_version,
            purpose, posture, verifier_outcome, fallback_used, fallback_reason,
            lineage_hash, lineage_json, requested_at_utc, evaluated_at_utc
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            lineage_record.request_id,
            candidate_id,
            lineage_record.evidence_packet_id,
            lineage_record.evidence_content_hash,
            lineage_record.workflow_pack_id,
            lineage_record.workflow_pack_version,
            lineage_record.purpose,
            lineage_record.posture,
            lineage_record.verifier_outcome,
            lineage_record.fallback_used,
            lineage_record.fallback_reason,
            lineage_record.lineage_hash,
            Jsonb(ai_explanation_lineage_to_json(lineage_record)),
            lineage_record.requested_at_utc,
            lineage_record.evaluated_at_utc,
        ),
    )
