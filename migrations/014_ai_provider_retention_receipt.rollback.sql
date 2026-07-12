DROP INDEX IF EXISTS uq_idea_ai_lineage_provider_retention_nonce;
DROP INDEX IF EXISTS uq_idea_ai_lineage_provider_retention_reference;
DROP INDEX IF EXISTS uq_idea_ai_lineage_provider_retention_confirmation;

ALTER TABLE IF EXISTS idea_ai_explanation_lineage
    DROP CONSTRAINT IF EXISTS ck_idea_ai_lineage_provider_retention_receipt;
ALTER TABLE IF EXISTS idea_ai_explanation_lineage
    DROP COLUMN IF EXISTS provider_retention_replay_nonce;
ALTER TABLE IF EXISTS idea_ai_explanation_lineage
    DROP COLUMN IF EXISTS provider_retention_confirmation_ref;
ALTER TABLE IF EXISTS idea_ai_explanation_lineage
    DROP COLUMN IF EXISTS provider_retention_confirmation_id;
