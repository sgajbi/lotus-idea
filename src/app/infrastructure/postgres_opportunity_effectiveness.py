from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection
from app.ports.idea_repository import OpportunityEffectivenessRepositorySummary


def load_opportunity_effectiveness_summary(
    connection: PostgresConnection,
    *,
    tenant_id: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
    evaluated_at_utc: datetime,
    max_opportunities: int,
) -> OpportunityEffectivenessRepositorySummary:
    """Load one bounded, tenant-scoped aggregate row without hydrating candidates."""

    with connection.cursor() as cursor:
        cursor.execute(
            _SUMMARY_QUERY,
            (
                tenant_id,
                window_start_utc,
                window_end_utc,
                evaluated_at_utc,
                max_opportunities + 1,
            ),
        )
        rows = cursor.fetchall()
    if len(rows) != 1:
        raise RuntimeError("opportunity effectiveness query must return exactly one summary row")
    row = rows[0]
    invalid_temporal_fact_count = _integer(row, "invalid_temporal_fact_count")
    if invalid_temporal_fact_count:
        raise RuntimeError("opportunity effectiveness contains temporally invalid durable facts")
    invalid_outcome_history_count = _integer(row, "invalid_outcome_history_count")
    if invalid_outcome_history_count:
        raise RuntimeError("opportunity effectiveness contains quarantined conversion outcomes")
    return OpportunityEffectivenessRepositorySummary(
        generated_opportunity_count=_integer(row, "generated_opportunity_count"),
        reviewed_opportunity_count=_integer(row, "reviewed_opportunity_count"),
        feedback_opportunity_count=_integer(row, "feedback_opportunity_count"),
        conversion_opportunity_count=_integer(row, "conversion_opportunity_count"),
        conversion_intent_count=_integer(row, "conversion_intent_count"),
        stale_evidence_opportunity_count=_integer(row, "stale_evidence_opportunity_count"),
        unavailable_evidence_opportunity_count=_integer(
            row, "unavailable_evidence_opportunity_count"
        ),
        unsupported_evidence_opportunity_count=_integer(
            row, "unsupported_evidence_opportunity_count"
        ),
        suppressed_opportunity_count=_integer(row, "suppressed_opportunity_count"),
        duplicate_suppressed_opportunity_count=_integer(
            row, "duplicate_suppressed_opportunity_count"
        ),
        recurrent_opportunity_count=_integer(row, "recurrent_opportunity_count"),
        recurrent_detection_count=_integer(row, "recurrent_detection_count"),
        reconciled_submission_count=_integer(row, "reconciled_submission_count"),
        family_counts=_counts(row, "family_counts"),
        score_band_counts=_counts(row, "score_band_counts"),
        latest_review_action_counts=_counts(row, "latest_review_action_counts"),
        feedback_reason_counts=_counts(row, "feedback_reason_counts"),
        current_downstream_outcome_counts=_counts(row, "current_downstream_outcome_counts"),
        downstream_submission_posture_counts=_counts(row, "downstream_submission_posture_counts"),
        detection_to_review_seconds=_decimals(row, "detection_to_review_seconds"),
        approval_to_conversion_seconds=_decimals(row, "approval_to_conversion_seconds"),
    )


def _integer(row: Any, key: str) -> int:
    value = read_row_value(row, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be an integer")
    return value


def _counts(row: Any, key: str) -> Mapping[str, int]:
    value = read_row_value(row, key)
    if not isinstance(value, Mapping):
        raise TypeError(f"{key} must be a mapping")
    counts: dict[str, int] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str):
            raise TypeError(f"{key} keys must be strings")
        if isinstance(item_value, bool) or not isinstance(item_value, int):
            raise TypeError(f"{key} values must be integers")
        counts[item_key] = item_value
    return counts


def _decimals(row: Any, key: str) -> tuple[Decimal, ...]:
    value = read_row_value(row, key)
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{key} must be an array")
    return tuple(item if isinstance(item, Decimal) else Decimal(str(item)) for item in value)


