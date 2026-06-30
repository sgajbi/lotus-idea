-- lotus-idea RFC-0002 Slice 06 durable repository schema contract.
-- This migration defines the first governed persistence shape before runtime
-- database wiring is enabled.

CREATE TABLE IF NOT EXISTS idea_candidate_record (
    candidate_id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    lifecycle_status TEXT NOT NULL,
    review_posture TEXT NOT NULL,
    evidence_packet_id TEXT NOT NULL,
    evidence_hash TEXT NOT NULL,
    candidate_json JSONB NOT NULL,
    persisted_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_idempotency_record (
    idempotency_key TEXT PRIMARY KEY,
    operation_name TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    candidate_id TEXT REFERENCES idea_candidate_record(candidate_id),
    created_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_lifecycle_history (
    lifecycle_history_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    source_status TEXT NOT NULL,
    target_status TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    changed_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_audit_event (
    audit_event_id TEXT PRIMARY KEY,
    candidate_id TEXT REFERENCES idea_candidate_record(candidate_id),
    event_type TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    outcome TEXT NOT NULL,
    attributes_json JSONB NOT NULL,
    occurred_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_outbox_event (
    outbox_event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL,
    occurred_at_utc TIMESTAMPTZ NOT NULL,
    idempotency_fingerprint TEXT,
    correlation_id TEXT,
    causation_id TEXT,
    published_at_utc TIMESTAMPTZ,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    lease_owner TEXT,
    lease_attempt_id TEXT,
    lease_expires_at_utc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS idea_review_decision (
    review_decision_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    action TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    decision_json JSONB NOT NULL,
    decided_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_feedback_event (
    feedback_event_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    actor_subject TEXT NOT NULL,
    feedback_json JSONB NOT NULL,
    recorded_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_conversion_intent (
    conversion_intent_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    target TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    intent_json JSONB NOT NULL,
    requested_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_conversion_outcome (
    conversion_outcome_id TEXT PRIMARY KEY,
    conversion_intent_id TEXT NOT NULL REFERENCES idea_conversion_intent(conversion_intent_id),
    source_system TEXT NOT NULL,
    status TEXT NOT NULL,
    outcome_json JSONB NOT NULL,
    recorded_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_report_evidence_pack_request (
    report_evidence_pack_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    conversion_intent_id TEXT NOT NULL REFERENCES idea_conversion_intent(conversion_intent_id),
    purpose TEXT NOT NULL,
    evidence_hash TEXT NOT NULL,
    evidence_pack_json JSONB NOT NULL,
    requested_at_utc TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_downstream_submission (
    idempotency_key TEXT PRIMARY KEY,
    request_fingerprint TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    target TEXT NOT NULL,
    source_authority TEXT NOT NULL,
    status TEXT NOT NULL,
    downstream_failure_reason TEXT,
    correlation_id TEXT,
    trace_id TEXT,
    submitted_at_utc TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idea_candidate_record_family_status
    ON idea_candidate_record (family, lifecycle_status, review_posture);

CREATE INDEX IF NOT EXISTS idx_idea_candidate_record_evidence_hash
    ON idea_candidate_record (evidence_hash);

CREATE INDEX IF NOT EXISTS idx_idea_candidate_record_persisted_at
    ON idea_candidate_record (persisted_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_idempotency_record_candidate
    ON idea_idempotency_record (candidate_id, operation_name);

CREATE INDEX IF NOT EXISTS idx_idea_lifecycle_history_candidate_time
    ON idea_lifecycle_history (candidate_id, changed_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_audit_event_candidate_time
    ON idea_audit_event (candidate_id, occurred_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_outbox_event_status_time
    ON idea_outbox_event (status, occurred_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_outbox_event_lease_expiry
    ON idea_outbox_event (status, lease_expires_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_outbox_event_aggregate_time
    ON idea_outbox_event (aggregate_type, aggregate_id, occurred_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_review_decision_candidate_time
    ON idea_review_decision (candidate_id, decided_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_feedback_event_candidate_time
    ON idea_feedback_event (candidate_id, recorded_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_conversion_intent_candidate_target
    ON idea_conversion_intent (candidate_id, target, requested_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_conversion_outcome_intent_time
    ON idea_conversion_outcome (conversion_intent_id, recorded_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_report_evidence_pack_candidate_time
    ON idea_report_evidence_pack_request (candidate_id, requested_at_utc);

CREATE INDEX IF NOT EXISTS idx_idea_downstream_submission_resource
    ON idea_downstream_submission (resource_type, resource_id, target);
