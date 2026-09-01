DROP TABLE IF EXISTS idea_advise_realization_history;

DROP INDEX IF EXISTS idx_idea_downstream_submission_owner_realization;

ALTER TABLE IF EXISTS idea_downstream_submission
    DROP CONSTRAINT IF EXISTS ck_idea_downstream_submission_owner_receipt,
    DROP COLUMN IF EXISTS owner_receipt_json;
