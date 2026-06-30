ALTER TABLE idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_event_type;

ALTER TABLE idea_outbox_event
    ADD CONSTRAINT ck_idea_outbox_event_event_type
    CHECK (
        event_type IN (
            'idea.candidate.persisted.v1',
            'idea.lifecycle.transitioned.v1',
            'idea.review.decision_recorded.v1',
            'idea.feedback.recorded.v1',
            'idea.conversion.intent_requested.v1',
            'idea.conversion.outcome_recorded.v1',
            'idea.report_evidence_pack.requested.v1'
        )
    );

ALTER TABLE idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_aggregate_type;

ALTER TABLE idea_outbox_event
    ADD CONSTRAINT ck_idea_outbox_event_aggregate_type
    CHECK (aggregate_type = 'idea_candidate');

ALTER TABLE idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_schema_version;

ALTER TABLE idea_outbox_event
    ADD CONSTRAINT ck_idea_outbox_event_schema_version
    CHECK (schema_version = 'v1');
