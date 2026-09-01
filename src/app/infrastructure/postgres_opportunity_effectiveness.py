from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from app.infrastructure.postgres_codecs import read_row_value
from app.infrastructure.postgres_protocols import PostgresConnection
from app.domain.ranking_evaluation import (
    MAX_RANKING_PRESENTATION_FACTS,
    RankedOpportunityJudgment,
    RankingPresentationFact,
    RankingRelevanceGrade,
)
from app.ports.idea_repository import (
    OpportunityEffectivenessRepositorySummary,
    OpportunityFamilyEffectivenessRepositorySummary,
)


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
                MAX_RANKING_PRESENTATION_FACTS + 1,
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
    invalid_presentation_fact_count = _integer(row, "invalid_presentation_fact_count")
    if invalid_presentation_fact_count:
        raise RuntimeError("opportunity effectiveness contains invalid presentation evidence")
    invalid_ranking_judgment_count = _integer(row, "invalid_ranking_judgment_count")
    if invalid_ranking_judgment_count:
        raise RuntimeError("opportunity effectiveness contains conflicting ranking judgments")
    ranking_presentation_fact_count = _integer(row, "ranking_presentation_fact_count")
    if ranking_presentation_fact_count > MAX_RANKING_PRESENTATION_FACTS:
        raise RuntimeError("opportunity effectiveness exceeds the ranking presentation fact bound")
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
        presented_opportunity_count=_integer(row, "presented_opportunity_count"),
        top_ranked_presented_opportunity_count=_integer(
            row, "top_ranked_presented_opportunity_count"
        ),
        top_ranked_accepted_opportunity_count=_integer(
            row, "top_ranked_accepted_opportunity_count"
        ),
        family_effectiveness=_family_effectiveness(row),
        family_counts=_counts(row, "family_counts"),
        score_band_counts=_counts(row, "score_band_counts"),
        latest_review_action_counts=_counts(row, "latest_review_action_counts"),
        feedback_reason_counts=_counts(row, "feedback_reason_counts"),
        current_downstream_outcome_counts=_counts(row, "current_downstream_outcome_counts"),
        downstream_submission_posture_counts=_counts(row, "downstream_submission_posture_counts"),
        detection_to_review_seconds=_decimals(row, "detection_to_review_seconds"),
        approval_to_conversion_seconds=_decimals(row, "approval_to_conversion_seconds"),
        ranking_presentation_facts=_ranking_presentation_facts(row),
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


def _family_effectiveness(
    row: Any,
) -> tuple[OpportunityFamilyEffectivenessRepositorySummary, ...]:
    value = read_row_value(row, "family_effectiveness")
    if not isinstance(value, (list, tuple)):
        raise TypeError("family_effectiveness must be an array")
    result: list[OpportunityFamilyEffectivenessRepositorySummary] = []
    fields = (
        "generated_opportunity_count",
        "presented_opportunity_count",
        "reviewed_opportunity_count",
        "approved_opportunity_count",
        "rejected_opportunity_count",
        "suppressed_opportunity_count",
        "duplicate_suppressed_opportunity_count",
        "feedback_opportunity_count",
        "conversion_opportunity_count",
        "conversion_intent_count",
        "downstream_accepted_count",
        "downstream_rejected_count",
        "downstream_uncertain_count",
    )
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError("family_effectiveness entries must be mappings")
        family = item.get("family")
        if not isinstance(family, str):
            raise TypeError("family_effectiveness family must be a string")
        counts: dict[str, int] = {}
        for field in fields:
            count = item.get(field)
            if isinstance(count, bool) or not isinstance(count, int):
                raise TypeError(f"family_effectiveness {field} must be an integer")
            counts[field] = count
        result.append(OpportunityFamilyEffectivenessRepositorySummary(family=family, **counts))
    return tuple(result)


def _decimals(row: Any, key: str) -> tuple[Decimal, ...]:
    value = read_row_value(row, key)
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{key} must be an array")
    return tuple(item if isinstance(item, Decimal) else Decimal(str(item)) for item in value)


