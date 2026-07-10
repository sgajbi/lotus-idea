-- Governed, append-only operator recovery evidence for dead-lettered Idea outbox events.

CREATE TABLE IF NOT EXISTS idea_outbox_recovery_audit (
    recovery_id TEXT PRIMARY KEY,
    outbox_event_id TEXT NOT NULL REFERENCES idea_outbox_event(outbox_event_id),
    support_reference TEXT NOT NULL,
    idempotency_fingerprint TEXT NOT NULL UNIQUE,
    request_fingerprint TEXT NOT NULL,
    actor_subject TEXT NOT NULL,
    recovery_reason TEXT NOT NULL,
    change_reference TEXT NOT NULL,
    requested_at_utc TIMESTAMPTZ NOT NULL,
    lease_owner TEXT NOT NULL,
    lease_attempt_id TEXT NOT NULL UNIQUE,
    lease_expires_at_utc TIMESTAMPTZ NOT NULL,
    original_retry_count INTEGER NOT NULL CHECK (original_retry_count >= 0),
    original_failure_reason TEXT NOT NULL,
    original_first_failed_at_utc TIMESTAMPTZ NOT NULL,
    original_last_failed_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_idea_outbox_recovery_event UNIQUE (outbox_event_id),
    CONSTRAINT ck_idea_outbox_recovery_lease_window CHECK (
        lease_expires_at_utc > requested_at_utc
    )
);

CREATE INDEX IF NOT EXISTS idx_idea_outbox_recovery_support_reference
    ON idea_outbox_recovery_audit (support_reference);

CREATE INDEX IF NOT EXISTS idx_idea_outbox_recovery_requested_at
    ON idea_outbox_recovery_audit (requested_at_utc);
