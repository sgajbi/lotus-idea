-- Refuse downgrade after tenant-scoped claims exist: collapsing them would lose identity truth.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'idea_downstream_submission'
          AND column_name = 'identity_version'
    ) THEN
        IF EXISTS (
            SELECT 1
            FROM idea_downstream_submission
            WHERE identity_version <> 'legacy_unscoped_v1'
        ) THEN
            RAISE EXCEPTION
                'unsafe downgrade: tenant-scoped downstream submission identities exist';
        END IF;
        EXECUTE 'ALTER TABLE IF EXISTS idea_downstream_submission
            DROP CONSTRAINT ck_idea_downstream_submission_identity_version,
            DROP CONSTRAINT ck_idea_downstream_submission_tenant,
            DROP CONSTRAINT pk_idea_downstream_submission,
            ADD CONSTRAINT idea_downstream_submission_pkey PRIMARY KEY (idempotency_key),
            DROP COLUMN identity_version,
            DROP COLUMN tenant_id';
    END IF;
END
$$;
