DROP INDEX IF EXISTS idx_idea_presentation_receipt_candidate_accepted_time;
DROP INDEX IF EXISTS idx_idea_conversion_outcome_intent_accepted_time;
DROP INDEX IF EXISTS idx_idea_conversion_intent_candidate_accepted_time;
DROP INDEX IF EXISTS idx_idea_feedback_event_candidate_accepted_time;
DROP INDEX IF EXISTS idx_idea_review_decision_candidate_accepted_time;

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    DROP CONSTRAINT IF EXISTS ck_idea_presentation_receipt_acceptance_time_source,
    DROP COLUMN IF EXISTS acceptance_time_source,
    DROP COLUMN IF EXISTS accepted_at_utc;

DO $$
BEGIN
    IF to_regclass('public.idea_conversion_outcome') IS NOT NULL THEN
        UPDATE idea_conversion_outcome
        SET outcome_json = outcome_json - 'accepted_at_utc' - 'acceptance_time_source';
    END IF;
END
$$;

ALTER TABLE IF EXISTS idea_conversion_outcome
    DROP CONSTRAINT IF EXISTS ck_idea_conversion_outcome_acceptance_time_source,
    DROP COLUMN IF EXISTS acceptance_time_source,
    DROP COLUMN IF EXISTS accepted_at_utc;

DO $$
BEGIN
    IF to_regclass('public.idea_conversion_intent') IS NOT NULL THEN
        UPDATE idea_conversion_intent
        SET intent_json = intent_json - 'accepted_at_utc' - 'acceptance_time_source';
    END IF;
END
$$;

ALTER TABLE IF EXISTS idea_conversion_intent
    DROP CONSTRAINT IF EXISTS ck_idea_conversion_intent_acceptance_time_source,
    DROP COLUMN IF EXISTS acceptance_time_source,
    DROP COLUMN IF EXISTS accepted_at_utc;

DO $$
BEGIN
    IF to_regclass('public.idea_feedback_event') IS NOT NULL THEN
        UPDATE idea_feedback_event
        SET feedback_json = feedback_json - 'accepted_at_utc' - 'acceptance_time_source';
    END IF;
END
$$;

ALTER TABLE IF EXISTS idea_feedback_event
    DROP CONSTRAINT IF EXISTS ck_idea_feedback_event_acceptance_time_source,
    DROP COLUMN IF EXISTS acceptance_time_source,
    DROP COLUMN IF EXISTS accepted_at_utc;

DO $$
BEGIN
    IF to_regclass('public.idea_review_decision') IS NOT NULL THEN
        UPDATE idea_review_decision
        SET decision_json = decision_json - 'accepted_at_utc' - 'acceptance_time_source';
    END IF;
END
$$;

ALTER TABLE IF EXISTS idea_review_decision
    DROP CONSTRAINT IF EXISTS ck_idea_review_decision_acceptance_time_source,
    DROP COLUMN IF EXISTS acceptance_time_source,
    DROP COLUMN IF EXISTS accepted_at_utc;
