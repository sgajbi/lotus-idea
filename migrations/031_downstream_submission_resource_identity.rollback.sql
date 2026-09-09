DROP INDEX IF EXISTS uq_idea_downstream_submission_resource_identity;

DO $$
BEGIN
    IF to_regclass('public.idea_downstream_submission') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_idea_downstream_submission_resource
            ON idea_downstream_submission (resource_type, resource_id, target);
    END IF;
END
$$;
