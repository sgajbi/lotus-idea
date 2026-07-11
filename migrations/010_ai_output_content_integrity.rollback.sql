ALTER TABLE idea_ai_explanation_lineage
    DROP CONSTRAINT IF EXISTS ck_ai_explanation_output_content_digest,
    DROP COLUMN IF EXISTS output_content_digest,
    DROP COLUMN IF EXISTS output_integrity_version;
