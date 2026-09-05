-- Bind new Workbench presentation receipts to the exact source revision vector shown.
-- Existing v1 receipts remain explicit legacy evidence and cannot authorize current review.

ALTER TABLE idea_candidate_presentation_receipt
    ADD COLUMN source_revision_vector_digest TEXT,
    ADD COLUMN source_cut_posture TEXT NOT NULL DEFAULT 'unknown';

ALTER TABLE idea_candidate_presentation_receipt
    ALTER COLUMN source_cut_posture DROP DEFAULT;

ALTER TABLE idea_candidate_presentation_receipt
    ADD CONSTRAINT ck_idea_candidate_presentation_receipt_values_v3 CHECK (
        receipt_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND rank_at_presentation > 0
        AND visible_candidate_count BETWEEN 1 AND 100
        AND queue_snapshot_digest ~ '^sha256:[0-9a-f]{64}$'
        AND queue_policy_version ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND ranking_policy_version ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND candidate_material_version > 0
        AND candidate_evidence_version > 0
        AND (
            (
                schema_version = 'lotus-idea.candidate-presentation-receipt.v1'
                AND source_revision_vector_digest IS NULL
                AND source_cut_posture = 'unknown'
            )
            OR (
                schema_version = 'lotus-idea.candidate-presentation-receipt.v2'
                AND source_revision_vector_digest ~ '^sha256:[0-9a-f]{64}$'
                AND source_cut_posture IN (
                    'coherent',
                    'coherent_with_declared_tolerance',
                    'mixed',
                    'partial',
                    'unknown'
                )
            )
        )
        AND surface = 'advisor_review_queue'
        AND producer = 'lotus-workbench'
    ) NOT VALID;

ALTER TABLE idea_candidate_presentation_receipt
    VALIDATE CONSTRAINT ck_idea_candidate_presentation_receipt_values_v3;

ALTER TABLE idea_candidate_presentation_receipt
    DROP CONSTRAINT ck_idea_candidate_presentation_receipt_values_v2;
