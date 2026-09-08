ALTER TABLE IF EXISTS idea_idempotency_record
    DROP CONSTRAINT IF EXISTS idea_idempotency_record_pkey;

ALTER TABLE IF EXISTS idea_idempotency_record
    DROP COLUMN IF EXISTS idempotency_record_identity;
