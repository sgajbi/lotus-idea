from __future__ import annotations

from typing import Any, Mapping

from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.ideas import EvidenceSupportability, IdeaLifecycleStatus, ReviewPosture
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.postgres_codecs import (
    idea_candidate_from_json,
    read_json_object,
    read_row_value,
)
from app.infrastructure.postgres_protocols import PostgresConnection
from app.ports.idea_repository import ReviewQueueRepositoryPage


REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS = (
    "tenant_id",
    "book_id",
    "portfolio_id",
    "client_id",
)


def load_review_queue_candidate_page(
    connection: PostgresConnection,
    *,
    access_scope_filter: QueueAccessScopeFilter | None,
    limit: int,
    offset: int,
) -> ReviewQueueRepositoryPage:
    if limit < 1:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero")

    predicate_sql, predicate_params = _review_queue_candidate_predicates(access_scope_filter)
    with connection.cursor() as cursor:
        cursor.execute(_review_queue_count_query(predicate_sql), predicate_params)
        count_rows = cursor.fetchall()
        if not count_rows:
            total_reviewable_item_count = 0
            total_excluded_candidate_count = 0
        else:
            count_row = count_rows[0]
            total_reviewable_item_count = int(
                read_row_value(count_row, "total_reviewable_item_count")
            )
            total_excluded_candidate_count = int(
                read_row_value(count_row, "total_excluded_candidate_count")
            )

        cursor.execute(
            _review_queue_page_query(predicate_sql),
            (*predicate_params, limit, offset),
        )
        records = tuple(candidate_record_from_row(row) for row in cursor.fetchall())

    return ReviewQueueRepositoryPage(
        candidate_records=records,
        total_reviewable_item_count=total_reviewable_item_count,
        total_excluded_candidate_count=total_excluded_candidate_count,
    )


def candidate_record_from_row(row: Mapping[str, Any]) -> CandidatePersistenceRecord:
    return CandidatePersistenceRecord(
        candidate=idea_candidate_from_json(read_json_object(row, "candidate_json")),
        evidence_hash=read_row_value(row, "evidence_hash"),
        persisted_at_utc=read_row_value(row, "persisted_at_utc"),
    )


def _review_queue_candidate_predicates(
    access_scope_filter: QueueAccessScopeFilter | None,
) -> tuple[str, tuple[Any, ...]]:
    predicates = [
        "lifecycle_status = ANY(%s)",
        "review_posture <> %s",
        "(candidate_json->>'suppression_reason') IS NULL",
        "(candidate_json->'score') IS NOT NULL",
        "(candidate_json->'evidence_packet'->>'supportability') <> %s",
    ]
    params: list[Any] = [
        [
            status.value
            for status in (
                IdeaLifecycleStatus.GENERATED,
                IdeaLifecycleStatus.ENRICHED,
                IdeaLifecycleStatus.SCORED,
                IdeaLifecycleStatus.GOVERNANCE_CHECKED,
                IdeaLifecycleStatus.READY_FOR_REVIEW,
            )
        ],
        ReviewPosture.SUPPRESSED.value,
        EvidenceSupportability.BLOCKED.value,
    ]
    if access_scope_filter is not None:
        filter_values = {
            "tenant_id": access_scope_filter.tenant_id,
            "book_id": access_scope_filter.book_id,
            "portfolio_id": access_scope_filter.portfolio_id,
            "client_id": access_scope_filter.client_id,
        }
        for field_name in REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS:
            values = filter_values[field_name]
            if values:
                predicates.append(f"(candidate_json->'access_scope'->>'{field_name}') = ANY(%s)")
                params.append(list(values))
    return " AND ".join(predicates), tuple(params)


def _review_queue_candidate_cte(predicate_sql: str) -> str:
    return f"""
        WITH base AS (
            SELECT candidate_id, lifecycle_status, review_posture, evidence_hash,
                   candidate_json, persisted_at_utc,
                   COALESCE(
                       (
                           SELECT string_agg(signal.value, ',' ORDER BY signal.value)
                           FROM jsonb_array_elements_text(
                               candidate_json->'source_signal_ids'
                           ) AS signal(value)
                       ),
                       candidate_id
                   ) AS source_signal_key,
                   ((candidate_json->'score'->>'score')::numeric) AS queue_score,
                   (candidate_json->>'created_at_utc') AS queue_created_at_utc
            FROM idea_candidate_record
        ),
        eligible AS (
            SELECT *
            FROM base
            WHERE {predicate_sql}
        ),
        deduped AS (
            SELECT DISTINCT ON (source_signal_key) *
            FROM eligible
            ORDER BY source_signal_key, queue_score DESC, queue_created_at_utc, candidate_id
        )
        """


def _review_queue_count_query(predicate_sql: str) -> str:
    return (
        "/* lotus-idea review-queue-count */\n"
        + _review_queue_candidate_cte(predicate_sql)
        + """
        SELECT
            (SELECT COUNT(*) FROM deduped)::integer AS total_reviewable_item_count,
            ((SELECT COUNT(*) FROM base) - (SELECT COUNT(*) FROM deduped))::integer
                AS total_excluded_candidate_count
        """
    )


def _review_queue_page_query(predicate_sql: str) -> str:
    return (
        "/* lotus-idea review-queue-page */\n"
        + _review_queue_candidate_cte(predicate_sql)
        + """
        SELECT candidate_id, evidence_hash, candidate_json, persisted_at_utc
        FROM deduped
        ORDER BY queue_score DESC, queue_created_at_utc, candidate_id
        LIMIT %s OFFSET %s
        """
    )