def _ranking_presentation_facts(row: Any) -> tuple[RankingPresentationFact, ...]:
    value = read_row_value(row, "ranking_presentation_facts")
    if not isinstance(value, (list, tuple)):
        raise TypeError("ranking_presentation_facts must be an array")
    facts: list[RankingPresentationFact] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise TypeError("ranking_presentation_facts entries must be mappings")
        grade = item.get("relevance_grade")
        facts.append(
            RankingPresentationFact(
                queue_snapshot_digest=str(item["queue_snapshot_digest"]),
                tenant_id=str(item["tenant_id"]),
                presented_at_utc=_timestamp(item["presented_at_utc"]),
                visible_opportunity_count=_mapping_integer(item, "visible_opportunity_count"),
                queue_policy_version=str(item["queue_policy_version"]),
                ranking_policy_version=str(item["ranking_policy_version"]),
                surface=str(item["surface"]),
                producer=str(item["producer"]),
                economic_identity_id=str(item["economic_identity_id"]),
                judgment=RankedOpportunityJudgment(
                    rank=_mapping_integer(item, "rank"),
                    relevance_grade=(
                        RankingRelevanceGrade(_mapping_integer(item, "relevance_grade"))
                        if grade is not None
                        else None
                    ),
                ),
            )
        )
    return tuple(facts)


