-- lotus-idea RFC-0002 Slice 09 source-safe AI explanation lineage schema.
-- Stores verifier/fallback lineage only; prompts, provider payloads, source
-- routes, portfolio IDs, and client IDs are intentionally outside this table.

CREATE TABLE IF NOT EXISTS idea_ai_explanation_lineage (
    ai_explanation_request_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    evidence_packet_id TEXT NOT NULL,
    evidence_content_hash TEXT NOT NULL,
    workflow_pack_id TEXT NOT NULL,
    workflow_pack_version TEXT NOT NULL,
    purpose TEXT NOT NULL,
    posture TEXT NOT NULL,
    verifier_outcome TEXT NOT NULL,
    fallback_used BOOLEAN NOT NULL,
    fallback_reason TEXT,
    lineage_hash TEXT NOT NULL,
    lineage_json JSONB NOT NULL,
    requested_at_utc TIMESTAMPTZ NOT NULL,
    evaluated_at_utc TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idea_ai_explanation_lineage_candidate_time
    ON idea_ai_explanation_lineage (candidate_id, evaluated_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_ai_explanation_lineage_workflow_time
    ON idea_ai_explanation_lineage (workflow_pack_id, workflow_pack_version, evaluated_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_ai_explanation_lineage_posture_time
    ON idea_ai_explanation_lineage (posture, evaluated_at_utc);
