-- Persist the exact Manage-owned action realization history for one accepted
-- Idea submission (lotus-idea#675, owner contract manage#660). The owner's
-- review status is not absorbing (REQUEST_CHANGES reopens APPROVED/REJECTED),
-- so the compare-and-set guards the append-only event version, never a
-- terminal-status flag.

CREATE TABLE IF NOT EXISTS idea_manage_realization_history (
    support_reference TEXT PRIMARY KEY
        REFERENCES idea_downstream_submission (support_reference) ON DELETE CASCADE,
    management_action_id TEXT NOT NULL UNIQUE,
    intake_id TEXT NOT NULL UNIQUE,
    current_source_event_version INTEGER NOT NULL,
    history_json JSONB NOT NULL,
    persisted_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_idea_manage_realization_version CHECK (current_source_event_version > 0),
    CONSTRAINT ck_idea_manage_realization_history_json CHECK (
        jsonb_typeof(history_json) = 'object'
        AND jsonb_typeof(history_json->'events') = 'array'
        AND jsonb_array_length(history_json->'events') > 0
    )
);