def _mapping_integer(item: Mapping[str, Any], key: str) -> int:
    value = item.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"ranking presentation {key} must be an integer")
    return value


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise TypeError("ranking presentation timestamp must be an ISO-8601 string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


_SUMMARY_QUERY = """
/* lotus-idea opportunity-effectiveness-summary-v1 */
WITH parameters AS (
    SELECT
        %s::TEXT AS tenant_id,
        %s::TIMESTAMPTZ AS window_start_utc,
        %s::TIMESTAMPTZ AS window_end_utc,
        %s::TIMESTAMPTZ AS evaluated_at_utc,
        %s::INTEGER AS bounded_limit,
        %s::INTEGER AS ranking_fact_limit
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
        intent.candidate_id,
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
presentation_receipts AS (
    SELECT DISTINCT
        receipt.receipt_id,
        receipt.candidate_id,
        receipt.tenant_id,
        receipt.presented_at_utc,
        receipt.rank_at_presentation,
        receipt.visible_candidate_count,
        receipt.queue_snapshot_digest,
        receipt.queue_policy_version,
        receipt.ranking_policy_version,
        receipt.surface,
        receipt.producer,
        cohort.business_identity_id AS economic_identity_id,
        COALESCE(
            history.evidence_hash,
            cohort.candidate_json->'evidence_packet'->'lineage_ref'->>'content_hash'
        ) AS evidence_hash,
        (
            SELECT MIN(version_change.changed_at_utc)
            FROM (
                SELECT later_history.recorded_at_utc AS changed_at_utc
                FROM idea_candidate_version_history AS later_history
                WHERE later_history.candidate_id = receipt.candidate_id
                  AND later_history.recorded_at_utc > receipt.presented_at_utc
                  AND (
                      later_history.material_version <> receipt.candidate_material_version
                      OR later_history.evidence_version <> receipt.candidate_evidence_version
                  )
                UNION ALL
                SELECT cohort.updated_at_utc
                WHERE cohort.updated_at_utc > receipt.presented_at_utc
                  AND (
                      cohort.material_version <> receipt.candidate_material_version
                      OR cohort.evidence_version <> receipt.candidate_evidence_version
                  )
            ) AS version_change
        ) AS valid_until_utc
    FROM idea_candidate_presentation_receipt AS receipt
    JOIN cohort USING (candidate_id)
    LEFT JOIN idea_candidate_version_history AS history
      ON history.candidate_id = receipt.candidate_id
     AND history.material_version = receipt.candidate_material_version
     AND history.evidence_version = receipt.candidate_evidence_version
     AND history.recorded_at_utc <= receipt.presented_at_utc
    CROSS JOIN parameters
    WHERE receipt.tenant_id = parameters.tenant_id
      AND receipt.presented_at_utc <= parameters.evaluated_at_utc
    ORDER BY receipt.presented_at_utc, receipt.queue_snapshot_digest,
             receipt.rank_at_presentation, receipt.receipt_id
    LIMIT (SELECT ranking_fact_limit FROM parameters)
),
ranking_human_judgments AS (
    SELECT
        receipt.receipt_id,
        review.decided_at_utc AS occurred_at_utc,
        CASE review.action
            WHEN 'approve_for_conversion' THEN 2
            WHEN 'reject' THEN 0
            WHEN 'suppress' THEN 0
        END::INTEGER AS relevance_grade
    FROM presentation_receipts AS receipt
    JOIN idea_review_decision AS review USING (candidate_id)
    CROSS JOIN parameters
    WHERE review.action IN ('approve_for_conversion', 'reject', 'suppress')
      AND review.decision_json->>'evidence_content_hash' = receipt.evidence_hash
      AND review.decided_at_utc >= receipt.presented_at_utc
      AND review.decided_at_utc <= parameters.evaluated_at_utc
      AND (receipt.valid_until_utc IS NULL OR review.decided_at_utc < receipt.valid_until_utc)
    UNION ALL
    SELECT
        receipt.receipt_id,
        feedback.recorded_at_utc,
        CASE feedback.feedback_outcome
            WHEN 'useful' THEN 1
            WHEN 'not_useful' THEN 0
        END::INTEGER AS relevance_grade
    FROM presentation_receipts AS receipt
    JOIN idea_feedback_event AS feedback USING (candidate_id)
    CROSS JOIN parameters
    WHERE feedback.feedback_json->>'evidence_content_hash' = receipt.evidence_hash
      AND feedback.recorded_at_utc >= receipt.presented_at_utc
      AND feedback.recorded_at_utc <= parameters.evaluated_at_utc
      AND (receipt.valid_until_utc IS NULL OR feedback.recorded_at_utc < receipt.valid_until_utc)
),
ranking_latest_human_time AS (
    SELECT receipt_id, MAX(occurred_at_utc) AS occurred_at_utc
    FROM ranking_human_judgments
    GROUP BY receipt_id
),
ranking_latest_human AS (
    SELECT judgment.receipt_id, MAX(judgment.relevance_grade)::INTEGER AS relevance_grade
    FROM ranking_human_judgments AS judgment
    JOIN ranking_latest_human_time USING (receipt_id, occurred_at_utc)
    GROUP BY judgment.receipt_id
),
invalid_ranking_judgments AS (
    SELECT judgment.receipt_id
    FROM ranking_human_judgments AS judgment
    JOIN ranking_latest_human_time USING (receipt_id, occurred_at_utc)
    GROUP BY judgment.receipt_id
    HAVING COUNT(DISTINCT judgment.relevance_grade) > 1
),
invalid_presentation_facts AS (
    SELECT receipt.receipt_id
    FROM idea_candidate_presentation_receipt AS receipt
    JOIN cohort USING (candidate_id)
    CROSS JOIN parameters
    WHERE receipt.presented_at_utc <= parameters.evaluated_at_utc
      AND (
          receipt.tenant_id <> parameters.tenant_id
          OR receipt.presented_at_utc < cohort.generated_at_utc
          OR (
              NOT EXISTS (
                  SELECT 1
                  FROM idea_candidate_version_history AS history
                  WHERE history.candidate_id = receipt.candidate_id
                    AND history.material_version = receipt.candidate_material_version
                    AND history.evidence_version = receipt.candidate_evidence_version
                    AND history.recorded_at_utc <= receipt.presented_at_utc
              )
              AND NOT (
                  cohort.material_version = receipt.candidate_material_version
                  AND cohort.evidence_version = receipt.candidate_evidence_version
                  AND cohort.updated_at_utc <= receipt.presented_at_utc
              )
          )
      )
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
family_effectiveness AS (
    SELECT
        family,
        COUNT(*)::INTEGER AS generated_opportunity_count,
        (SELECT COUNT(DISTINCT receipt.candidate_id)::INTEGER
         FROM presentation_receipts AS receipt
         JOIN cohort AS presented_candidate USING (candidate_id)
         WHERE presented_candidate.family = family_cohort.family)
            AS presented_opportunity_count,
        (SELECT COUNT(*)::INTEGER FROM latest_reviews AS review
         JOIN cohort AS reviewed_candidate USING (candidate_id)
         WHERE reviewed_candidate.family = family_cohort.family)
            AS reviewed_opportunity_count,
        (SELECT COUNT(*)::INTEGER FROM latest_reviews AS review
         JOIN cohort AS reviewed_candidate USING (candidate_id)
         WHERE reviewed_candidate.family = family_cohort.family
           AND review.action = 'approve_for_conversion')
            AS approved_opportunity_count,
        (SELECT COUNT(*)::INTEGER FROM latest_reviews AS review
         JOIN cohort AS reviewed_candidate USING (candidate_id)
         WHERE reviewed_candidate.family = family_cohort.family
           AND review.action = 'reject')
            AS rejected_opportunity_count,
        (SELECT COUNT(*)::INTEGER FROM cohort AS suppressed_candidate
         LEFT JOIN latest_reviews AS review USING (candidate_id)
         WHERE suppressed_candidate.family = family_cohort.family
           AND (review.action = 'suppress'
             OR (review.candidate_id IS NULL
               AND suppressed_candidate.candidate_json->>'suppression_reason' IS NOT NULL)))
            AS suppressed_opportunity_count,
        (SELECT COUNT(*)::INTEGER FROM cohort AS suppressed_candidate
         LEFT JOIN latest_reviews AS review USING (candidate_id)
         WHERE suppressed_candidate.family = family_cohort.family
           AND ((review.action = 'suppress' AND review.suppression_reason = 'duplicate')
             OR (review.candidate_id IS NULL
               AND suppressed_candidate.candidate_json->>'suppression_reason' = 'duplicate')))
            AS duplicate_suppressed_opportunity_count,
        (SELECT COUNT(DISTINCT event.candidate_id)::INTEGER FROM feedback AS event
         JOIN cohort AS feedback_candidate USING (candidate_id)
         WHERE feedback_candidate.family = family_cohort.family)
            AS feedback_opportunity_count,
        (SELECT COUNT(DISTINCT intent.candidate_id)::INTEGER FROM intents AS intent
         JOIN cohort AS conversion_candidate USING (candidate_id)
         WHERE conversion_candidate.family = family_cohort.family)
            AS conversion_opportunity_count,
        (SELECT COUNT(*)::INTEGER FROM intents AS intent
         JOIN cohort AS conversion_candidate USING (candidate_id)
         WHERE conversion_candidate.family = family_cohort.family)
            AS conversion_intent_count,
        (SELECT COUNT(*)::INTEGER FROM current_outcomes AS outcome
         JOIN cohort AS outcome_candidate USING (candidate_id)
         WHERE outcome_candidate.family = family_cohort.family
           AND outcome.status IN ('accepted', 'completed'))
            AS downstream_accepted_count,
        (SELECT COUNT(*)::INTEGER FROM current_outcomes AS outcome
         JOIN cohort AS outcome_candidate USING (candidate_id)
         WHERE outcome_candidate.family = family_cohort.family
           AND outcome.status = 'rejected')
            AS downstream_rejected_count,
        (SELECT COUNT(*)::INTEGER FROM current_outcomes AS outcome
         JOIN cohort AS outcome_candidate USING (candidate_id)
         WHERE outcome_candidate.family = family_cohort.family
           AND outcome.status IN ('not_reported', 'requested'))
            AS downstream_uncertain_count
    FROM cohort AS family_cohort
    GROUP BY family
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
    (SELECT COUNT(DISTINCT candidate_id)::INTEGER FROM presentation_receipts)
        AS presented_opportunity_count,
    (SELECT COUNT(DISTINCT candidate_id)::INTEGER
     FROM presentation_receipts
     WHERE rank_at_presentation = 1)
        AS top_ranked_presented_opportunity_count,
    (SELECT COUNT(DISTINCT receipt.candidate_id)::INTEGER
     FROM presentation_receipts AS receipt
     CROSS JOIN parameters
     WHERE receipt.rank_at_presentation = 1
       AND EXISTS (
           SELECT 1
           FROM idea_review_decision AS review
           WHERE review.candidate_id = receipt.candidate_id
             AND review.action = 'approve_for_conversion'
             AND review.decision_json->>'evidence_content_hash' = receipt.evidence_hash
             AND review.decided_at_utc >= receipt.presented_at_utc
             AND review.decided_at_utc <= parameters.evaluated_at_utc
       )) AS top_ranked_accepted_opportunity_count,
    (SELECT COUNT(*)::INTEGER FROM submissions AS submission CROSS JOIN parameters
     WHERE EXISTS (
         SELECT 1 FROM jsonb_array_elements(submission.audit_json) AS audit
         WHERE audit->>'action' = 'reconciled'
           AND (audit->>'occurredAtUtc')::TIMESTAMPTZ <= parameters.evaluated_at_utc
     )) AS reconciled_submission_count,
    COALESCE((SELECT jsonb_object_agg(value, count) FROM family_counts), '{}'::JSONB)
        AS family_counts,
    COALESCE((SELECT jsonb_agg(to_jsonb(family_effectiveness) ORDER BY family)
              FROM family_effectiveness), '[]'::JSONB)
        AS family_effectiveness,
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
    COALESCE((
        SELECT jsonb_agg(
            jsonb_build_object(
                'queue_snapshot_digest', receipt.queue_snapshot_digest,
                'tenant_id', receipt.tenant_id,
                'presented_at_utc', receipt.presented_at_utc,
                'visible_opportunity_count', receipt.visible_candidate_count,
                'queue_policy_version', receipt.queue_policy_version,
                'ranking_policy_version', receipt.ranking_policy_version,
                'surface', receipt.surface,
                'producer', receipt.producer,
                'economic_identity_id', receipt.economic_identity_id,
                'rank', receipt.rank_at_presentation,
                'relevance_grade', CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM intents AS intent
                        JOIN current_outcomes AS outcome USING (conversion_intent_id)
                        WHERE intent.candidate_id = receipt.candidate_id
                          AND intent.intent_json->>'evidence_content_hash' = receipt.evidence_hash
                          AND intent.requested_at_utc >= receipt.presented_at_utc
                          AND intent.requested_at_utc <= parameters.evaluated_at_utc
                          AND (
                              receipt.valid_until_utc IS NULL
                              OR intent.requested_at_utc < receipt.valid_until_utc
                          )
                          AND outcome.status IN ('accepted', 'completed')
                    ) THEN 3
                    ELSE ranking_latest_human.relevance_grade
                END
            )
            ORDER BY receipt.queue_snapshot_digest, receipt.rank_at_presentation,
                     receipt.receipt_id
        )
        FROM presentation_receipts AS receipt
        LEFT JOIN ranking_latest_human USING (receipt_id)
        CROSS JOIN parameters
    ), '[]'::JSONB) AS ranking_presentation_facts,
    (SELECT COUNT(*)::INTEGER FROM invalid_temporal_facts) AS invalid_temporal_fact_count,
    (SELECT COUNT(DISTINCT quarantine.conversion_intent_id)::INTEGER
     FROM idea_conversion_outcome_quarantine AS quarantine
     JOIN intents USING (conversion_intent_id)) AS invalid_outcome_history_count,
    (SELECT COUNT(*)::INTEGER FROM invalid_presentation_facts)
        AS invalid_presentation_fact_count,
    (SELECT COUNT(*)::INTEGER FROM invalid_ranking_judgments)
        AS invalid_ranking_judgment_count,
    (SELECT COUNT(*)::INTEGER FROM presentation_receipts)
        AS ranking_presentation_fact_count
"""


__all__ = ["load_opportunity_effectiveness_summary"]
