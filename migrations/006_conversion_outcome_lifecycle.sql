ALTER TABLE idea_conversion_outcome
    ADD COLUMN IF NOT EXISTS source_event_version INTEGER,
    ADD COLUMN IF NOT EXISTS supersedes_conversion_outcome_id TEXT,
    ADD COLUMN IF NOT EXISTS correction_reason TEXT,
    ADD COLUMN IF NOT EXISTS actor_subject TEXT;

WITH ranked_outcomes AS (
    SELECT conversion_outcome_id,
           ROW_NUMBER() OVER (
               PARTITION BY conversion_intent_id
               ORDER BY recorded_at_utc, conversion_outcome_id
           ) AS source_event_version
    FROM idea_conversion_outcome
)
UPDATE idea_conversion_outcome AS outcome
SET source_event_version = ranked.source_event_version,
    actor_subject = COALESCE(outcome.actor_subject, 'legacy-source-event')
FROM ranked_outcomes AS ranked
WHERE outcome.conversion_outcome_id = ranked.conversion_outcome_id
  AND (outcome.source_event_version IS NULL OR outcome.actor_subject IS NULL);

CREATE TABLE IF NOT EXISTS idea_conversion_outcome_quarantine (
    quarantine_id TEXT PRIMARY KEY,
    conversion_intent_id TEXT NOT NULL,
    conversion_outcome_id TEXT NOT NULL UNIQUE,
    source_event_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    outcome_json JSONB NOT NULL,
    diagnostic_code TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    quarantined_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

WITH ordered_outcomes AS (
    SELECT conversion_outcome_id,
           conversion_intent_id,
           source_event_version,
           status,
           ROW_NUMBER() OVER (
               PARTITION BY conversion_intent_id
               ORDER BY source_event_version, recorded_at_utc, conversion_outcome_id
           ) AS stream_position,
           LAG(status) OVER (
               PARTITION BY conversion_intent_id
               ORDER BY source_event_version, recorded_at_utc, conversion_outcome_id
           ) AS previous_status
    FROM idea_conversion_outcome
),
invalid_intents AS (
    SELECT DISTINCT conversion_intent_id
    FROM ordered_outcomes
    WHERE (stream_position = 1 AND status NOT IN ('requested', 'accepted', 'rejected', 'failed'))
       OR (
           stream_position > 1
           AND NOT (
               (previous_status = 'requested' AND status IN ('accepted', 'rejected', 'failed'))
               OR (previous_status = 'accepted' AND status = 'completed')
           )
       )
)
INSERT INTO idea_conversion_outcome_quarantine (
    quarantine_id,
    conversion_intent_id,
    conversion_outcome_id,
    source_event_version,
    status,
    outcome_json,
    diagnostic_code,
    policy_version
)
SELECT 'conversion-outcome-lifecycle-v1:' || outcome.conversion_outcome_id,
       outcome.conversion_intent_id,
       outcome.conversion_outcome_id,
       outcome.source_event_version,
       outcome.status,
       outcome.outcome_json,
       'invalid_legacy_conversion_outcome_history',
       'idea-conversion-outcome-v1'
FROM idea_conversion_outcome AS outcome
JOIN invalid_intents AS invalid
  ON invalid.conversion_intent_id = outcome.conversion_intent_id
ON CONFLICT (conversion_outcome_id) DO NOTHING;

UPDATE idea_conversion_outcome
SET outcome_json = outcome_json || jsonb_build_object(
    'source_event_version', source_event_version,
    'actor_subject', actor_subject,
    'supersedes_conversion_outcome_id', supersedes_conversion_outcome_id,
    'correction_reason', correction_reason
);

ALTER TABLE idea_conversion_outcome
    ALTER COLUMN source_event_version SET NOT NULL,
    ALTER COLUMN actor_subject SET NOT NULL,
    DROP CONSTRAINT IF EXISTS ck_idea_conversion_outcome_source_event_version,
    ADD CONSTRAINT ck_idea_conversion_outcome_source_event_version
        CHECK (source_event_version > 0),
    DROP CONSTRAINT IF EXISTS uq_idea_conversion_outcome_intent_version,
    ADD CONSTRAINT uq_idea_conversion_outcome_intent_version
        UNIQUE (conversion_intent_id, source_event_version),
    DROP CONSTRAINT IF EXISTS fk_idea_conversion_outcome_supersedes,
    ADD CONSTRAINT fk_idea_conversion_outcome_supersedes
        FOREIGN KEY (supersedes_conversion_outcome_id)
        REFERENCES idea_conversion_outcome(conversion_outcome_id);

CREATE INDEX IF NOT EXISTS idx_idea_conversion_outcome_current
    ON idea_conversion_outcome (conversion_intent_id, source_event_version DESC);

CREATE INDEX IF NOT EXISTS idx_idea_conversion_outcome_quarantine_intent
    ON idea_conversion_outcome_quarantine (conversion_intent_id, source_event_version);
