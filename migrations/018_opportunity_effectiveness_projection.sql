-- Index-supported cohort selection for RFC-0002 opportunity effectiveness.
-- generated_at_utc remains available after governed payload redaction so aggregate
-- retention evidence does not depend on parsing or retaining the candidate JSON.

ALTER TABLE idea_candidate_record
    ADD COLUMN generated_at_utc TIMESTAMPTZ;

UPDATE idea_candidate_record
SET generated_at_utc = (candidate_json->>'created_at_utc')::TIMESTAMPTZ;

ALTER TABLE idea_candidate_record
    ALTER COLUMN generated_at_utc SET NOT NULL;

CREATE INDEX idx_idea_candidate_record_effectiveness_cohort
    ON idea_candidate_record (generated_at_utc, candidate_id);

CREATE INDEX idx_idea_data_lifecycle_effectiveness_scope
    ON idea_data_lifecycle_control (tenant_id, candidate_id)
    WHERE state IN ('active', 'held');
