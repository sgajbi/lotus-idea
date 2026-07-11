-- Lotus Idea RFC-0002 Slice 06 governed retention, hold, erasure, and purge state.

CREATE TABLE IF NOT EXISTS idea_data_lifecycle_control (
    candidate_id TEXT PRIMARY KEY REFERENCES idea_candidate_record(candidate_id),
    tenant_id TEXT NOT NULL,
    policy_ref TEXT NOT NULL,
    state TEXT NOT NULL,
    retention_expires_at_utc TIMESTAMPTZ NOT NULL,
    version INTEGER NOT NULL,
    held_from_state TEXT,
    hold_authority_ref TEXT,
    hold_change_reference TEXT,
    held_at_utc TIMESTAMPTZ,
    erased_at_utc TIMESTAMPTZ,
    purged_at_utc TIMESTAMPTZ,
    tombstone_sha256 TEXT,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_idea_data_lifecycle_control_state
        CHECK (state IN ('active', 'held', 'erased', 'purged')),
    CONSTRAINT ck_idea_data_lifecycle_control_policy
        CHECK (policy_ref IN (
            'lotus-idea:regulated-advisory-evidence:seven-year:v1',
            'lotus-idea:operational-delivery:four-hundred-day:v1',
            'lotus-idea:quarantine:ninety-day:v1'
        )),
    CONSTRAINT ck_idea_data_lifecycle_control_version CHECK (version > 0),
    CONSTRAINT ck_idea_data_lifecycle_control_hold CHECK (
        (
            state = 'held'
            AND held_from_state IN ('active', 'erased', 'purged')
            AND hold_authority_ref IS NOT NULL
            AND hold_change_reference IS NOT NULL
            AND held_at_utc IS NOT NULL
        ) OR (
            state <> 'held'
            AND held_from_state IS NULL
            AND hold_authority_ref IS NULL
            AND hold_change_reference IS NULL
            AND held_at_utc IS NULL
        )
    ),
    CONSTRAINT ck_idea_data_lifecycle_control_erasure CHECK (
        (
            COALESCE(held_from_state, state) IN ('erased', 'purged')
            AND erased_at_utc IS NOT NULL
        ) OR (
            COALESCE(held_from_state, state) NOT IN ('erased', 'purged')
            AND erased_at_utc IS NULL
            AND purged_at_utc IS NULL
        )
    ),
    CONSTRAINT ck_idea_data_lifecycle_control_purge CHECK (
        (COALESCE(held_from_state, state) = 'purged' AND purged_at_utc IS NOT NULL)
        OR (COALESCE(held_from_state, state) <> 'purged' AND purged_at_utc IS NULL)
    ),
    CONSTRAINT ck_idea_data_lifecycle_control_tombstone CHECK (
        tombstone_sha256 IS NULL OR tombstone_sha256 ~ '^[a-f0-9]{64}$'
    )
);

CREATE TABLE IF NOT EXISTS idea_data_lifecycle_operation (
    operation_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    request_fingerprint TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    tenant_id TEXT NOT NULL,
    action TEXT NOT NULL,
    decision TEXT NOT NULL,
    dry_run BOOLEAN NOT NULL,
    actor_subject TEXT NOT NULL,
    approver_subject TEXT,
    authority_ref TEXT NOT NULL,
    reason TEXT NOT NULL,
    change_reference TEXT NOT NULL,
    blockers_json JSONB NOT NULL,
    affected_row_counts_json JSONB NOT NULL,
    audit_sha256 TEXT NOT NULL,
    requested_at_utc TIMESTAMPTZ NOT NULL,
    evaluated_at_utc TIMESTAMPTZ NOT NULL,
    control_version INTEGER,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_idea_data_lifecycle_operation_action
        CHECK (action IN ('apply_hold', 'release_hold', 'erase', 'purge')),
    CONSTRAINT ck_idea_data_lifecycle_operation_decision
        CHECK (decision IN ('preview', 'applied', 'replayed', 'blocked', 'conflict', 'not_found')),
    CONSTRAINT ck_idea_data_lifecycle_operation_time
        CHECK (evaluated_at_utc >= requested_at_utc),
    CONSTRAINT ck_idea_data_lifecycle_operation_control_version
        CHECK (control_version IS NULL OR control_version > 0),
    CONSTRAINT ck_idea_data_lifecycle_operation_audit_hash
        CHECK (audit_sha256 ~ '^[a-f0-9]{64}$'),
    CONSTRAINT ck_idea_data_lifecycle_operation_lineage
        CHECK (
            BTRIM(correlation_id) <> ''
            AND BTRIM(trace_id) <> ''
            AND correlation_id <> trace_id
        )
);

INSERT INTO idea_data_lifecycle_control (
    candidate_id,
    tenant_id,
    policy_ref,
    state,
    retention_expires_at_utc,
    version,
    updated_at_utc
)
SELECT
    candidate_id,
    candidate_json->'access_scope'->>'tenant_id',
    'lotus-idea:regulated-advisory-evidence:seven-year:v1',
    'active',
    persisted_at_utc + INTERVAL '7 years',
    1,
    updated_at_utc
FROM idea_candidate_record
WHERE NULLIF(BTRIM(candidate_json->'access_scope'->>'tenant_id'), '') IS NOT NULL
ON CONFLICT (candidate_id) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_idea_data_lifecycle_control_tenant_candidate
    ON idea_data_lifecycle_control (tenant_id, candidate_id);

CREATE INDEX IF NOT EXISTS idx_idea_data_lifecycle_control_state_expiry
    ON idea_data_lifecycle_control (state, retention_expires_at_utc, candidate_id);

CREATE INDEX IF NOT EXISTS idx_idea_data_lifecycle_operation_candidate_time
    ON idea_data_lifecycle_operation (candidate_id, evaluated_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_idea_data_lifecycle_operation_tenant_time
    ON idea_data_lifecycle_operation (tenant_id, evaluated_at_utc DESC);
