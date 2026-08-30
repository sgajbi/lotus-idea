-- Immutable, bounded proof of candidates actually rendered in the governed advisor review queue.
-- The receipt deliberately excludes client content, candidate rationale and actor identity.

CREATE TABLE idea_candidate_presentation_receipt (
    receipt_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    tenant_id TEXT NOT NULL,
    presented_at_utc TIMESTAMPTZ NOT NULL,
    rank_at_presentation INTEGER NOT NULL,
    visible_candidate_count INTEGER NOT NULL,
    queue_snapshot_digest TEXT NOT NULL,
    queue_policy_version TEXT NOT NULL,
    ranking_policy_version TEXT NOT NULL,
    candidate_material_version INTEGER NOT NULL,
    candidate_evidence_version INTEGER NOT NULL,
    schema_version TEXT NOT NULL,
    surface TEXT NOT NULL,
    producer TEXT NOT NULL,
    recorded_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_idea_candidate_presentation_receipt_values CHECK (
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
    )
);

CREATE INDEX idx_idea_candidate_presentation_receipt_tenant_time
    ON idea_candidate_presentation_receipt (tenant_id, presented_at_utc, receipt_id);

CREATE INDEX idx_idea_candidate_presentation_receipt_candidate_time
    ON idea_candidate_presentation_receipt (candidate_id, presented_at_utc, receipt_id);
