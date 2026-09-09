-- A caller idempotency key governs transport replay, but it must not create a
-- second submission aggregate for the same authoritative downstream resource.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM idea_downstream_submission
        GROUP BY tenant_id, resource_type, resource_id, target
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION
            'cannot enforce downstream submission resource identity while duplicate resources exist';
    END IF;
END
$$;

DROP INDEX IF EXISTS idx_idea_downstream_submission_resource;

CREATE UNIQUE INDEX uq_idea_downstream_submission_resource_identity
    ON idea_downstream_submission (tenant_id, resource_type, resource_id, target);
