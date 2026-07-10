ALTER TABLE idea_outbox_event
    ADD COLUMN IF NOT EXISTS trace_id TEXT,
    ADD COLUMN IF NOT EXISTS lineage_origin TEXT;

UPDATE idea_outbox_event
SET correlation_id = CASE
        WHEN correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9.:-]{0,95}$'
         AND correlation_id !~* '(access_token|api-key|apikey|authorization|bearer|client_secret|password|secret|token|PB_)'
            THEN correlation_id
        ELSE 'corr-system-' || SUBSTRING(MD5(outbox_event_id) FROM 1 FOR 24)
    END,
    trace_id = 'trace-system-' || SUBSTRING(MD5(outbox_event_id) FROM 1 FOR 24),
    causation_id = CASE
        WHEN causation_id ~ '^[A-Za-z0-9][A-Za-z0-9.:-]{0,95}$'
         AND causation_id !~* '(access_token|api-key|apikey|authorization|bearer|client_secret|password|secret|token|PB_)'
            THEN causation_id
        ELSE NULL
    END,
    lineage_origin = 'legacy_migrated';

ALTER TABLE idea_outbox_event
    ALTER COLUMN correlation_id SET NOT NULL,
    ALTER COLUMN trace_id SET NOT NULL,
    ALTER COLUMN lineage_origin SET NOT NULL,
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_lineage_origin,
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_lineage_identifiers,
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_causation_origin,
    ADD CONSTRAINT ck_idea_outbox_event_lineage_origin CHECK (
        lineage_origin IN ('request', 'parent_event', 'system_generated', 'legacy_migrated')
    ),
    ADD CONSTRAINT ck_idea_outbox_event_lineage_identifiers CHECK (
        correlation_id ~ '^[A-Za-z0-9][A-Za-z0-9.:-]{0,95}$'
        AND correlation_id !~* '(access_token|api-key|apikey|authorization|bearer|client_secret|password|secret|token|PB_)'
        AND trace_id ~ '^[A-Za-z0-9][A-Za-z0-9.:-]{0,95}$'
        AND trace_id !~* '(access_token|api-key|apikey|authorization|bearer|client_secret|password|secret|token|PB_)'
        AND (
            causation_id IS NULL
            OR (
                causation_id ~ '^[A-Za-z0-9][A-Za-z0-9.:-]{0,95}$'
                AND causation_id !~* '(access_token|api-key|apikey|authorization|bearer|client_secret|password|secret|token|PB_)'
            )
        )
    ),
    ADD CONSTRAINT ck_idea_outbox_event_causation_origin CHECK (
        (lineage_origin = 'parent_event' AND causation_id IS NOT NULL)
        OR (lineage_origin IN ('request', 'system_generated') AND causation_id IS NULL)
        OR lineage_origin = 'legacy_migrated'
    );
