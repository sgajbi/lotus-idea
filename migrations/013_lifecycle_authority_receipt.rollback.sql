DROP INDEX IF EXISTS uq_idea_data_lifecycle_operation_authority_replay_nonce;
DROP INDEX IF EXISTS uq_idea_data_lifecycle_operation_authority_decision;

ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP CONSTRAINT IF EXISTS ck_idea_data_lifecycle_operation_authority_receipt;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP COLUMN IF EXISTS authority_verified_at_utc;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP COLUMN IF EXISTS authority_rotation_epoch;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP COLUMN IF EXISTS authority_key_id;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP COLUMN IF EXISTS authority_replay_nonce;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP COLUMN IF EXISTS authority_decision_id;
