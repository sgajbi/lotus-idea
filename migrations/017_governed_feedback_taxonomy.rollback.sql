-- Roll back only when no v2 feedback was accepted; otherwise preserve governed evidence.

ALTER TABLE IF EXISTS idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_event_type;
ALTER TABLE IF EXISTS idea_feedback_event
    DROP CONSTRAINT IF EXISTS ck_idea_feedback_event_taxonomy_json,
    DROP CONSTRAINT IF EXISTS ck_idea_feedback_event_taxonomy_values;

DO $$
BEGIN
    IF to_regclass('idea_feedback_event') IS NULL
        OR to_regclass('idea_outbox_event') IS NULL THEN
        RETURN;
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'idea_feedback_event'
          AND column_name = 'migration_source_outcome'
    ) THEN
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM idea_feedback_event
        WHERE migration_source_outcome IS NULL
    ) OR EXISTS (
        SELECT 1
        FROM idea_outbox_event
        WHERE event_type = 'idea.feedback.recorded.v2'
          AND feedback_taxonomy_migration_source_event_type IS NULL
    ) THEN
        RAISE EXCEPTION
            'cannot roll back governed feedback taxonomy while governed records exist';
    END IF;

    UPDATE idea_outbox_event
    SET event_type = feedback_taxonomy_migration_source_event_type,
        payload_json = feedback_taxonomy_migration_source_payload
    WHERE feedback_taxonomy_migration_source_event_type IS NOT NULL;

    UPDATE idea_feedback_event
    SET feedback_json = (
            jsonb_set(
                feedback_json,
                '{feedback,outcome}',
                to_jsonb(migration_source_outcome),
                TRUE
            )
            #- '{feedback,taxonomy_version}'
            #- '{feedback,reason}'
            #- '{evaluation_context}'
        );
END
$$;

ALTER TABLE IF EXISTS idea_outbox_event
    ADD CONSTRAINT ck_idea_outbox_event_event_type CHECK (
        event_type IN (
            'idea.candidate.persisted.v1',
            'idea.candidate.evidence_refreshed.v1',
            'idea.candidate.material_version_created.v1',
            'idea.candidate.recurrent_condition_reopened.v1',
            'idea.lifecycle.transitioned.v1',
            'idea.review.decision_recorded.v1',
            'idea.feedback.recorded.v1',
            'idea.conversion.intent_requested.v1',
            'idea.conversion.outcome_recorded.v1',
            'idea.report_evidence_pack.requested.v1'
        )
    );

DROP INDEX IF EXISTS idx_idea_feedback_event_offline_evaluation;

ALTER TABLE IF EXISTS idea_outbox_event
    DROP COLUMN IF EXISTS feedback_taxonomy_migration_source_payload,
    DROP COLUMN IF EXISTS feedback_taxonomy_migration_source_event_type;

ALTER TABLE IF EXISTS idea_feedback_event
    DROP COLUMN IF EXISTS migration_source_outcome,
    DROP COLUMN IF EXISTS feedback_reason,
    DROP COLUMN IF EXISTS feedback_outcome,
    DROP COLUMN IF EXISTS feedback_taxonomy_version;
