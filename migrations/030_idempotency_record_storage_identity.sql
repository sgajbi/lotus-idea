-- Give the append-only mutation ledger a storage identity for restore and
-- PostgreSQL replica-identity safety. Tenant/system business uniqueness remains
-- owned by the partial indexes introduced in migration 028.

ALTER TABLE idea_idempotency_record
    ADD COLUMN idempotency_record_identity TEXT GENERATED ALWAYS AS (
        CASE
            WHEN tenant_id IS NULL THEN
                'system:' || length(idempotency_key)::TEXT || ':' || idempotency_key
            ELSE
                'tenant:' || length(tenant_id)::TEXT || ':' || tenant_id || ':'
                || length(idempotency_key)::TEXT || ':' || idempotency_key
        END
    ) STORED;

ALTER TABLE idea_idempotency_record
    ADD CONSTRAINT idea_idempotency_record_pkey
    PRIMARY KEY (idempotency_record_identity);
