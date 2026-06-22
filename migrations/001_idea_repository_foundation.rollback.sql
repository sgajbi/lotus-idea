-- Rollback for lotus-idea RFC-0002 Slice 06 durable repository schema contract.
-- Drop indexes and tables in dependency-safe reverse order.

DROP INDEX IF EXISTS idx_idea_report_evidence_pack_candidate_time;
DROP INDEX IF EXISTS idx_idea_conversion_outcome_intent_time;
DROP INDEX IF EXISTS idx_idea_conversion_intent_candidate_target;
DROP INDEX IF EXISTS idx_idea_feedback_event_candidate_time;
DROP INDEX IF EXISTS idx_idea_review_decision_candidate_time;
DROP INDEX IF EXISTS idx_idea_outbox_event_aggregate_time;
DROP INDEX IF EXISTS idx_idea_outbox_event_status_time;
DROP INDEX IF EXISTS idx_idea_audit_event_candidate_time;
DROP INDEX IF EXISTS idx_idea_lifecycle_history_candidate_time;
DROP INDEX IF EXISTS idx_idea_idempotency_record_candidate;
DROP INDEX IF EXISTS idx_idea_candidate_record_persisted_at;
DROP INDEX IF EXISTS idx_idea_candidate_record_evidence_hash;
DROP INDEX IF EXISTS idx_idea_candidate_record_family_status;

DROP TABLE IF EXISTS idea_report_evidence_pack_request;
DROP TABLE IF EXISTS idea_conversion_outcome;
DROP TABLE IF EXISTS idea_conversion_intent;
DROP TABLE IF EXISTS idea_feedback_event;
DROP TABLE IF EXISTS idea_review_decision;
DROP TABLE IF EXISTS idea_outbox_event;
DROP TABLE IF EXISTS idea_audit_event;
DROP TABLE IF EXISTS idea_lifecycle_history;
DROP TABLE IF EXISTS idea_idempotency_record;
DROP TABLE IF EXISTS idea_candidate_record;
