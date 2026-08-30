-- Version review feedback as a governed usefulness outcome plus an actionable reason.

ALTER TABLE idea_feedback_event
    ADD COLUMN feedback_taxonomy_version TEXT,
    ADD COLUMN feedback_outcome TEXT,
    ADD COLUMN feedback_reason TEXT,
    ADD COLUMN migration_source_outcome TEXT;

WITH mapped AS (
    SELECT feedback_event_id,
           feedback_json->'feedback'->>'outcome' AS source_outcome,
           CASE
               WHEN feedback_json->'feedback'->>'outcome' = 'useful' THEN 'useful'
               WHEN feedback_json->'feedback'->>'outcome' IN (
                   'not_useful', 'duplicate', 'too_late', 'missing_context', 'unsupported_claim'
               ) THEN 'not_useful'
               ELSE NULL
           END AS governed_outcome,
           CASE feedback_json->'feedback'->>'outcome'
               WHEN 'useful' THEN 'relevant'
               WHEN 'not_useful' THEN 'not_relevant'
               WHEN 'duplicate' THEN 'duplicate'
               WHEN 'too_late' THEN 'wrong_timing'
               WHEN 'missing_context' THEN 'insufficient_evidence'
               WHEN 'unsupported_claim' THEN 'insufficient_evidence'
               ELSE NULL
           END AS governed_reason
    FROM idea_feedback_event
)
UPDATE idea_feedback_event AS event
SET feedback_taxonomy_version = 'idea-feedback-taxonomy-v1',
    feedback_outcome = mapped.governed_outcome,
    feedback_reason = mapped.governed_reason,
    migration_source_outcome = mapped.source_outcome,
    feedback_json = jsonb_set(
        jsonb_set(
            jsonb_set(
                event.feedback_json,
                '{feedback,taxonomy_version}',
                to_jsonb('idea-feedback-taxonomy-v1'::TEXT),
                TRUE
            ),
            '{feedback,outcome}',
            to_jsonb(mapped.governed_outcome),
            TRUE
        ),
        '{feedback,reason}',
        to_jsonb(mapped.governed_reason),
        TRUE
    )
FROM mapped
WHERE mapped.feedback_event_id = event.feedback_event_id;

UPDATE idea_feedback_event AS event
SET feedback_json = jsonb_set(
        event.feedback_json,
        '{evaluation_context}',
        jsonb_build_object(
            'candidate_family', candidate.family,
            'candidate_identity_policy_version', candidate.identity_policy_version,
            'score_policy_version', candidate.candidate_json->'score'->>'policy_version',
            'score', candidate.candidate_json->'score'->>'score',
            'evidence_supportability',
                candidate.candidate_json->'evidence_packet'->>'supportability',
            'ranking_policy_version', 'idea-deterministic-ranking-v1',
            'queue_priority_bucket',
                CASE
                    WHEN candidate.candidate_json->'score' IS NULL THEN NULL
                    WHEN candidate.candidate_json->'score'->>'policy_version' NOT IN (
                        'allocation-drift-mandate-review-v1',
                        'bond-maturity-review-v1',
                        'cashflow-liquidity-review-v1',
                        'concentration-attention-v1',
                        'drawdown-review-attention-v1',
                        'high-volatility-attention-v1',
                        'idea-weighted-evidence-score-v1',
                        'idle-liquidity-v1',
                        'mandate-restriction-review-v1',
                        'missing-benchmark-review-v1',
                        'missing-risk-profile-review-v1',
                        'missing-suitability-context-review-v1',
                        'underperformance-review-v1'
                    ) THEN NULL
                    WHEN (candidate.candidate_json->'score'->>'score')::NUMERIC >= 85
                        THEN 'critical'
                    WHEN (candidate.candidate_json->'score'->>'score')::NUMERIC >= 70
                        THEN 'high'
                    WHEN (candidate.candidate_json->'score'->>'score')::NUMERIC >= 50
                        THEN 'standard'
                    ELSE 'watchlist'
                END
        ),
        TRUE
    )
