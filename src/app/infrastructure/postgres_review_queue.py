from __future__ import annotations

from typing import Any, Mapping

from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.ideas import EvidenceSupportability, IdeaLifecycleStatus, ReviewPosture
from app.domain.scoring import QueueExclusionReason
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.postgres_codecs import (
    idea_candidate_from_json,
    read_json_object,
    read_row_value,
)
from app.infrastructure.postgres_protocols import PostgresConnection
from app.ports.idea_repository import (
    ReviewQueueReadinessRepositorySummary,
    ReviewQueueRepositoryPage,
)


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


def load_review_queue_readiness_summary(
    connection: PostgresConnection,
    *,
    access_scope_filter: QueueAccessScopeFilter | None,
) -> ReviewQueueReadinessRepositorySummary:
    access_scope_mismatch_sql, access_scope_params = _access_scope_mismatch_predicate(
        access_scope_filter,
    )
    params = (
        *access_scope_params,
        ReviewPosture.SUPPRESSED.value,
        IdeaLifecycleStatus.EXPIRED.value,
        IdeaLifecycleStatus.CLOSED.value,
        IdeaLifecycleStatus.REJECTED.value,
        EvidenceSupportability.BLOCKED.value,
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
    )
    with connection.cursor() as cursor:
        cursor.execute(
            _review_queue_readiness_summary_query(access_scope_mismatch_sql),
            params,
        )
        rows = cursor.fetchall()
    if not rows:
        return _empty_readiness_summary()
    row = rows[0]
    exclusion_counts = {
        reason.value: int(read_row_value(row, reason.value)) for reason in QueueExclusionReason
    }
    return ReviewQueueReadinessRepositorySummary(
        candidate_snapshot_count=int(read_row_value(row, "candidate_snapshot_count")),
        reviewable_item_count=int(read_row_value(row, "reviewable_item_count")),
        excluded_candidate_count=int(read_row_value(row, "excluded_candidate_count")),
        exclusion_counts=exclusion_counts,
        scored_candidate_count=int(read_row_value(row, "scored_candidate_count")),
        unscored_candidate_count=int(read_row_value(row, "unscored_candidate_count")),
    )


def candidate_record_from_row(row: Mapping[str, Any]) -> CandidatePersistenceRecord:
    return CandidatePersistenceRecord(
        candidate=idea_candidate_from_json(read_json_object(row, "candidate_json")),
        evidence_hash=read_row_value(row, "evidence_hash"),
        persisted_at_utc=read_row_value(row, "persisted_at_utc"),
    )


def _empty_readiness_summary() -> ReviewQueueReadinessRepositorySummary:
    return ReviewQueueReadinessRepositorySummary(
        candidate_snapshot_count=0,
        reviewable_item_count=0,
        excluded_candidate_count=0,
        exclusion_counts={reason.value: 0 for reason in QueueExclusionReason},
        scored_candidate_count=0,
        unscored_candidate_count=0,
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


def _access_scope_mismatch_predicate(
    access_scope_filter: QueueAccessScopeFilter | None,
) -> tuple[str, tuple[Any, ...]]:
    if access_scope_filter is None or access_scope_filter.is_empty:
        return "FALSE", ()

    filter_values = {
        "tenant_id": access_scope_filter.tenant_id,
        "book_id": access_scope_filter.book_id,
        "portfolio_id": access_scope_filter.portfolio_id,
        "client_id": access_scope_filter.client_id,
    }
    mismatch_predicates = ["(candidate_json->'access_scope') IS NULL"]
    params: list[Any] = []
    for field_name in REVIEW_QUEUE_ACCESS_SCOPE_FILTER_FIELDS:
        values = filter_values[field_name]
        if values:
            mismatch_predicates.append(f"(candidate_json->'access_scope'->>'{field_name}') IS NULL")
            mismatch_predicates.append(
                f"NOT ((candidate_json->'access_scope'->>'{field_name}') = ANY(%s))"
            )
            params.append(list(values))
    return " OR ".join(mismatch_predicates), tuple(params)


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


def _review_queue_readiness_summary_query(access_scope_mismatch_sql: str) -> str:
    return f"""
        /* lotus-idea review-queue-readiness-summary */
        WITH base AS (
            SELECT candidate_id, lifecycle_status, review_posture,
                   candidate_json,
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
        classified AS (
            SELECT *,
                   CASE
                       WHEN {access_scope_mismatch_sql}
                           THEN '{QueueExclusionReason.ACCESS_SCOPE_MISMATCH.value}'
                       WHEN review_posture = %s
                            OR (candidate_json->>'suppression_reason') IS NOT NULL
                           THEN '{QueueExclusionReason.SUPPRESSED.value}'
                       WHEN lifecycle_status = %s
                           THEN '{QueueExclusionReason.EXPIRED.value}'
                       WHEN lifecycle_status = %s
                           THEN '{QueueExclusionReason.CLOSED.value}'
                       WHEN lifecycle_status = %s
                           THEN '{QueueExclusionReason.REJECTED.value}'
                       WHEN (candidate_json->'evidence_packet'->>'supportability') = %s
                           THEN '{QueueExclusionReason.UNSUPPORTED_EVIDENCE.value}'
                       WHEN (candidate_json->'score') IS NULL
                           THEN '{QueueExclusionReason.UNSCORED.value}'
                       WHEN NOT (lifecycle_status = ANY(%s))
                           THEN '{QueueExclusionReason.NON_REVIEWABLE_STATUS.value}'
                       ELSE NULL
                   END AS exclusion_reason
            FROM base
        ),
        eligible AS (
            SELECT *
            FROM classified
            WHERE exclusion_reason IS NULL
        ),
        deduped AS (
            SELECT DISTINCT ON (source_signal_key) *
            FROM eligible
            ORDER BY source_signal_key, queue_score DESC, queue_created_at_utc, candidate_id
        ),
        duplicate_counts AS (
            SELECT GREATEST(
                (SELECT COUNT(*) FROM eligible) - (SELECT COUNT(*) FROM deduped),
                0
            )::integer AS duplicate_count
        )
        SELECT
            (SELECT COUNT(*) FROM base)::integer AS candidate_snapshot_count,
            (SELECT COUNT(*) FROM deduped)::integer AS reviewable_item_count,
            (
                (SELECT COUNT(*) FROM classified WHERE exclusion_reason IS NOT NULL)
                + (SELECT duplicate_count FROM duplicate_counts)
            )::integer AS excluded_candidate_count,
            (SELECT COUNT(*) FROM base WHERE (candidate_json->'score') IS NOT NULL)::integer
                AS scored_candidate_count,
            (SELECT COUNT(*) FROM base WHERE (candidate_json->'score') IS NULL)::integer
                AS unscored_candidate_count,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.SUPPRESSED.value}')::integer
                AS suppressed,
            (SELECT duplicate_count FROM duplicate_counts)::integer AS duplicate,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.EXPIRED.value}')::integer
                AS expired,
            (0)::integer AS snoozed,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.CLOSED.value}')::integer
                AS closed,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.REJECTED.value}')::integer
                AS rejected,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.UNSUPPORTED_EVIDENCE.value}')::integer
                AS unsupported_evidence,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.UNSCORED.value}')::integer
                AS unscored,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.NON_REVIEWABLE_STATUS.value}')::integer
                AS non_reviewable_status,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.ACCESS_SCOPE_MISMATCH.value}')::integer
                AS access_scope_mismatch
        """


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
