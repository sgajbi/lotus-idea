-- Rolling back after two tenants have used the same raw key would collapse
-- distinct durable identities. Refuse that downgrade rather than deleting or
-- coalescing evidence.
DO $$
DECLARE
    duplicate_raw_keys BOOLEAN := FALSE;
BEGIN
    IF to_regclass('idea_idempotency_record') IS NOT NULL THEN
        EXECUTE
            'SELECT EXISTS (
                SELECT idempotency_key
                FROM idea_idempotency_record
                GROUP BY idempotency_key
                HAVING COUNT(*) > 1
            )'
        INTO duplicate_raw_keys;
    END IF;
    IF duplicate_raw_keys THEN
        RAISE EXCEPTION
            'cannot roll back tenant-scoped idempotency while duplicate raw keys exist';
    END IF;
END
$$;

DROP INDEX IF EXISTS idx_idea_idempotency_record_tenant_candidate;
DROP INDEX IF EXISTS uq_idea_idempotency_record_system_key;
DROP INDEX IF EXISTS uq_idea_idempotency_record_tenant_key;

ALTER TABLE IF EXISTS idea_idempotency_record
    DROP CONSTRAINT IF EXISTS ck_idea_idempotency_record_tenant_scope;

ALTER TABLE IF EXISTS idea_idempotency_record
    DROP COLUMN IF EXISTS tenant_id;

DO $$
DECLARE
    table_oid OID := to_regclass('idea_idempotency_record');
    has_primary_key BOOLEAN := FALSE;
BEGIN
    IF table_oid IS NOT NULL THEN
        SELECT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = table_oid AND contype = 'p'
        ) INTO has_primary_key;
    END IF;
    IF table_oid IS NOT NULL AND NOT has_primary_key THEN
        ALTER TABLE IF EXISTS idea_idempotency_record ADD PRIMARY KEY (idempotency_key);
    END IF;
END
$$;
