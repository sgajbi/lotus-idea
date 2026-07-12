-- Persist a bounded, verified lotus-ai provider-retention receipt with AI lineage.
-- This receipt reports provider posture only and cannot authorize Idea lifecycle actions.

ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN provider_retention_confirmation_id TEXT;
ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN provider_retention_confirmation_ref TEXT;
ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN provider_retention_replay_nonce TEXT;

ALTER TABLE idea_ai_explanation_lineage
    ADD CONSTRAINT ck_idea_ai_lineage_provider_retention_receipt
    CHECK (
        (provider_retention_confirmation_id IS NULL
         AND provider_retention_confirmation_ref IS NULL
         AND provider_retention_replay_nonce IS NULL)
        OR
        (lotus_ai_run_id IS NOT NULL
         AND provider_retention_confirmation_id ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND provider_retention_confirmation_ref ~ '^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$'
         AND provider_retention_replay_nonce ~ '^[0-9a-f]{64}$')
    );

CREATE UNIQUE INDEX uq_idea_ai_lineage_provider_retention_confirmation
    ON idea_ai_explanation_lineage (provider_retention_confirmation_id)
    WHERE provider_retention_confirmation_id IS NOT NULL;
CREATE UNIQUE INDEX uq_idea_ai_lineage_provider_retention_reference
    ON idea_ai_explanation_lineage (provider_retention_confirmation_ref)
    WHERE provider_retention_confirmation_ref IS NOT NULL;
CREATE UNIQUE INDEX uq_idea_ai_lineage_provider_retention_nonce
    ON idea_ai_explanation_lineage (provider_retention_replay_nonce)
    WHERE provider_retention_replay_nonce IS NOT NULL;
