DROP INDEX IF EXISTS uq_idea_data_lifecycle_operation_archive_digest_applied;
DROP INDEX IF EXISTS uq_idea_data_lifecycle_operation_archive_decision_applied;

ALTER TABLE IF EXISTS idea_data_lifecycle_operation
    DROP CONSTRAINT IF EXISTS ck_idea_data_lifecycle_operation_archive_receipt;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation DROP COLUMN IF EXISTS archive_verified_at_utc;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation DROP COLUMN IF EXISTS archive_key_id;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation DROP COLUMN IF EXISTS archive_payload_digest;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation DROP COLUMN IF EXISTS archive_evidence_pack_id;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation DROP COLUMN IF EXISTS archive_document_id;
ALTER TABLE IF EXISTS idea_data_lifecycle_operation DROP COLUMN IF EXISTS archive_decision_id;
