-- Persist bounded verified lotus-ai attestation identity for replay protection.
-- Raw prompts, provider payloads, generated content, and unrestricted evidence remain excluded.

ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN lotus_ai_run_id TEXT;
ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN lotus_ai_replay_nonce TEXT;
ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN lotus_ai_attestation_key_id TEXT;

CREATE UNIQUE INDEX uq_idea_ai_explanation_lineage_lotus_ai_run_id
    ON idea_ai_explanation_lineage (lotus_ai_run_id)
    WHERE lotus_ai_run_id IS NOT NULL;

CREATE UNIQUE INDEX uq_idea_ai_explanation_lineage_lotus_ai_replay_nonce
    ON idea_ai_explanation_lineage (lotus_ai_replay_nonce)
    WHERE lotus_ai_replay_nonce IS NOT NULL;
