from __future__ import annotations

from app.domain.presentation_receipts import (
    CandidatePresentationReceipt,
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
    PresentationReceiptResult,
)
from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor
from app.infrastructure.postgres_slo import execute_observed_postgres_call


class PostgresPresentationReceiptRepositoryMixin:
    _connection: PostgresConnection

    def record_presentation_receipt(
        self,
        receipt: CandidatePresentationReceipt,
    ) -> PresentationReceiptResult:
        return execute_observed_postgres_call(
            "mutation",
            lambda: _record_presentation_receipt(self._connection, receipt),
        )


def _record_presentation_receipt(
    connection: PostgresConnection,
    receipt: CandidatePresentationReceipt,
) -> PresentationReceiptResult:
    try:
        with connection.cursor() as cursor:
            inserted = _insert_receipt(cursor, receipt)
            if inserted:
                result = PresentationReceiptResult(
                    decision=PresentationReceiptDecision.ACCEPTED,
                    receipt=receipt,
                )
            else:
                existing = _load_receipt(cursor, receipt)
                if existing is None:
                    raise PresentationReceiptCandidateStateError(
                        "candidate does not match the referenced tenant and version"
                    )
                result = PresentationReceiptResult(
                    decision=(
                        PresentationReceiptDecision.REPLAYED
                        if existing == receipt
                        else PresentationReceiptDecision.CONFLICT
                    ),
                    receipt=existing,
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return result


def _insert_receipt(
    cursor: PostgresCursor,
    receipt: CandidatePresentationReceipt,
) -> bool:
    cursor.execute(
        """
        INSERT INTO idea_candidate_presentation_receipt (
            receipt_id, candidate_id, tenant_id, presented_at_utc,
            rank_at_presentation, visible_candidate_count, queue_snapshot_digest,
            queue_policy_version, ranking_policy_version, candidate_material_version,
            candidate_evidence_version, schema_version, surface, producer
        )
        SELECT %s, candidate_id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        FROM idea_candidate_record
        WHERE candidate_id = %s
          AND candidate_json->'access_scope'->>'tenant_id' = %s
          AND (candidate_json->'identity'->>'material_version')::INTEGER = %s
          AND (candidate_json->'identity'->>'evidence_version')::INTEGER = %s
          AND updated_at_utc <= %s
        ON CONFLICT (receipt_id) DO NOTHING
        RETURNING receipt_id
        """,
        (
            receipt.receipt_id,
            receipt.tenant_id,
            receipt.presented_at_utc,
            receipt.rank_at_presentation,
            receipt.visible_candidate_count,
            receipt.queue_snapshot_digest,
            receipt.queue_policy_version,
            receipt.ranking_policy_version,
            receipt.candidate_material_version,
            receipt.candidate_evidence_version,
            receipt.schema_version,
            receipt.surface,
            receipt.producer,
            receipt.candidate_id,
            receipt.tenant_id,
            receipt.candidate_material_version,
            receipt.candidate_evidence_version,
            receipt.presented_at_utc,
        ),
    )
    return bool(cursor.fetchall())


def _load_receipt(
    cursor: PostgresCursor,
    receipt: CandidatePresentationReceipt,
) -> CandidatePresentationReceipt | None:
    cursor.execute(
        """
        SELECT receipt_id, candidate_id, tenant_id, presented_at_utc,
               rank_at_presentation, visible_candidate_count, queue_snapshot_digest,
               queue_policy_version, ranking_policy_version, candidate_material_version,
               candidate_evidence_version, schema_version, surface, producer
        FROM idea_candidate_presentation_receipt
        WHERE receipt_id = %s
          AND candidate_id = %s
          AND tenant_id = %s
        """,
        (receipt.receipt_id, receipt.candidate_id, receipt.tenant_id),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    row = rows[0]
    return CandidatePresentationReceipt(
        receipt_id=str(read_row_value(row, "receipt_id")),
        candidate_id=str(read_row_value(row, "candidate_id")),
        tenant_id=str(read_row_value(row, "tenant_id")),
        presented_at_utc=read_row_value(row, "presented_at_utc"),
        rank_at_presentation=int(read_row_value(row, "rank_at_presentation")),
        visible_candidate_count=int(read_row_value(row, "visible_candidate_count")),
        queue_snapshot_digest=str(read_row_value(row, "queue_snapshot_digest")),
        queue_policy_version=str(read_row_value(row, "queue_policy_version")),
        ranking_policy_version=str(read_row_value(row, "ranking_policy_version")),
        candidate_material_version=int(read_row_value(row, "candidate_material_version")),
        candidate_evidence_version=int(read_row_value(row, "candidate_evidence_version")),
        schema_version=str(read_row_value(row, "schema_version")),
        surface=str(read_row_value(row, "surface")),
        producer=str(read_row_value(row, "producer")),
    )


__all__ = ["PostgresPresentationReceiptRepositoryMixin"]
