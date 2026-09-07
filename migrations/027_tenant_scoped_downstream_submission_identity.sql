-- Scope outbound submission idempotency to its authoritative tenant.
-- Existing opaque support references remain stable and are explicitly classified as legacy.

ALTER TABLE idea_downstream_submission
    ADD COLUMN IF NOT EXISTS tenant_id TEXT,
    ADD COLUMN IF NOT EXISTS identity_version TEXT;

WITH authoritative_scope AS (
    SELECT
        'conversion_intent'::text AS resource_type,
        conversion.conversion_intent_id AS resource_id,
        lifecycle.tenant_id
    FROM idea_conversion_intent conversion
    JOIN idea_candidate_record candidate
      ON candidate.candidate_id = conversion.candidate_id
    JOIN idea_data_lifecycle_control lifecycle
      ON lifecycle.candidate_id = candidate.candidate_id
     AND lifecycle.tenant_id = candidate.candidate_json->'access_scope'->>'tenant_id'
    UNION ALL
    SELECT
        'report_evidence_pack'::text AS resource_type,
        report.report_evidence_pack_id AS resource_id,
        lifecycle.tenant_id
    FROM idea_report_evidence_pack_request report
    JOIN idea_candidate_record candidate
      ON candidate.candidate_id = report.candidate_id
    JOIN idea_data_lifecycle_control lifecycle
      ON lifecycle.candidate_id = candidate.candidate_id
     AND lifecycle.tenant_id = candidate.candidate_json->'access_scope'->>'tenant_id'
)
UPDATE idea_downstream_submission submission
SET tenant_id = scope.tenant_id,
    identity_version = 'legacy_unscoped_v1'
FROM authoritative_scope scope
WHERE submission.resource_type = scope.resource_type
  AND submission.resource_id = scope.resource_id
  AND submission.tenant_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM idea_downstream_submission
        WHERE tenant_id IS NULL OR btrim(tenant_id) = ''
    ) THEN
        RAISE EXCEPTION
            'cannot attribute every downstream submission to an authoritative candidate tenant';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM idea_downstream_submission
        WHERE identity_version IS DISTINCT FROM 'legacy_unscoped_v1'
    ) THEN
        RAISE EXCEPTION 'unexpected downstream submission identity version during migration';
    END IF;
END
$$;

ALTER TABLE idea_downstream_submission
    DROP CONSTRAINT idea_downstream_submission_pkey,
    ADD CONSTRAINT pk_idea_downstream_submission
        PRIMARY KEY (tenant_id, idempotency_key),
    ALTER COLUMN tenant_id SET NOT NULL,
    ALTER COLUMN identity_version SET NOT NULL,
    ADD CONSTRAINT ck_idea_downstream_submission_tenant
        CHECK (btrim(tenant_id) <> ''),
    ADD CONSTRAINT ck_idea_downstream_submission_identity_version
        CHECK (identity_version IN ('legacy_unscoped_v1', 'tenant_scoped_v2'));
