from __future__ import annotations


REQUIRED_TABLES = (
    "idea_candidate_record",
    "idea_idempotency_record",
    "idea_lifecycle_history",
    "idea_audit_event",
    "idea_outbox_event",
    "idea_review_decision",
    "idea_feedback_event",
    "idea_conversion_intent",
    "idea_conversion_outcome",
    "idea_report_evidence_pack_request",
    "idea_downstream_submission",
)

REQUIRED_INDEXES = (
    "idx_idea_candidate_record_family_status",
    "idx_idea_candidate_record_review_queue_order",
    "idx_idea_candidate_record_scope_tenant",
    "idx_idea_candidate_record_scope_book",
    "idx_idea_candidate_record_scope_portfolio",
    "idx_idea_candidate_record_scope_client",
    "idx_idea_candidate_record_evidence_hash",
    "idx_idea_candidate_record_persisted_at",
    "idx_idea_idempotency_record_candidate",
    "idx_idea_lifecycle_history_candidate_time",
    "idx_idea_audit_event_candidate_time",
    "idx_idea_outbox_event_status_time",
    "idx_idea_outbox_event_retry_due",
    "idx_idea_outbox_event_lease_expiry",
    "idx_idea_outbox_event_aggregate_time",
    "idx_idea_review_decision_candidate_time",
    "idx_idea_feedback_event_candidate_time",
    "idx_idea_conversion_intent_candidate_target",
    "idx_idea_conversion_outcome_intent_time",
    "idx_idea_report_evidence_pack_candidate_time",
    "idx_idea_downstream_submission_resource",
)

REQUIRED_FORWARD_FRAGMENTS = (
    "JSONB NOT NULL",
    "TIMESTAMPTZ NOT NULL",
    "PRIMARY KEY",
    "REFERENCES idea_candidate_record(candidate_id)",
    "REFERENCES idea_conversion_intent(conversion_intent_id)",
    "ck_idea_outbox_event_event_type",
    "ck_idea_outbox_event_aggregate_type",
    "ck_idea_outbox_event_schema_version",
    "request_fingerprint TEXT NOT NULL",
    "resource_type TEXT NOT NULL",
    "resource_id TEXT NOT NULL",
    "source_authority TEXT NOT NULL",
    "submitted_at_utc TIMESTAMPTZ NOT NULL",
)

AI_LINEAGE_REQUIRED_TABLES = ("idea_ai_explanation_lineage",)

AI_LINEAGE_REQUIRED_INDEXES = (
    "idx_idea_ai_explanation_lineage_candidate_time",
    "idx_idea_ai_explanation_lineage_workflow_time",
    "idx_idea_ai_explanation_lineage_posture_time",
)

AI_LINEAGE_REQUIRED_FORWARD_FRAGMENTS = (
    "JSONB NOT NULL",
    "TIMESTAMPTZ NOT NULL",
    "PRIMARY KEY",
    "BOOLEAN NOT NULL",
    "REFERENCES idea_candidate_record(candidate_id)",
)

PROHIBITED_SQL_FRAGMENTS = (
    "TODO",
    "TBD",
    "PLACEHOLDER",
    "DROP TABLE IF EXISTS idea_candidate_record;",
)
