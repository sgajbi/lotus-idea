from __future__ import annotations

from app.domain.control_time import (
    PRESENTATION_TIME_POLICY,
    AcceptanceTimeSource,
    ObservedTimeSkewError,
    require_observed_time_within_policy,
)
from app.domain.presentation_receipts import (
    CandidatePresentationReceipt,
    PresentationReceiptCandidateStateError,
    PresentationReceiptDecision,
    PresentationReceiptResult,
)
from app.domain.source_revision import SourceCutPosture
from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection, PostgresCursor
from app.infrastructure.postgres_slo import execute_observed_postgres_call


class PostgresPresentationReceiptRepositoryMixin:
    _connection: PostgresConnection

    def presentation_receipt_by_id(
        self,
        receipt_id: str,
        *,
        candidate_id: str,
        tenant_id: str,
    ) -> CandidatePresentationReceipt | None:
        return execute_observed_postgres_call(
            "projection_read",
            lambda: _load_receipt_by_scope(
                self._connection,
                receipt_id=receipt_id,
                candidate_id=candidate_id,
                tenant_id=tenant_id,
            ),
        )

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
            try:
                require_observed_time_within_policy(
                    receipt.presented_at_utc,
                    receipt.accepted_at_utc,
                    PRESENTATION_TIME_POLICY,
                )
            except ObservedTimeSkewError:
                existing = _load_receipt(cursor, receipt)
                if existing is not None and existing.has_same_producer_claim(receipt):
                    result = PresentationReceiptResult(
                        decision=PresentationReceiptDecision.REPLAYED,
                        receipt=existing,
                    )
                    connection.commit()
                    return result
                raise
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
                        if existing.has_same_producer_claim(receipt)
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
            candidate_evidence_version, source_revision_vector_digest, source_cut_posture,
            accepted_at_utc, acceptance_time_source,
            schema_version, surface, producer
        )
        SELECT %s, candidate_id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        FROM idea_candidate_record
        WHERE candidate_id = %s
          AND candidate_json->'access_scope'->>'tenant_id' = %s
          AND (candidate_json->'identity'->>'material_version')::INTEGER = %s
          AND (candidate_json->'identity'->>'evidence_version')::INTEGER = %s
          AND candidate_json->'evidence_packet'->>'source_revision_vector_digest' = %s
          AND candidate_json->'evidence_packet'->>'source_cut_posture' = %s
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
            receipt.source_revision_vector_digest,
            receipt.source_cut_posture.value,
            receipt.accepted_at_utc,
            receipt.acceptance_time_source.value,
            receipt.schema_version,
            receipt.surface,
            receipt.producer,
            receipt.candidate_id,
            receipt.tenant_id,
            receipt.candidate_material_version,
            receipt.candidate_evidence_version,
            receipt.source_revision_vector_digest,
            receipt.source_cut_posture.value,
            receipt.accepted_at_utc,
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
               candidate_evidence_version, source_revision_vector_digest, source_cut_posture,
               accepted_at_utc, acceptance_time_source,
               schema_version, surface, producer
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
    return _receipt_from_row(rows[0])


def _load_receipt_by_scope(
    connection: PostgresConnection,
    *,
    receipt_id: str,
    candidate_id: str,
    tenant_id: str,
) -> CandidatePresentationReceipt | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT receipt_id, candidate_id, tenant_id, presented_at_utc,
                   rank_at_presentation, visible_candidate_count, queue_snapshot_digest,
                   queue_policy_version, ranking_policy_version, candidate_material_version,
                   candidate_evidence_version, source_revision_vector_digest, source_cut_posture,
                   accepted_at_utc, acceptance_time_source,
                   schema_version, surface, producer
            FROM idea_candidate_presentation_receipt
            WHERE receipt_id = %s
              AND candidate_id = %s
              AND tenant_id = %s
            """,
            (receipt_id, candidate_id, tenant_id),
        )
        rows = cursor.fetchall()
    return _receipt_from_row(rows[0]) if rows else None


def load_presentation_receipts(
    cursor: PostgresCursor,
) -> dict[str, CandidatePresentationReceipt]:
    cursor.execute(
        """
        SELECT receipt.receipt_id, receipt.candidate_id, receipt.tenant_id,
               receipt.presented_at_utc, receipt.rank_at_presentation,
               receipt.visible_candidate_count, receipt.queue_snapshot_digest,
               receipt.queue_policy_version, receipt.ranking_policy_version,
               receipt.candidate_material_version, receipt.candidate_evidence_version,
               receipt.source_revision_vector_digest, receipt.source_cut_posture,
               receipt.accepted_at_utc, receipt.acceptance_time_source,
               receipt.schema_version, receipt.surface, receipt.producer
        FROM idea_candidate_presentation_receipt AS receipt
        LEFT JOIN idea_data_lifecycle_control AS lifecycle
          ON lifecycle.candidate_id = receipt.candidate_id
        WHERE COALESCE(lifecycle.held_from_state, lifecycle.state, 'active')
              NOT IN ('erased', 'purged')
        ORDER BY receipt.presented_at_utc, receipt.receipt_id
        """
    )
    receipts: dict[str, CandidatePresentationReceipt] = {}
    for row in cursor.fetchall():
        receipt = _receipt_from_row(row)
        receipts[receipt.receipt_id] = receipt
    return receipts


def insert_presentation_receipt_snapshot(
    cursor: PostgresCursor,
    receipt: CandidatePresentationReceipt,
) -> None:
    cursor.execute(
        """
        INSERT INTO idea_candidate_presentation_receipt (
            receipt_id, candidate_id, tenant_id, presented_at_utc,
            rank_at_presentation, visible_candidate_count, queue_snapshot_digest,
            queue_policy_version, ranking_policy_version, candidate_material_version,
            candidate_evidence_version, source_revision_vector_digest, source_cut_posture,
            accepted_at_utc, acceptance_time_source,
            schema_version, surface, producer
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            receipt.receipt_id,
            receipt.candidate_id,
            receipt.tenant_id,
            receipt.presented_at_utc,
            receipt.rank_at_presentation,
            receipt.visible_candidate_count,
            receipt.queue_snapshot_digest,
            receipt.queue_policy_version,
            receipt.ranking_policy_version,
            receipt.candidate_material_version,
            receipt.candidate_evidence_version,
            receipt.source_revision_vector_digest,
            receipt.source_cut_posture.value,
            receipt.accepted_at_utc,
            receipt.acceptance_time_source.value,
            receipt.schema_version,
            receipt.surface,
            receipt.producer,
        ),
    )


def _receipt_from_row(row: object) -> CandidatePresentationReceipt:
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
        source_revision_vector_digest=str(
            read_row_value(row, "source_revision_vector_digest")
        ),
        source_cut_posture=SourceCutPosture(read_row_value(row, "source_cut_posture")),
        accepted_at_utc=read_row_value(row, "accepted_at_utc"),
        acceptance_time_source=AcceptanceTimeSource(read_row_value(row, "acceptance_time_source")),
        schema_version=str(read_row_value(row, "schema_version")),
        surface=str(read_row_value(row, "surface")),
        producer=str(read_row_value(row, "producer")),
    )


__all__ = [
    "PostgresPresentationReceiptRepositoryMixin",
    "insert_presentation_receipt_snapshot",
    "load_presentation_receipts",
]
