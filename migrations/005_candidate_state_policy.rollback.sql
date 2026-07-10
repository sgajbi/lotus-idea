ALTER TABLE idea_candidate_record
    DROP CONSTRAINT IF EXISTS ck_idea_candidate_record_state_policy_v1;

DROP TABLE IF EXISTS idea_candidate_state_quarantine;
