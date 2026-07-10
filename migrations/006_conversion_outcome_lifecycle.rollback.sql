DROP INDEX IF EXISTS idx_idea_conversion_outcome_current;
DROP INDEX IF EXISTS idx_idea_conversion_outcome_quarantine_intent;
DROP TABLE IF EXISTS idea_conversion_outcome_quarantine;

ALTER TABLE IF EXISTS idea_conversion_outcome
    DROP CONSTRAINT IF EXISTS fk_idea_conversion_outcome_supersedes,
    DROP CONSTRAINT IF EXISTS uq_idea_conversion_outcome_intent_version,
    DROP CONSTRAINT IF EXISTS ck_idea_conversion_outcome_source_event_version;

ALTER TABLE IF EXISTS idea_conversion_outcome
    DROP COLUMN IF EXISTS actor_subject,
    DROP COLUMN IF EXISTS correction_reason,
    DROP COLUMN IF EXISTS supersedes_conversion_outcome_id,
    DROP COLUMN IF EXISTS source_event_version;
