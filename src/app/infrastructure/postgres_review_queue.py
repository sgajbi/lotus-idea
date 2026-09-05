from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from app.domain.access_scope import QueueAccessScopeFilter
from app.domain.ideas import (
    EvidenceSupportability,
    IdeaLifecycleStatus,
    ReviewPosture,
    SuppressionReason,
)
from app.domain.review_governance import ReviewAction
from app.domain.review_queue import (
    QueueExclusionReason,
    ReviewQueueAudience,
    ReviewQueueSnapshotConflictError,
    build_review_queue_snapshot_identity,
    require_matching_review_queue_snapshot,
)
from app.domain.persistence import CandidatePersistenceRecord
from app.infrastructure.postgres_codecs import (
    idea_candidate_from_json,
    read_json_object,
    read_row_value,
)
from app.infrastructure.candidate_state_sql import candidate_record_state_compatibility_sql
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


class PostgresReviewQueueRepositoryMixin:
    """Bounded PostgreSQL adapter for advisor queue projections."""

    _connection: PostgresConnection

    def review_queue_candidate_page(
        self,
        *,
        evaluated_at_utc: datetime,
        audience: ReviewQueueAudience,
        expected_snapshot_token: str | None,
        queue_policy_version: str,
        rankable_score_policy_versions: tuple[str, ...],
        access_scope_filter: QueueAccessScopeFilter | None,
        limit: int,
        offset: int,
    ) -> ReviewQueueRepositoryPage:
        return load_review_queue_candidate_page(
            self._connection,
            evaluated_at_utc=evaluated_at_utc,
            audience=audience,
            expected_snapshot_token=expected_snapshot_token,
            queue_policy_version=queue_policy_version,
            rankable_score_policy_versions=rankable_score_policy_versions,
            access_scope_filter=access_scope_filter,
            limit=limit,
            offset=offset,
        )

    def review_queue_readiness_summary(
        self,
        *,
        evaluated_at_utc: datetime,
        audience: ReviewQueueAudience,
        rankable_score_policy_versions: tuple[str, ...],
        access_scope_filter: QueueAccessScopeFilter | None,
    ) -> ReviewQueueReadinessRepositorySummary:
        return load_review_queue_readiness_summary(
            self._connection,
            evaluated_at_utc=evaluated_at_utc,
            audience=audience,
            rankable_score_policy_versions=rankable_score_policy_versions,
            access_scope_filter=access_scope_filter,
        )


def load_review_queue_candidate_page(
    connection: PostgresConnection,
    *,
    evaluated_at_utc: datetime,
    audience: ReviewQueueAudience,
    expected_snapshot_token: str | None,
    queue_policy_version: str,
    rankable_score_policy_versions: tuple[str, ...],
    access_scope_filter: QueueAccessScopeFilter | None,
    limit: int,
    offset: int,
) -> ReviewQueueRepositoryPage:
    if limit < 1:
        raise ValueError("limit must be positive")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero")
    rankable_score_policy_versions = _normalize_rankable_score_policy_versions(
        rankable_score_policy_versions
    )

    predicate_sql, predicate_params = _review_queue_candidate_predicates(
        evaluated_at_utc=evaluated_at_utc,
        audience=audience,
        rankable_score_policy_versions=rankable_score_policy_versions,
        access_scope_filter=access_scope_filter,
    )
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
        fingerprint = _snapshot_fingerprint(count_rows)
        snapshot_identity = build_review_queue_snapshot_identity(
            fingerprint=fingerprint,
            audience=audience,
            evaluated_at_utc=evaluated_at_utc,
            policy_version=queue_policy_version,
            rankable_score_policy_versions=rankable_score_policy_versions,
            access_scope_filter=access_scope_filter,
        )
        require_matching_review_queue_snapshot(
            expected_token=expected_snapshot_token,
            actual_token=snapshot_identity.token,
        )

        cursor.execute(
            _review_queue_page_query(predicate_sql),
            (*predicate_params, limit, offset),
        )
        records = tuple(candidate_record_from_row(row) for row in cursor.fetchall())

        cursor.execute(_review_queue_count_query(predicate_sql), predicate_params)
        verification_rows = cursor.fetchall()
        verification_identity = build_review_queue_snapshot_identity(
            fingerprint=_snapshot_fingerprint(verification_rows),
            audience=audience,
            evaluated_at_utc=evaluated_at_utc,
            policy_version=queue_policy_version,
            rankable_score_policy_versions=rankable_score_policy_versions,
            access_scope_filter=access_scope_filter,
        )
        if verification_identity.token != snapshot_identity.token:
            raise ReviewQueueSnapshotConflictError(
                "advisor review queue state changed while the page was being read"
            )

    return ReviewQueueRepositoryPage(
        candidate_records=records,
        total_reviewable_item_count=total_reviewable_item_count,
        total_excluded_candidate_count=total_excluded_candidate_count,
        snapshot_token=snapshot_identity.token,
    )


