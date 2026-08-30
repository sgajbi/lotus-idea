-- Rollback deliberately fails during validation if receipts now rely on an independent global
-- rank. Operators must reconcile those governed records before reinstating the legacy relation.

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    ADD CONSTRAINT ck_idea_candidate_presentation_receipt_values CHECK (
        receipt_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND tenant_id ~ '^[A-Za-z0-9][A-Za-z0-9._:-]{2,255}$'
        AND rank_at_presentation BETWEEN 1 AND visible_candidate_count
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

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    VALIDATE CONSTRAINT ck_idea_candidate_presentation_receipt_values;

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    DROP CONSTRAINT ck_idea_candidate_presentation_receipt_values_v2;
