ALTER TABLE IF EXISTS idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_causation_origin,
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_lineage_identifiers,
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_lineage_origin,
    ALTER COLUMN correlation_id DROP NOT NULL,
    DROP COLUMN IF EXISTS lineage_origin,
    DROP COLUMN IF EXISTS trace_id;
