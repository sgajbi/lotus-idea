ALTER TABLE idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_schema_version;

ALTER TABLE idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_aggregate_type;

ALTER TABLE idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_event_type;
