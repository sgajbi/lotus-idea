from __future__ import annotations

from typing import Any

from app.infrastructure.postgres_codecs import decode_datetime, read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection
from app.ports.idea_repository import RuntimeTrustTelemetryRepositorySummary


def load_runtime_trust_telemetry_summary(
    connection: PostgresConnection,
) -> RuntimeTrustTelemetryRepositorySummary:
    with connection.cursor() as cursor:
        cursor.execute(_summary_query())
        summary_rows = cursor.fetchall()
        summary = summary_rows[0] if summary_rows else {}

        source_authority_counts = _load_count_map(
            cursor,
            """
            /* lotus-idea runtime-trust-telemetry-source-authority-counts */
            WITH source_ref_rows AS (
                SELECT source_ref
                FROM idea_candidate_record
                CROSS JOIN LATERAL jsonb_array_elements(
                    candidate_json->'evidence_packet'->'source_refs'
                ) AS source_ref
            )
            SELECT source_ref->>'source_system' AS label, COUNT(*)::integer AS count
            FROM source_ref_rows
            GROUP BY label
            """,
        )
        freshness_counts = _load_count_map(
            cursor,
            """
            /* lotus-idea runtime-trust-telemetry-freshness-counts */
            WITH source_ref_rows AS (
                SELECT source_ref
                FROM idea_candidate_record
                CROSS JOIN LATERAL jsonb_array_elements(
                    candidate_json->'evidence_packet'->'source_refs'
                ) AS source_ref
            )
            SELECT source_ref->>'freshness' AS label, COUNT(*)::integer AS count
            FROM source_ref_rows
            GROUP BY label
            """,
        )
        supportability_counts = _load_count_map(
            cursor,
            """
            /* lotus-idea runtime-trust-telemetry-supportability-counts */
            SELECT candidate_json->'evidence_packet'->>'supportability' AS label,
                   COUNT(*)::integer AS count
            FROM idea_candidate_record
            GROUP BY label
            """,
        )
        lifecycle_counts = _load_count_map(
            cursor,
            """
            /* lotus-idea runtime-trust-telemetry-lifecycle-counts */
            SELECT lifecycle_status AS label, COUNT(*)::integer AS count
            FROM idea_candidate_record
            GROUP BY lifecycle_status
            """,
        )

    return RuntimeTrustTelemetryRepositorySummary(
        candidate_snapshot_count=_int(summary, "candidate_snapshot_count"),
        current_source_ref_count=_int(summary, "current_source_ref_count"),
        stale_or_unavailable_source_ref_count=_int(
            summary,
            "stale_or_unavailable_source_ref_count",
        ),
        source_authority_counts=source_authority_counts,
        freshness_counts=freshness_counts,
        supportability_counts=supportability_counts,
        lifecycle_counts=lifecycle_counts,
        review_decision_count=_int(summary, "review_decision_count"),
        feedback_event_count=_int(summary, "feedback_event_count"),
        conversion_intent_count=_int(summary, "conversion_intent_count"),
        conversion_outcome_count=_int(summary, "conversion_outcome_count"),
        report_evidence_pack_count=_int(summary, "report_evidence_pack_count"),
        lineage_materialized=bool(read_row_value(summary, "lineage_materialized"))
        if summary
        else False,
        source_batch_evidence_available=bool(
            read_row_value(summary, "source_batch_evidence_available")
        )
        if summary
        else False,
        data_quality_status=str(
            read_row_value(summary, "data_quality_status") or "quality_unknown"
        ),
        latest_source_generated_at_utc=(
            decode_datetime(read_row_value(summary, "latest_source_generated_at_utc"))
            if summary and read_row_value(summary, "latest_source_generated_at_utc") is not None
            else None
        ),
        source_as_of_dates=tuple(
            str(value) for value in (read_row_value(summary, "source_as_of_dates") or ())
        ),
    )


def _summary_query() -> str:
    return """
        /* lotus-idea runtime-trust-telemetry-summary */
        WITH candidate_base AS (
            SELECT candidate_json
            FROM idea_candidate_record
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
            (SELECT COUNT(*) FROM idea_review_decision)::integer AS review_decision_count,
            (SELECT COUNT(*) FROM idea_feedback_event)::integer AS feedback_event_count,
            (SELECT COUNT(*) FROM idea_conversion_intent)::integer AS conversion_intent_count,
            (SELECT COUNT(*) FROM idea_conversion_outcome)::integer AS conversion_outcome_count,
            (
                SELECT COUNT(*)
                FROM idea_report_evidence_pack_request
            )::integer AS report_evidence_pack_count
    """


def _load_count_map(cursor: Any, query: str) -> dict[str, int]:
    cursor.execute(query)
    counts: dict[str, int] = {}
    for row in cursor.fetchall():
        label = read_row_value(row, "label")
        if label is not None:
            counts[str(label)] = int(read_row_value(row, "count"))
    return counts


def _int(row: Any, key: str) -> int:
    if not row:
        return 0
    value = read_row_value(row, key)
    return int(value) if value is not None else 0
