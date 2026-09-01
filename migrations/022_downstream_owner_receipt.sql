-- Persist source-safe owner receipts for terminal accepted or rejected downstream work.

ALTER TABLE idea_downstream_submission
    ADD COLUMN IF NOT EXISTS owner_receipt_json JSONB;

ALTER TABLE idea_downstream_submission
    ADD CONSTRAINT ck_idea_downstream_submission_owner_receipt CHECK (
        owner_receipt_json IS NULL OR (
            status IN ('accepted_by_downstream', 'rejected_by_downstream')
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

CREATE TABLE IF NOT EXISTS idea_advise_realization_history (
    support_reference TEXT PRIMARY KEY
        REFERENCES idea_downstream_submission (support_reference) ON DELETE CASCADE,
    realization_id TEXT NOT NULL UNIQUE,
    intake_id TEXT NOT NULL UNIQUE,
    current_source_event_version INTEGER NOT NULL,
    history_json JSONB NOT NULL,
    persisted_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_idea_advise_realization_version CHECK (current_source_event_version > 0),
    CONSTRAINT ck_idea_advise_realization_history_json CHECK (
        jsonb_typeof(history_json) = 'object'
        AND jsonb_typeof(history_json->'outcomes') = 'array'
        AND jsonb_array_length(history_json->'outcomes') > 0
    )
);