def load_review_queue_readiness_summary(
    connection: PostgresConnection,
    *,
    evaluated_at_utc: datetime,
    audience: ReviewQueueAudience,
    rankable_score_policy_versions: tuple[str, ...],
    access_scope_filter: QueueAccessScopeFilter | None,
) -> ReviewQueueReadinessRepositorySummary:
    rankable_score_policy_versions = _normalize_rankable_score_policy_versions(
        rankable_score_policy_versions
    )
    access_scope_mismatch_sql, access_scope_params = _access_scope_mismatch_predicate(
        access_scope_filter,
    )
    params = (
        evaluated_at_utc,
        evaluated_at_utc,
        audience.required_posture.value,
        *access_scope_params,
        evaluated_at_utc,
        ReviewAction.SNOOZE.value,
        evaluated_at_utc,
        SuppressionReason.DUPLICATE.value,
        ReviewPosture.SUPPRESSED.value,
        IdeaLifecycleStatus.EXPIRED.value,
        IdeaLifecycleStatus.CLOSED.value,
        IdeaLifecycleStatus.REJECTED.value,
        EvidenceSupportability.BLOCKED.value,
        list(rankable_score_policy_versions),
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


def _snapshot_fingerprint(rows: Sequence[Any]) -> str:
    if not rows:
        return "empty"
    return str(read_row_value(rows[0], "snapshot_fingerprint"))


def _normalize_rankable_score_policy_versions(
    policy_versions: tuple[str, ...],
) -> tuple[str, ...]:
    normalized = tuple(sorted(version.strip() for version in policy_versions))
    if not normalized or any(not version for version in normalized):
        raise ValueError("rankable_score_policy_versions is required")
    if len(set(normalized)) != len(normalized):
        raise ValueError("rankable_score_policy_versions must be unique")
    return normalized


def _review_queue_candidate_predicates(
    *,
    evaluated_at_utc: datetime,
    audience: ReviewQueueAudience,
    rankable_score_policy_versions: tuple[str, ...],
    access_scope_filter: QueueAccessScopeFilter | None,
) -> tuple[str, tuple[Any, ...]]:
    predicates = [
        candidate_record_state_compatibility_sql(),
        "COALESCE((candidate_json->'evidence_packet'->>"
        "'applicability_expires_at_utc')::timestamptz > %s, TRUE)",
        "lifecycle_status = ANY(%s)",
        "review_posture <> %s",
        "(candidate_json->>'suppression_reason') IS NULL",
        "NOT COALESCE(latest_review_action = %s AND latest_snoozed_until_utc > %s, FALSE)",
        "(candidate_json->'score') IS NOT NULL",
        "(candidate_json->'score'->>'policy_version') = ANY(%s)",
        "(candidate_json->'evidence_packet'->>'supportability') <> %s",
    ]
    params: list[Any] = [
        evaluated_at_utc,
        evaluated_at_utc,
        audience.required_posture.value,
        evaluated_at_utc,
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
        ReviewAction.SNOOZE.value,
        evaluated_at_utc,
        list(rankable_score_policy_versions),
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
            SELECT candidate.candidate_id, lifecycle_status, review_posture, evidence_hash,
                   candidate_json, persisted_at_utc,
                   latest_review.latest_review_action,
                   latest_review.latest_snoozed_until_utc,
                   latest_review.latest_review_accepted_at_utc,
                   latest_review.latest_review_decision_id,
                   ((candidate_json->'score'->>'score')::numeric) AS queue_score,
                   (candidate_json->>'created_at_utc') AS queue_created_at_utc
            FROM idea_candidate_record AS candidate
            {_latest_review_lateral_join()}
            WHERE (candidate_json->>'created_at_utc')::timestamptz <= %s
              AND (
                  review_posture = %s
                  OR (candidate_json->>'suppression_reason') IS NOT NULL
              )
        ),
        eligible AS (
            SELECT *
            FROM base
            WHERE {predicate_sql}
        )
        """


def _review_queue_count_query(predicate_sql: str) -> str:
    return (
        "/* lotus-idea review-queue-count */\n"
        + _review_queue_candidate_cte(predicate_sql)
        + """
        SELECT
            (SELECT COUNT(*) FROM eligible)::integer AS total_reviewable_item_count,
            ((SELECT COUNT(*) FROM base) - (SELECT COUNT(*) FROM eligible))::integer
                AS total_excluded_candidate_count,
            md5(
                COALESCE(
                    (
                        SELECT string_agg(
                            md5(
                                candidate_id || '|' || evidence_hash || '|' ||
                                candidate_json::text || '|' ||
                                COALESCE(latest_review_action, '') || '|' ||
                                COALESCE(latest_review_accepted_at_utc::text, '') || '|' ||
                                COALESCE(latest_snoozed_until_utc::text, '') || '|' ||
                                COALESCE(latest_review_decision_id, '')
                            ),
                            '' ORDER BY candidate_id
                        )
                        FROM base
                    ),
                    ''
                )
            ) AS snapshot_fingerprint
        """
    )


def _latest_review_lateral_join() -> str:
    return """
            LEFT JOIN LATERAL (
                SELECT review.action AS latest_review_action,
                       (review.decision_json->>'snoozed_until_utc')::timestamptz
                           AS latest_snoozed_until_utc,
                       review.accepted_at_utc AS latest_review_accepted_at_utc,
                       review.review_decision_id AS latest_review_decision_id
                FROM idea_review_decision AS review
                WHERE review.candidate_id = candidate.candidate_id
                  AND review.accepted_at_utc <= %s
                  AND review.accepted_at_utc >= COALESCE(
                      (
                          SELECT MIN(history.recorded_at_utc)
                          FROM idea_candidate_version_history AS history
                          WHERE history.candidate_id = candidate.candidate_id
                            AND history.material_version = candidate.material_version
                      ),
                      (candidate.candidate_json->>'created_at_utc')::timestamptz
                  )
                ORDER BY review.accepted_at_utc DESC, review.review_decision_id DESC
                LIMIT 1
            ) AS latest_review ON TRUE
        """


def _review_queue_readiness_summary_query(access_scope_mismatch_sql: str) -> str:
    return (
        "/* lotus-idea review-queue-readiness-summary */\n"
        + _review_queue_readiness_candidate_ctes(access_scope_mismatch_sql)
        + "\n"
        + _review_queue_readiness_summary_select()
    )


def _review_queue_readiness_candidate_ctes(access_scope_mismatch_sql: str) -> str:
    return f"""
        WITH base AS (
            {_review_queue_base_candidate_select()}
        ),
        classified AS (
            SELECT *,
                   {_review_queue_readiness_exclusion_case(access_scope_mismatch_sql)}
            FROM base
        ),
        eligible AS (
            SELECT *
            FROM classified
            WHERE exclusion_reason IS NULL
        )
        """


def _review_queue_base_candidate_select() -> str:
    return f"""
            SELECT candidate.candidate_id, lifecycle_status, review_posture,
                   candidate_json,
                   latest_review.latest_review_action,
                   latest_review.latest_snoozed_until_utc,
                   ((candidate_json->'score'->>'score')::numeric) AS queue_score,
                   (candidate_json->>'created_at_utc') AS queue_created_at_utc
            FROM idea_candidate_record AS candidate
            {_latest_review_lateral_join()}
            WHERE (candidate_json->>'created_at_utc')::timestamptz <= %s
              AND (
                  review_posture = %s
                  OR (candidate_json->>'suppression_reason') IS NOT NULL
              )
        """


def _review_queue_readiness_exclusion_case(access_scope_mismatch_sql: str) -> str:
    compatible_state_sql = candidate_record_state_compatibility_sql()
    return f"""
                    CASE
                        WHEN {access_scope_mismatch_sql}
                            THEN '{QueueExclusionReason.ACCESS_SCOPE_MISMATCH.value}'
                        WHEN NOT {compatible_state_sql}
                            THEN '{QueueExclusionReason.INVALID_STATE.value}'
                        WHEN COALESCE(
                            (candidate_json->'evidence_packet'->>
                                'applicability_expires_at_utc')::timestamptz <= %s,
                            FALSE
                        )
                            THEN '{QueueExclusionReason.EXPIRED.value}'
                        WHEN latest_review_action = %s
                            AND latest_snoozed_until_utc > %s
                            THEN '{QueueExclusionReason.SNOOZED.value}'
                        WHEN (candidate_json->>'suppression_reason') = %s
                            THEN '{QueueExclusionReason.DUPLICATE.value}'
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
                        WHEN (candidate_json->'score'->>'policy_version') IS NULL
                            OR NOT ((candidate_json->'score'->>'policy_version') = ANY(%s))
                            THEN '{QueueExclusionReason.UNRANKABLE_SCORE_POLICY.value}'
                        WHEN NOT (lifecycle_status = ANY(%s))
                           THEN '{QueueExclusionReason.NON_REVIEWABLE_STATUS.value}'
                       ELSE NULL
                   END AS exclusion_reason
        """


def _review_queue_readiness_summary_select() -> str:
    return f"""
        SELECT
            (SELECT COUNT(*) FROM base)::integer AS candidate_snapshot_count,
            (SELECT COUNT(*) FROM eligible)::integer AS reviewable_item_count,
            (SELECT COUNT(*) FROM classified WHERE exclusion_reason IS NOT NULL)::integer
                AS excluded_candidate_count,
            (SELECT COUNT(*) FROM base WHERE (candidate_json->'score') IS NOT NULL)::integer
                AS scored_candidate_count,
            (SELECT COUNT(*) FROM base WHERE (candidate_json->'score') IS NULL)::integer
                AS unscored_candidate_count,
            (SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{QueueExclusionReason.INVALID_STATE.value}')::integer
                AS invalid_state,
            {_queue_exclusion_count_projection(QueueExclusionReason.SUPPRESSED)},
            {_queue_exclusion_count_projection(QueueExclusionReason.DUPLICATE)},
            {_queue_exclusion_count_projection(QueueExclusionReason.EXPIRED)},
            {_queue_exclusion_count_projection(QueueExclusionReason.SNOOZED)},
            {_queue_exclusion_count_projection(QueueExclusionReason.CLOSED)},
            {_queue_exclusion_count_projection(QueueExclusionReason.REJECTED)},
            {_queue_exclusion_count_projection(QueueExclusionReason.UNSUPPORTED_EVIDENCE)},
            {_queue_exclusion_count_projection(QueueExclusionReason.UNSCORED)},
            {_queue_exclusion_count_projection(QueueExclusionReason.UNRANKABLE_SCORE_POLICY)},
            {_queue_exclusion_count_projection(QueueExclusionReason.NON_REVIEWABLE_STATUS)},
            {_queue_exclusion_count_projection(QueueExclusionReason.ACCESS_SCOPE_MISMATCH)}
        """


def _queue_exclusion_count_projection(reason: QueueExclusionReason) -> str:
    return f"""(SELECT COUNT(*) FROM classified
                WHERE exclusion_reason = '{reason.value}')::integer
                AS {reason.value}"""


def _review_queue_page_query(predicate_sql: str) -> str:
    return (
        "/* lotus-idea review-queue-page */\n"
        + _review_queue_candidate_cte(predicate_sql)
        + """
        SELECT candidate_id, evidence_hash, candidate_json, persisted_at_utc
        FROM eligible
        ORDER BY queue_score DESC, queue_created_at_utc, candidate_id
        LIMIT %s OFFSET %s
        """
    )
