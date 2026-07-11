-- Add versioned output-content integrity to AI explanation lineage.
-- Pre-v1 rows cannot be reconstructed because content was intentionally not retained.

ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN output_integrity_version TEXT,
    ADD COLUMN output_content_digest TEXT;

UPDATE idea_ai_explanation_lineage
SET output_integrity_version = 'lotus-idea.ai-output-integrity.pre-v1-unverifiable',
    output_content_digest = lineage_hash,
    lineage_json = lineage_json || jsonb_build_object(
        'output_integrity_version', 'lotus-idea.ai-output-integrity.pre-v1-unverifiable',
        'output_content_digest', lineage_hash
    )
WHERE output_integrity_version IS NULL;

ALTER TABLE idea_ai_explanation_lineage
    ALTER COLUMN output_integrity_version SET NOT NULL,
    ALTER COLUMN output_content_digest SET NOT NULL;

ALTER TABLE idea_ai_explanation_lineage
    ADD CONSTRAINT ck_ai_explanation_output_content_digest
    CHECK (output_content_digest ~ '^sha256:[0-9a-f]{64}$');