_SUMMARY_QUERY = """
/* lotus-idea opportunity-effectiveness-summary-v1 */
WITH parameters AS (
    SELECT
        %s::TEXT AS tenant_id,
        %s::TIMESTAMPTZ AS window_start_utc,
        %s::TIMESTAMPTZ AS window_end_utc,
        %s::TIMESTAMPTZ AS evaluated_at_utc,
        %s::INTEGER AS bounded_limit
),
cohort AS MATERIALIZED (
    SELECT candidate.*
    FROM idea_candidate_record AS candidate
    JOIN idea_data_lifecycle_control AS lifecycle
      ON lifecycle.candidate_id = candidate.candidate_id
    CROSS JOIN parameters
    WHERE lifecycle.tenant_id = parameters.tenant_id
      AND lifecycle.state IN ('active', 'held')
      AND candidate.generated_at_utc >= parameters.window_start_utc
      AND candidate.generated_at_utc < parameters.window_end_utc
    ORDER BY candidate.candidate_id
    LIMIT (SELECT bounded_limit FROM parameters)
),
latest_reviews AS (
    SELECT DISTINCT ON (review.candidate_id)
        review.candidate_id,
        review.action,
        review.decision_json->>'suppression_reason' AS suppression_reason,
        review.decided_at_utc
    FROM idea_review_decision AS review
    JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE review.decided_at_utc <= parameters.evaluated_at_utc
    ORDER BY review.candidate_id, review.decided_at_utc DESC, review.review_decision_id DESC
),
first_approvals AS (
    SELECT review.candidate_id, MIN(review.decided_at_utc) AS decided_at_utc
    FROM idea_review_decision AS review
    JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE review.action = 'approve_for_conversion'
      AND review.decided_at_utc <= parameters.evaluated_at_utc
    GROUP BY review.candidate_id
),
feedback AS (
    SELECT event.candidate_id, event.feedback_reason
    FROM idea_feedback_event AS event
    JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE event.recorded_at_utc <= parameters.evaluated_at_utc
),
intents AS (
    SELECT intent.*
    FROM idea_conversion_intent AS intent
    JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE intent.requested_at_utc <= parameters.evaluated_at_utc
),
first_intents AS (
    SELECT candidate_id, MIN(requested_at_utc) AS requested_at_utc
    FROM intents
    GROUP BY candidate_id
),
current_outcomes AS (
    SELECT
        intent.conversion_intent_id,
        COALESCE(current_outcome.status, 'not_reported') AS status
    FROM intents AS intent
    CROSS JOIN parameters
    LEFT JOIN LATERAL (
        SELECT outcome.status
        FROM idea_conversion_outcome AS outcome
        WHERE outcome.conversion_intent_id = intent.conversion_intent_id
          AND outcome.recorded_at_utc <= parameters.evaluated_at_utc
        ORDER BY outcome.source_event_version DESC, outcome.conversion_outcome_id DESC
        LIMIT 1
    ) AS current_outcome ON TRUE
),
submissions AS (
    SELECT submission.*
    FROM idea_downstream_submission AS submission
    JOIN intents ON intents.conversion_intent_id = submission.resource_id
    CROSS JOIN parameters
    WHERE submission.resource_type = 'conversion_intent'
      AND submission.submitted_at_utc <= parameters.evaluated_at_utc
),
recurrent AS (
    SELECT history.candidate_id, COUNT(*)::INTEGER AS detection_count
    FROM idea_candidate_version_history AS history
    JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE history.change_reason = 'recurrent_condition'
      AND history.recorded_at_utc <= parameters.evaluated_at_utc
    GROUP BY history.candidate_id
),
invalid_temporal_facts AS (
    SELECT review.review_decision_id AS fact_id
    FROM idea_review_decision AS review JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE review.decided_at_utc <= parameters.evaluated_at_utc
      AND review.decided_at_utc < cohort.generated_at_utc
    UNION ALL
    SELECT event.feedback_event_id
    FROM idea_feedback_event AS event JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE event.recorded_at_utc <= parameters.evaluated_at_utc
      AND event.recorded_at_utc < cohort.generated_at_utc
    UNION ALL
    SELECT intent.conversion_intent_id
    FROM intents AS intent JOIN cohort USING (candidate_id)
    WHERE intent.requested_at_utc < cohort.generated_at_utc
    UNION ALL
    SELECT history.candidate_version_history_id
    FROM idea_candidate_version_history AS history JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE history.recorded_at_utc <= parameters.evaluated_at_utc
      AND history.recorded_at_utc < cohort.generated_at_utc
    UNION ALL
    SELECT outcome.conversion_outcome_id
    FROM idea_conversion_outcome AS outcome
    JOIN intents AS intent USING (conversion_intent_id)
    CROSS JOIN parameters
    WHERE outcome.recorded_at_utc <= parameters.evaluated_at_utc
      AND outcome.recorded_at_utc < intent.requested_at_utc
),
family_counts AS (
    SELECT family AS value, COUNT(*)::INTEGER AS count FROM cohort GROUP BY family
),
score_band_counts AS (
    SELECT
        CASE
            WHEN candidate_json->'score' = 'null'::JSONB THEN 'unranked'
            WHEN (candidate_json->'score'->>'score')::NUMERIC >= 85 THEN 'critical'
            WHEN (candidate_json->'score'->>'score')::NUMERIC >= 70 THEN 'high'
            WHEN (candidate_json->'score'->>'score')::NUMERIC >= 50 THEN 'standard'
            ELSE 'watchlist'
        END AS value,
        COUNT(*)::INTEGER AS count
    FROM cohort
    GROUP BY value
),
review_action_counts AS (
    SELECT action AS value, COUNT(*)::INTEGER AS count FROM latest_reviews GROUP BY action
),
feedback_reason_counts AS (
    SELECT feedback_reason AS value, COUNT(*)::INTEGER AS count FROM feedback GROUP BY feedback_reason
),
outcome_counts AS (
    SELECT status AS value, COUNT(*)::INTEGER AS count FROM current_outcomes GROUP BY status
),
submission_counts AS (
    SELECT status AS value, COUNT(*)::INTEGER AS count FROM submissions GROUP BY status
)
SELECT
    (SELECT COUNT(*)::INTEGER FROM cohort) AS generated_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM latest_reviews) AS reviewed_opportunity_count,
    (SELECT COUNT(DISTINCT candidate_id)::INTEGER FROM feedback) AS feedback_opportunity_count,
    (SELECT COUNT(DISTINCT candidate_id)::INTEGER FROM intents) AS conversion_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM intents) AS conversion_intent_count,
    (SELECT COUNT(*)::INTEGER FROM cohort WHERE EXISTS (
        SELECT 1 FROM jsonb_array_elements(candidate_json->'evidence_packet'->'source_refs') AS source
        WHERE source->>'freshness' IN ('stale', 'expired')
    )) AS stale_evidence_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM cohort WHERE EXISTS (
        SELECT 1 FROM jsonb_array_elements(candidate_json->'evidence_packet'->'source_refs') AS source
        WHERE source->>'freshness' = 'unavailable'
    )) AS unavailable_evidence_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM cohort
     WHERE candidate_json->'evidence_packet'->>'supportability' <> 'ready')
        AS unsupported_evidence_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM cohort
     LEFT JOIN latest_reviews USING (candidate_id)
     WHERE latest_reviews.action = 'suppress'
        OR (latest_reviews.candidate_id IS NULL AND cohort.candidate_json->>'suppression_reason' IS NOT NULL))
        AS suppressed_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM cohort
     LEFT JOIN latest_reviews USING (candidate_id)
     WHERE (latest_reviews.action = 'suppress' AND latest_reviews.suppression_reason = 'duplicate')
        OR (latest_reviews.candidate_id IS NULL AND cohort.candidate_json->>'suppression_reason' = 'duplicate'))
        AS duplicate_suppressed_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM recurrent) AS recurrent_opportunity_count,
    COALESCE((SELECT SUM(detection_count)::INTEGER FROM recurrent), 0)
        AS recurrent_detection_count,
    (SELECT COUNT(*)::INTEGER FROM submissions AS submission CROSS JOIN parameters
     WHERE EXISTS (
         SELECT 1 FROM jsonb_array_elements(submission.audit_json) AS audit
         WHERE audit->>'action' = 'reconciled'
           AND (audit->>'occurredAtUtc')::TIMESTAMPTZ <= parameters.evaluated_at_utc
     )) AS reconciled_submission_count,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM family_counts), '{}'::JSONB)
        AS family_counts,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM score_band_counts), '{}'::JSONB)
        AS score_band_counts,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM review_action_counts), '{}'::JSONB)
        AS latest_review_action_counts,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM feedback_reason_counts), '{}'::JSONB)
        AS feedback_reason_counts,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM outcome_counts), '{}'::JSONB)
        AS current_downstream_outcome_counts,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM submission_counts), '{}'::JSONB)
        AS downstream_submission_posture_counts,
    COALESCE((SELECT array_agg(
        EXTRACT(EPOCH FROM (latest_reviews.decided_at_utc - cohort.generated_at_utc))::NUMERIC
        ORDER BY latest_reviews.decided_at_utc - cohort.generated_at_utc
    ) FROM latest_reviews JOIN cohort USING (candidate_id)), ARRAY[]::NUMERIC[])
        AS detection_to_review_seconds,
    COALESCE((SELECT array_agg(
        EXTRACT(EPOCH FROM (first_intents.requested_at_utc - first_approvals.decided_at_utc))::NUMERIC
        ORDER BY first_intents.requested_at_utc - first_approvals.decided_at_utc
    ) FROM first_approvals JOIN first_intents USING (candidate_id)
      WHERE first_intents.requested_at_utc >= first_approvals.decided_at_utc), ARRAY[]::NUMERIC[])
        AS approval_to_conversion_seconds,
    (SELECT COUNT(*)::INTEGER FROM invalid_temporal_facts) AS invalid_temporal_fact_count,
    (SELECT COUNT(DISTINCT quarantine.conversion_intent_id)::INTEGER
     FROM idea_conversion_outcome_quarantine AS quarantine
     JOIN intents USING (conversion_intent_id)) AS invalid_outcome_history_count
"""


__all__ = ["load_opportunity_effectiveness_summary"]
