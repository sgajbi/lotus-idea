from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.infrastructure.postgres_codecs import decode_datetime, read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection
from app.ports.idea_repository import RuntimeTrustTelemetryRepositorySummary


@dataclass(frozen=True)
class _RuntimeTrustTelemetryRows:
    summary: Any
    source_authority_counts: dict[str, int]
    freshness_counts: dict[str, int]
    supportability_counts: dict[str, int]
    lifecycle_counts: dict[str, int]
    data_lifecycle_state_counts: dict[str, int]


@dataclass(frozen=True)
class _RuntimeTrustTelemetryCountQuery:
    field_name: str
    sql: str


def load_runtime_trust_telemetry_summary(
    connection: PostgresConnection,
) -> RuntimeTrustTelemetryRepositorySummary:
    with connection.cursor() as cursor:
        rows = _load_runtime_trust_telemetry_rows(cursor)

    return _summary_from_rows(rows)


def _load_runtime_trust_telemetry_rows(cursor: Any) -> _RuntimeTrustTelemetryRows:
    summary = _load_summary_row(cursor)
    count_maps = _load_count_maps(cursor)
    return _RuntimeTrustTelemetryRows(
        summary=summary,
        source_authority_counts=count_maps["source_authority_counts"],
        freshness_counts=count_maps["freshness_counts"],
        supportability_counts=count_maps["supportability_counts"],
        lifecycle_counts=count_maps["lifecycle_counts"],
        data_lifecycle_state_counts=count_maps["data_lifecycle_state_counts"],
    )


def _summary_from_rows(
    rows: _RuntimeTrustTelemetryRows,
) -> RuntimeTrustTelemetryRepositorySummary:
    summary = rows.summary
    return RuntimeTrustTelemetryRepositorySummary(
        candidate_snapshot_count=_int(summary, "candidate_snapshot_count"),
        current_source_ref_count=_int(summary, "current_source_ref_count"),
        stale_or_unavailable_source_ref_count=_int(
            summary,
            "stale_or_unavailable_source_ref_count",
        ),
        source_authority_counts=rows.source_authority_counts,
        freshness_counts=rows.freshness_counts,
        supportability_counts=rows.supportability_counts,
        lifecycle_counts=rows.lifecycle_counts,
        review_decision_count=_int(summary, "review_decision_count"),
        feedback_event_count=_int(summary, "feedback_event_count"),
        conversion_intent_count=_int(summary, "conversion_intent_count"),
        conversion_outcome_count=_int(summary, "conversion_outcome_count"),
        report_evidence_pack_count=_int(summary, "report_evidence_pack_count"),
        downstream_submission_count=_int(summary, "downstream_submission_count"),
        downstream_reconciliation_required_count=_int(
            summary,
            "downstream_reconciliation_required_count",
        ),
        lineage_materialized=bool(read_row_value(summary, "lineage_materialized"))
        if summary
        else False,
        source_batch_evidence_available=bool(
            read_row_value(summary, "source_batch_evidence_available")
        )
        if summary
        else False,
        data_quality_status=str(
            _optional_row_value(summary, "data_quality_status") or "quality_unknown"
        ),
        latest_source_generated_at_utc=_latest_source_generated_at_utc(summary),
        source_as_of_dates=tuple(
            str(value) for value in (_optional_row_value(summary, "source_as_of_dates") or ())
        ),
        data_lifecycle_state_counts=rows.data_lifecycle_state_counts,
        retention_expired_count=_int(summary, "retention_expired_count"),
        lifecycle_control_missing_count=_int(summary, "lifecycle_control_missing_count"),
    )


def _load_summary_row(cursor: Any) -> Any:
    cursor.execute(_summary_query())
    rows = cursor.fetchall()
    return rows[0] if rows else {}


