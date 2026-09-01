-- Persist the source-safe owner receipt returned for accepted downstream work.

ALTER TABLE idea_downstream_submission
    ADD COLUMN IF NOT EXISTS owner_receipt_json JSONB;

ALTER TABLE idea_downstream_submission
    ADD CONSTRAINT ck_idea_downstream_submission_owner_receipt CHECK (
        owner_receipt_json IS NULL OR (
            status = 'accepted_by_downstream'
            AND jsonb_typeof(owner_receipt_json) = 'object'
            AND owner_receipt_json ?& ARRAY[
                'ownerAuthority',
                'ownerRequestId',
                'ownerRealizationId',
                'ownerWorkId',
                'sourceEventVersion',
                'sourceEvidenceFingerprint'
            ]
            AND owner_receipt_json->>'ownerAuthority' = source_authority
            AND (owner_receipt_json->>'ownerRequestId') <> ''
            AND (owner_receipt_json->>'ownerRealizationId') <> ''
            AND (owner_receipt_json->>'sourceEvidenceFingerprint') ~ '^sha256:'
            AND (owner_receipt_json->>'sourceEventVersion') ~ '^[1-9][0-9]*$'
        )
    );

CREATE INDEX IF NOT EXISTS idx_idea_downstream_submission_owner_realization
    ON idea_downstream_submission ((owner_receipt_json->>'ownerRealizationId'))
    WHERE owner_receipt_json IS NOT NULL;
