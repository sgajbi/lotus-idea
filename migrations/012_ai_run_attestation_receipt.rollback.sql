DROP INDEX IF EXISTS uq_idea_ai_explanation_lineage_lotus_ai_replay_nonce;
DROP INDEX IF EXISTS uq_idea_ai_explanation_lineage_lotus_ai_run_id;

ALTER TABLE idea_ai_explanation_lineage
    DROP COLUMN IF EXISTS lotus_ai_attestation_key_id;
ALTER TABLE idea_ai_explanation_lineage
    DROP COLUMN IF EXISTS lotus_ai_replay_nonce;
ALTER TABLE idea_ai_explanation_lineage
    DROP COLUMN IF EXISTS lotus_ai_run_id;