_SUMMARY_BASE_QUERY = """
        /* lotus-idea runtime-trust-telemetry-summary */
        WITH candidate_base AS (
            SELECT candidate_json
            FROM idea_candidate_record candidate
            JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = candidate.candidate_id
            WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
        ),
        source_ref_rows AS (
            SELECT source_ref
            FROM candidate_base
            CROSS JOIN LATERAL jsonb_array_elements(
                candidate_json->'evidence_packet'->'source_refs'
            ) AS source_ref
        )
        SELECT
            (SELECT COUNT(*) FROM candidate_base)::integer AS candidate_snapshot_count,
            (
                SELECT COUNT(*)
                FROM source_ref_rows
                WHERE source_ref->>'freshness' = 'current'
            )::integer AS current_source_ref_count,
            (
                SELECT COUNT(*)
                FROM source_ref_rows
                WHERE COALESCE(source_ref->>'freshness', '') <> 'current'
            )::integer AS stale_or_unavailable_source_ref_count,
            (SELECT COUNT(*) > 0 FROM source_ref_rows) AS source_batch_evidence_available,
            COALESCE(
                (
                    SELECT BOOL_AND(
                        COALESCE(
                            candidate_json->'evidence_packet'->'lineage_ref'->>'lineage_id',
                            ''
                        ) <> ''
                        AND jsonb_array_length(
                            COALESCE(
                                candidate_json->'evidence_packet'->'lineage_ref'->'source_refs',
                                '[]'::jsonb
                            )
                        ) > 0
                    )
                    FROM candidate_base
                ),
                false
            ) AS lineage_materialized,
            (
                SELECT CASE
                    WHEN COUNT(*) = 0 THEN 'quality_unknown'
                    WHEN BOOL_AND(source_ref->>'data_quality_status' = 'complete')
                        THEN 'quality_passed'
                    ELSE 'quality_warning'
                END
                FROM source_ref_rows
            ) AS data_quality_status,
            (
                SELECT MAX((source_ref->>'generated_at_utc')::timestamptz)
                FROM source_ref_rows
            ) AS latest_source_generated_at_utc,
            COALESCE(
                ARRAY(
                    SELECT DISTINCT source_ref->>'as_of_date'
                    FROM source_ref_rows
                    WHERE COALESCE(source_ref->>'as_of_date', '') <> ''
                    ORDER BY 1
                ),
                ARRAY[]::text[]
            ) AS source_as_of_dates,
"""

_SUMMARY_WORKFLOW_COUNTS_QUERY = """
            (
                SELECT COUNT(*) FROM idea_review_decision record
                JOIN idea_data_lifecycle_control lifecycle USING (candidate_id)
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )::integer AS review_decision_count,
            (
                SELECT COUNT(*) FROM idea_feedback_event record
                JOIN idea_data_lifecycle_control lifecycle USING (candidate_id)
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )::integer AS feedback_event_count,
            (
                SELECT COUNT(*) FROM idea_conversion_intent record
                JOIN idea_data_lifecycle_control lifecycle USING (candidate_id)
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )::integer AS conversion_intent_count,
            (
                SELECT COUNT(*) FROM idea_conversion_outcome outcome
                JOIN idea_conversion_intent intent USING (conversion_intent_id)
                JOIN idea_data_lifecycle_control lifecycle USING (candidate_id)
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )::integer AS conversion_outcome_count,
            (
                SELECT COUNT(*) FROM idea_report_evidence_pack_request record
                JOIN idea_data_lifecycle_control lifecycle USING (candidate_id)
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )::integer AS report_evidence_pack_count,
            (
                SELECT COUNT(*)
                FROM idea_downstream_submission
            )::integer AS downstream_submission_count,
            (
                SELECT COUNT(*)
                FROM idea_downstream_submission
                WHERE status IN ('in_flight', 'reconciliation_required')
            )::integer AS downstream_reconciliation_required_count
"""

_SUMMARY_DATA_LIFECYCLE_QUERY = """
            ,(
                SELECT COUNT(*) FROM idea_data_lifecycle_control
                WHERE state = 'active' AND retention_expires_at_utc <= CURRENT_TIMESTAMP
            )::integer AS retention_expired_count
            ,(
                SELECT COUNT(*)
                FROM idea_candidate_record candidate
                LEFT JOIN idea_data_lifecycle_control lifecycle
                  ON lifecycle.candidate_id = candidate.candidate_id
                WHERE lifecycle.candidate_id IS NULL
            )::integer AS lifecycle_control_missing_count
"""


def _summary_query() -> str:
    return "".join(
        (
            _SUMMARY_BASE_QUERY,
            _SUMMARY_WORKFLOW_COUNTS_QUERY,
            _SUMMARY_DATA_LIFECYCLE_QUERY,
        )
    )


