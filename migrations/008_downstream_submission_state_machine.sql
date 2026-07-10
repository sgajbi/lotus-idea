-- Durable claim/finalize/reconcile state for outbound Idea submissions.

ALTER TABLE idea_downstream_submission
    ADD COLUMN IF NOT EXISTS support_reference TEXT,
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER,
    ADD COLUMN IF NOT EXISTS updated_at_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS lease_owner TEXT,
    ADD COLUMN IF NOT EXISTS lease_attempt_id TEXT,
    ADD COLUMN IF NOT EXISTS lease_expires_at_utc TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS audit_json JSONB;

UPDATE idea_downstream_submission
SET support_reference = COALESCE(
        support_reference,
        'downstream-submission-' || substr(
            encode(sha256(idempotency_key::bytea), 'hex'),
            1,
            24
        )
    ),
    attempt_count = COALESCE(attempt_count, 1),
    updated_at_utc = COALESCE(updated_at_utc, submitted_at_utc),
    audit_json = COALESCE(
        audit_json,
        jsonb_build_array(
            jsonb_build_object(
                'auditId', 'downstream-audit-legacy-' || substr(
                    encode(sha256(idempotency_key::bytea), 'hex'),
                    1,
                    16
                ),
                'action', 'finalized',
                'actorSubject', 'legacy-migration',
                'previousPosture', NULL,
                'currentPosture', status,
                'occurredAtUtc', submitted_at_utc,
                'reason', downstream_failure_reason,
                'changeReference', NULL
            )
        )
    );

ALTER TABLE idea_downstream_submission
    ALTER COLUMN support_reference SET NOT NULL,
    ALTER COLUMN attempt_count SET NOT NULL,
    ALTER COLUMN updated_at_utc SET NOT NULL,
    ALTER COLUMN audit_json SET NOT NULL,
    ADD CONSTRAINT uq_idea_downstream_submission_support_reference UNIQUE (support_reference),
    ADD CONSTRAINT uq_idea_downstream_submission_lease_attempt UNIQUE (lease_attempt_id),
    ADD CONSTRAINT ck_idea_downstream_submission_support_reference CHECK (
        support_reference ~ '^downstream-submission-[a-f0-9]{24}$'
    ),
    ADD CONSTRAINT ck_idea_downstream_submission_attempt_count CHECK (attempt_count > 0),
    ADD CONSTRAINT ck_idea_downstream_submission_updated_time CHECK (
        updated_at_utc >= submitted_at_utc
    ),
    ADD CONSTRAINT ck_idea_downstream_submission_audit CHECK (
        jsonb_typeof(audit_json) = 'array' AND jsonb_array_length(audit_json) > 0
    ),
    ADD CONSTRAINT ck_idea_downstream_submission_status CHECK (
        status IN (
            'in_flight',
            'accepted_by_downstream',
            'rejected_by_downstream',
            'not_configured',
            'reconciliation_required',
            'quarantined'
        )
    ),
    ADD CONSTRAINT ck_idea_downstream_submission_failure_posture CHECK (
        (
            status IN ('in_flight', 'accepted_by_downstream')
            AND downstream_failure_reason IS NULL
        ) OR (
            status IN (
                'rejected_by_downstream',
                'not_configured',
                'reconciliation_required',
                'quarantined'
            )
            AND downstream_failure_reason IS NOT NULL
        )
    ),
    ADD CONSTRAINT ck_idea_downstream_submission_lease CHECK (
        (
            status = 'in_flight'
            AND lease_owner IS NOT NULL
            AND lease_attempt_id IS NOT NULL
            AND lease_expires_at_utc IS NOT NULL
            AND lease_expires_at_utc > submitted_at_utc
        ) OR status <> 'in_flight'
    );

CREATE INDEX IF NOT EXISTS idx_idea_downstream_submission_reconciliation
    ON idea_downstream_submission (status, updated_at_utc, support_reference)
    WHERE status IN ('in_flight', 'reconciliation_required');
