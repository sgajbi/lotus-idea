ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    ADD CONSTRAINT ck_idea_candidate_presentation_receipt_values_v2 CHECK (
        receipt_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND rank_at_presentation > 0
        AND visible_candidate_count BETWEEN 1 AND 100
        AND queue_snapshot_digest ~ '^sha256:[0-9a-f]{64}$'
        AND queue_policy_version ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND ranking_policy_version ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND candidate_material_version > 0
        AND candidate_evidence_version > 0
        AND schema_version = 'lotus-idea.candidate-presentation-receipt.v1'
        AND surface = 'advisor_review_queue'
        AND producer = 'lotus-workbench'
    ) NOT VALID;

DO $$
BEGIN
    IF to_regclass('public.idea_candidate_presentation_receipt') IS NOT NULL THEN
        UPDATE idea_candidate_presentation_receipt
        SET schema_version = 'lotus-idea.candidate-presentation-receipt.v1'
        WHERE schema_version = 'lotus-idea.candidate-presentation-receipt.v2';
    END IF;
END
$$;

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    VALIDATE CONSTRAINT ck_idea_candidate_presentation_receipt_values_v2;

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    DROP CONSTRAINT ck_idea_candidate_presentation_receipt_values_v3,
    DROP COLUMN source_revision_vector_digest,
    DROP COLUMN source_cut_posture;