def _load_count_maps(cursor: Any) -> dict[str, dict[str, int]]:
    return {query.field_name: _load_count_map(cursor, query.sql) for query in _count_queries()}


def _count_queries() -> tuple[_RuntimeTrustTelemetryCountQuery, ...]:
    return (
        _RuntimeTrustTelemetryCountQuery(
            field_name="source_authority_counts",
            sql=_source_authority_counts_query(),
        ),
        _RuntimeTrustTelemetryCountQuery(
            field_name="freshness_counts",
            sql=_freshness_counts_query(),
        ),
        _RuntimeTrustTelemetryCountQuery(
            field_name="supportability_counts",
            sql=_supportability_counts_query(),
        ),
        _RuntimeTrustTelemetryCountQuery(
            field_name="lifecycle_counts",
            sql=_lifecycle_counts_query(),
        ),
        _RuntimeTrustTelemetryCountQuery(
            field_name="data_lifecycle_state_counts",
            sql=_data_lifecycle_counts_query(),
        ),
    )


def _source_authority_counts_query() -> str:
    return """
            /* lotus-idea runtime-trust-telemetry-source-authority-counts */
            WITH source_ref_rows AS (
                SELECT source_ref
                FROM idea_candidate_record candidate
                JOIN idea_data_lifecycle_control lifecycle
                  ON lifecycle.candidate_id = candidate.candidate_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    candidate_json->'evidence_packet'->'source_refs'
                ) AS source_ref
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )
            SELECT source_ref->>'source_system' AS label, COUNT(*)::integer AS count
            FROM source_ref_rows
            GROUP BY label
            """


def _freshness_counts_query() -> str:
    return """
            /* lotus-idea runtime-trust-telemetry-freshness-counts */
            WITH source_ref_rows AS (
                SELECT source_ref
                FROM idea_candidate_record candidate
                JOIN idea_data_lifecycle_control lifecycle
                  ON lifecycle.candidate_id = candidate.candidate_id
                CROSS JOIN LATERAL jsonb_array_elements(
                    candidate_json->'evidence_packet'->'source_refs'
                ) AS source_ref
                WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            )
            SELECT source_ref->>'freshness' AS label, COUNT(*)::integer AS count
            FROM source_ref_rows
            GROUP BY label
            """


def _supportability_counts_query() -> str:
    return """
            /* lotus-idea runtime-trust-telemetry-supportability-counts */
            SELECT candidate_json->'evidence_packet'->>'supportability' AS label,
                   COUNT(*)::integer AS count
            FROM idea_candidate_record candidate
            JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = candidate.candidate_id
            WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            GROUP BY label
            """


def _lifecycle_counts_query() -> str:
    return """
            /* lotus-idea runtime-trust-telemetry-lifecycle-counts */
            SELECT lifecycle_status AS label, COUNT(*)::integer AS count
            FROM idea_candidate_record candidate
            JOIN idea_data_lifecycle_control lifecycle
              ON lifecycle.candidate_id = candidate.candidate_id
            WHERE COALESCE(lifecycle.held_from_state, lifecycle.state) = 'active'
            GROUP BY lifecycle_status
            """


def _data_lifecycle_counts_query() -> str:
    return """
            /* lotus-idea runtime-trust-telemetry-data-lifecycle-counts */
            SELECT state AS label, COUNT(*)::integer AS count
            FROM idea_data_lifecycle_control
            GROUP BY state
            """


def _load_count_map(cursor: Any, query: str) -> dict[str, int]:
    cursor.execute(query)
    counts: dict[str, int] = {}
    for row in cursor.fetchall():
        label = read_row_value(row, "label")
        if label is not None:
            counts[str(label)] = int(read_row_value(row, "count"))
    return counts


def _latest_source_generated_at_utc(summary: Any) -> datetime | None:
    if not summary:
        return None
    value = _optional_row_value(summary, "latest_source_generated_at_utc")
    return decode_datetime(value) if value is not None else None


def _optional_row_value(row: Any, key: str) -> Any:
    if not row:
        return None
    try:
        return read_row_value(row, key)
    except KeyError:
        return None


def _int(row: Any, key: str) -> int:
    if not row:
        return 0
    value = read_row_value(row, key)
    return int(value) if value is not None else 0
