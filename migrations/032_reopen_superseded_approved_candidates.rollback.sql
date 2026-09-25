-- A repaired candidate must never regain authority from a superseded approval.
-- Rollback is therefore allowed only when migration 032 repaired no durable rows.

DO $$
BEGIN
    IF to_regclass('public.idea_audit_event') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1
            FROM idea_audit_event
            WHERE event_type = 'idea.migration.superseded_approval_reopened.v1'
              AND attributes_json ->> 'migration_version' = '032'
        ) THEN
            RAISE EXCEPTION
                'unsafe downgrade: migration 032 reopened candidates whose approval authority is superseded';
        END IF;
    END IF;
END
$$;
