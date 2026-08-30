-- Govern stable economic candidate identity and independently version material state and evidence.

ALTER TABLE idea_candidate_record
    ADD COLUMN business_identity_id TEXT,
    ADD COLUMN identity_policy_version TEXT,
    ADD COLUMN material_fingerprint TEXT,
    ADD COLUMN material_version INTEGER,
    ADD COLUMN evidence_version INTEGER,
    ADD COLUMN change_reason TEXT,
    ADD COLUMN supersedes_material_version INTEGER;

UPDATE idea_candidate_record
SET business_identity_id = 'opportunity_migrated_' || candidate_id,
    identity_policy_version = 'idea-opportunity-identity-migration-v1',
    material_fingerprint = evidence_hash,
    material_version = 1,
    evidence_version = 1,
    change_reason = 'migration_backfill',
    supersedes_material_version = NULL,
    candidate_json = jsonb_set(
        candidate_json,
        '{identity}',
        jsonb_build_object(
            'business_identity_id', 'opportunity_migrated_' || candidate_id,
            'policy_version', 'idea-opportunity-identity-migration-v1',
            'material_fingerprint', evidence_hash,
            'material_version', 1,
            'evidence_version', 1,
            'change_reason', 'migration_backfill',
            'supersedes_material_version', NULL
        ),
        TRUE
    );

ALTER TABLE idea_candidate_record
    ALTER COLUMN business_identity_id SET NOT NULL,
    ALTER COLUMN identity_policy_version SET NOT NULL,
    ALTER COLUMN material_fingerprint SET NOT NULL,
    ALTER COLUMN material_version SET NOT NULL,
    ALTER COLUMN evidence_version SET NOT NULL,
    ALTER COLUMN change_reason SET NOT NULL;

ALTER TABLE idea_candidate_record
    ADD CONSTRAINT ck_idea_candidate_record_identity_versions
    CHECK (
        material_fingerprint ~ '^sha256:[0-9a-f]{64}$'
        AND material_version > 0
        AND evidence_version > 0
        AND change_reason IN (
            'initial_detection',
            'evidence_correction',
            'material_change',
            'recurrent_condition',
            'migration_backfill'
        )
        AND (
            supersedes_material_version IS NULL
            OR (
                supersedes_material_version > 0
                AND supersedes_material_version < material_version
            )
        )
    ),
    ADD CONSTRAINT ck_idea_candidate_record_identity_json
    CHECK (
        candidate_json->'identity'->>'business_identity_id' = business_identity_id
        AND candidate_json->'identity'->>'policy_version' = identity_policy_version
        AND candidate_json->'identity'->>'material_fingerprint' = material_fingerprint
        AND (candidate_json->'identity'->>'material_version')::INTEGER = material_version
        AND (candidate_json->'identity'->>'evidence_version')::INTEGER = evidence_version
        AND candidate_json->'identity'->>'change_reason' = change_reason
        AND (
            (supersedes_material_version IS NULL
             AND candidate_json->'identity'->>'supersedes_material_version' IS NULL)
            OR
            (candidate_json->'identity'->>'supersedes_material_version')::INTEGER
                = supersedes_material_version
        )
    );

CREATE UNIQUE INDEX uq_idea_candidate_record_business_identity
    ON idea_candidate_record (business_identity_id);

CREATE TABLE idea_candidate_version_history (
    candidate_version_history_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idea_candidate_record(candidate_id),
    business_identity_id TEXT NOT NULL,
    material_fingerprint TEXT NOT NULL,
    material_version INTEGER NOT NULL,
    evidence_version INTEGER NOT NULL,
    change_reason TEXT NOT NULL,
    source_lifecycle_status TEXT,
    resulting_lifecycle_status TEXT NOT NULL,
    supersedes_material_version INTEGER,
    evidence_hash TEXT NOT NULL,
    recorded_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_idea_candidate_version_history_version
        UNIQUE (candidate_id, material_version, evidence_version),
    CONSTRAINT ck_idea_candidate_version_history_values
        CHECK (
            material_fingerprint ~ '^sha256:[0-9a-f]{64}$'
            AND evidence_hash ~ '^sha256:[0-9a-f]{64}$'
            AND material_version > 0
            AND evidence_version > 0
            AND change_reason IN (
                'initial_detection',
                'evidence_correction',
                'material_change',
                'recurrent_condition',
                'migration_backfill'
            )
            AND (
                supersedes_material_version IS NULL
                OR (
                    supersedes_material_version > 0
                    AND supersedes_material_version < material_version
                )
            )
        )
);

INSERT INTO idea_candidate_version_history (
    candidate_version_history_id,
    candidate_id,
    business_identity_id,
    material_fingerprint,
    material_version,
    evidence_version,
    change_reason,
    source_lifecycle_status,
    resulting_lifecycle_status,
    supersedes_material_version,
    evidence_hash,
    recorded_at_utc
)
SELECT candidate_id || ':version:1:1',
       candidate_id,
       business_identity_id,
       material_fingerprint,
       1,
       1,
       'migration_backfill',
       NULL,
       lifecycle_status,
       NULL,
       evidence_hash,
       persisted_at_utc
FROM idea_candidate_record;

ALTER TABLE idea_outbox_event DROP CONSTRAINT ck_idea_outbox_event_event_type;
ALTER TABLE idea_outbox_event
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
