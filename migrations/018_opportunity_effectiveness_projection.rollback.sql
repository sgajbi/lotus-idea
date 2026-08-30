DROP INDEX IF EXISTS idx_idea_data_lifecycle_effectiveness_scope;
DROP INDEX IF EXISTS idx_idea_candidate_record_effectiveness_cohort;

ALTER TABLE IF EXISTS idea_candidate_record
    DROP COLUMN IF EXISTS generated_at_utc;
