-- Persist independently verified Archive posture receipts for linked Idea evidence.

ALTER TABLE idea_data_lifecycle_operation ADD COLUMN archive_decision_id TEXT;
ALTER TABLE idea_data_lifecycle_operation ADD COLUMN archive_document_id TEXT;
ALTER TABLE idea_data_lifecycle_operation ADD COLUMN archive_evidence_pack_id TEXT;
ALTER TABLE idea_data_lifecycle_operation ADD COLUMN archive_payload_digest TEXT;
ALTER TABLE idea_data_lifecycle_operation ADD COLUMN archive_key_id TEXT;
ALTER TABLE idea_data_lifecycle_operation ADD COLUMN archive_verified_at_utc TIMESTAMPTZ;

ALTER TABLE idea_data_lifecycle_operation
    ADD CONSTRAINT ck_idea_data_lifecycle_operation_archive_receipt
    CHECK (
        (archive_decision_id IS NULL
         AND archive_document_id IS NULL
         AND archive_evidence_pack_id IS NULL
         AND archive_payload_digest IS NULL
         AND archive_key_id IS NULL
         AND archive_verified_at_utc IS NULL)
        OR
        (dry_run = FALSE
         AND archive_decision_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND archive_document_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND archive_evidence_pack_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND archive_payload_digest ~ '^sha256:[0-9a-f]{64}$'
         AND archive_key_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND archive_verified_at_utc >= requested_at_utc)
    );

CREATE UNIQUE INDEX uq_idea_data_lifecycle_operation_archive_decision_applied
    ON idea_data_lifecycle_operation (archive_decision_id)
    WHERE archive_decision_id IS NOT NULL AND decision = 'applied';

CREATE UNIQUE INDEX uq_idea_data_lifecycle_operation_archive_digest_applied
    ON idea_data_lifecycle_operation (archive_payload_digest)
    WHERE archive_payload_digest IS NOT NULL AND decision = 'applied';