FROM idea_candidate_record AS candidate
WHERE candidate.candidate_id = event.candidate_id;

ALTER TABLE idea_feedback_event
    ALTER COLUMN feedback_taxonomy_version SET NOT NULL,
    ALTER COLUMN feedback_outcome SET NOT NULL,
    ALTER COLUMN feedback_reason SET NOT NULL,
    ADD CONSTRAINT ck_idea_feedback_event_taxonomy_values CHECK (
        feedback_taxonomy_version = 'idea-feedback-taxonomy-v1'
        AND (
            (feedback_outcome = 'useful' AND feedback_reason = 'relevant')
            OR
            (feedback_outcome = 'not_useful' AND feedback_reason IN (
                'not_relevant',
                'already_known',
                'wrong_timing',
                'insufficient_evidence',
                'wrong_priority',
                'duplicate',
                'client_specific_constraint'
            ))
        )
    ),
    ADD CONSTRAINT ck_idea_feedback_event_taxonomy_json CHECK (
        feedback_json->'feedback'->>'taxonomy_version' = feedback_taxonomy_version
        AND feedback_json->'feedback'->>'outcome' = feedback_outcome
        AND feedback_json->'feedback'->>'reason' = feedback_reason
    );

CREATE INDEX idx_idea_feedback_event_offline_evaluation
    ON idea_feedback_event (
        candidate_id,
        feedback_taxonomy_version,
        feedback_outcome,
        feedback_reason,
        recorded_at_utc
    );

ALTER TABLE idea_outbox_event
    ADD COLUMN feedback_taxonomy_migration_source_event_type TEXT,
    ADD COLUMN feedback_taxonomy_migration_source_payload JSONB;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM idea_outbox_event AS outbox
        LEFT JOIN idea_feedback_event AS feedback
          ON feedback.candidate_id = outbox.aggregate_id
         AND feedback.recorded_at_utc = outbox.occurred_at_utc
        WHERE outbox.event_type = 'idea.feedback.recorded.v1'
        GROUP BY outbox.outbox_event_id
        HAVING COUNT(feedback.feedback_event_id) <> 1
    ) THEN
        RAISE EXCEPTION
            'legacy feedback outbox event must match exactly one durable feedback event';
    END IF;
END
$$;

ALTER TABLE idea_outbox_event DROP CONSTRAINT ck_idea_outbox_event_event_type;

UPDATE idea_outbox_event AS outbox
SET feedback_taxonomy_migration_source_event_type = outbox.event_type,
    feedback_taxonomy_migration_source_payload = outbox.payload_json,
    event_type = 'idea.feedback.recorded.v2',
    payload_json = jsonb_build_object(
        'feedback_outcome', feedback.feedback_outcome,
        'feedback_reason', feedback.feedback_reason,
        'feedback_taxonomy_version', feedback.feedback_taxonomy_version,
        'actor_role', feedback.feedback_json->>'actor_role'
    )
FROM idea_feedback_event AS feedback
WHERE outbox.event_type = 'idea.feedback.recorded.v1'
  AND feedback.candidate_id = outbox.aggregate_id
  AND feedback.recorded_at_utc = outbox.occurred_at_utc;

ALTER TABLE idea_outbox_event
    ADD CONSTRAINT ck_idea_outbox_event_event_type CHECK (
        event_type IN (
            'idea.candidate.persisted.v1',
            'idea.candidate.evidence_refreshed.v1',
            'idea.candidate.material_version_created.v1',
            'idea.candidate.recurrent_condition_reopened.v1',
            'idea.lifecycle.transitioned.v1',
            'idea.review.decision_recorded.v1',
            'idea.feedback.recorded.v2',
            'idea.conversion.intent_requested.v1',
            'idea.conversion.outcome_recorded.v1',
            'idea.report_evidence_pack.requested.v1'
        )
    );
