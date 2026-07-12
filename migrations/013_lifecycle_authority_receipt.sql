-- Persist verified bank lifecycle-authority receipt identity for applied operations.
-- Existing operations and dry-run previews remain explicitly unattested.

ALTER TABLE idea_data_lifecycle_operation
    ADD COLUMN authority_decision_id TEXT;
ALTER TABLE idea_data_lifecycle_operation
    ADD COLUMN authority_replay_nonce TEXT;
ALTER TABLE idea_data_lifecycle_operation
    ADD COLUMN authority_key_id TEXT;
ALTER TABLE idea_data_lifecycle_operation
    ADD COLUMN authority_rotation_epoch INTEGER;
ALTER TABLE idea_data_lifecycle_operation
    ADD COLUMN authority_verified_at_utc TIMESTAMPTZ;

ALTER TABLE idea_data_lifecycle_operation
    ADD CONSTRAINT ck_idea_data_lifecycle_operation_authority_receipt
    CHECK (
        (authority_decision_id IS NULL
         AND authority_replay_nonce IS NULL
         AND authority_key_id IS NULL
         AND authority_rotation_epoch IS NULL
         AND authority_verified_at_utc IS NULL)
        OR
        (dry_run = FALSE
         AND authority_decision_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND authority_replay_nonce ~ '^[0-9a-f]{64}$'
         AND authority_key_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND authority_rotation_epoch > 0
         AND authority_verified_at_utc >= requested_at_utc)
    );

CREATE UNIQUE INDEX uq_idea_data_lifecycle_operation_authority_decision
    ON idea_data_lifecycle_operation (authority_decision_id)
    WHERE authority_decision_id IS NOT NULL;

CREATE UNIQUE INDEX uq_idea_data_lifecycle_operation_authority_replay_nonce
    ON idea_data_lifecycle_operation (authority_replay_nonce)
    WHERE authority_replay_nonce IS NOT NULL;
