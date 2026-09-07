-- Scope candidate-bound mutation idempotency to the authoritative candidate tenant.
-- Deploy with old writers drained: the previous binary targets the former raw-key
-- primary key and is not compatible with the composite uniqueness contract.

ALTER TABLE idea_idempotency_record
    ADD COLUMN tenant_id TEXT;

UPDATE idea_idempotency_record AS idempotency
SET tenant_id = candidate.candidate_json->'access_scope'->>'tenant_id'
FROM idea_candidate_record AS candidate
WHERE idempotency.candidate_id = candidate.candidate_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM idea_idempotency_record
        WHERE candidate_id IS NOT NULL
          AND (tenant_id IS NULL OR btrim(tenant_id) = '')
    ) THEN
        RAISE EXCEPTION
            'candidate-bound idempotency rows require a source candidate tenant';
    END IF;
END
$$;

ALTER TABLE idea_idempotency_record
    DROP CONSTRAINT idea_idempotency_record_pkey;

ALTER TABLE idea_idempotency_record
    ADD CONSTRAINT ck_idea_idempotency_record_tenant_scope
    CHECK (
        (candidate_id IS NOT NULL AND tenant_id IS NOT NULL AND btrim(tenant_id) <> '')
        OR (candidate_id IS NULL AND tenant_id IS NULL)
    );

CREATE UNIQUE INDEX uq_idea_idempotency_record_tenant_key
    ON idea_idempotency_record (tenant_id, idempotency_key)
    WHERE tenant_id IS NOT NULL;

CREATE UNIQUE INDEX uq_idea_idempotency_record_system_key
    ON idea_idempotency_record (idempotency_key)
    WHERE tenant_id IS NULL;

CREATE INDEX idx_idea_idempotency_record_tenant_candidate
    ON idea_idempotency_record (tenant_id, candidate_id, operation_name);
