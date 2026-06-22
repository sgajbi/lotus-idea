-- Rollback for lotus-idea RFC-0002 Slice 09 source-safe AI explanation lineage.

DROP INDEX IF EXISTS idx_idea_ai_explanation_lineage_posture_time;
DROP INDEX IF EXISTS idx_idea_ai_explanation_lineage_workflow_time;
DROP INDEX IF EXISTS idx_idea_ai_explanation_lineage_candidate_time;

DROP TABLE IF EXISTS idea_ai_explanation_lineage;
