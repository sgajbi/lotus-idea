-- Restore the pre-identity schema only when no governed version event exists.
-- Re-adding the former event-type constraint fails closed before history is
-- dropped if the database contains evidence refresh, material-version, or
-- recurrent-condition events.

ALTER TABLE IF EXISTS idea_outbox_event
    DROP CONSTRAINT IF EXISTS ck_idea_outbox_event_event_type;
ALTER TABLE IF EXISTS idea_outbox_event
    ADD CONSTRAINT ck_idea_outbox_event_event_type CHECK (
        event_type IN (
            'idea.candidate.persisted.v1',
            'idea.lifecycle.transitioned.v1',
            'idea.review.decision_recorded.v1',
            'idea.feedback.recorded.v1',
            'idea.conversion.intent_requested.v1',
            'idea.conversion.outcome_recorded.v1',
            'idea.report_evidence_pack.requested.v1'
        )
    );

DROP TABLE IF EXISTS idea_candidate_version_history;
DROP INDEX IF EXISTS uq_idea_candidate_record_business_identity;

ALTER TABLE IF EXISTS idea_candidate_record
    DROP CONSTRAINT IF EXISTS ck_idea_candidate_record_identity_json,
    DROP CONSTRAINT IF EXISTS ck_idea_candidate_record_identity_versions;

ALTER TABLE IF EXISTS idea_candidate_record
    DROP COLUMN IF EXISTS supersedes_material_version,
    DROP COLUMN IF EXISTS change_reason,
    DROP COLUMN IF EXISTS evidence_version,
    DROP COLUMN IF EXISTS material_version,
    DROP COLUMN IF EXISTS material_fingerprint,
    DROP COLUMN IF EXISTS identity_policy_version,
    DROP COLUMN IF EXISTS business_identity_id;
