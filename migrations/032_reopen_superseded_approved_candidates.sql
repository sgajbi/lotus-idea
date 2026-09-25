-- Reopen approved, not-yet-converted candidates when their durable evidence has
-- moved beyond the evidence authorized by every exact review decision.
--
-- The repair is deliberately narrow: historical converted/terminal states and
-- legacy-unverified approvals are not rewritten. Each repaired row receives a
-- durable audit event and lifecycle transition before its state is changed.

LOCK TABLE idea_candidate_record IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE idea_review_decision IN SHARE MODE;
LOCK TABLE idea_audit_event IN ROW EXCLUSIVE MODE;
LOCK TABLE idea_lifecycle_history IN ROW EXCLUSIVE MODE;

WITH stale_approved AS (
    SELECT candidate.*
    FROM idea_candidate_record AS candidate
    WHERE candidate.lifecycle_status = 'approved'
      AND candidate.review_posture = 'approved_for_conversion'
      AND EXISTS (
          SELECT 1
          FROM idea_review_decision AS review
          WHERE review.candidate_id = candidate.candidate_id
            AND review.action = 'approve_for_conversion'
            AND review.decision_json ->> 'review_channel' IN ('workbench', 'operator')
            AND review.decision_json ->> 'review_policy_version' = 'idea-human-review-v1'
            AND review.decision_json ->> 'review_authority_policy_version'
                = 'idea-review-authority-v1'
      )
      AND NOT EXISTS (
          SELECT 1
          FROM idea_review_decision AS review
          WHERE review.candidate_id = candidate.candidate_id
            AND review.action = 'approve_for_conversion'
            AND review.decision_json ->> 'review_channel' IN ('workbench', 'operator')
            AND review.decision_json ->> 'review_policy_version' = 'idea-human-review-v1'
            AND review.decision_json ->> 'review_authority_policy_version'
                = 'idea-review-authority-v1'
            AND review.decision_json ->> 'candidate_material_version'
                = candidate.material_version::TEXT
            AND review.decision_json ->> 'candidate_evidence_version'
                = candidate.evidence_version::TEXT
            AND review.decision_json ->> 'evidence_packet_id'
                = candidate.evidence_packet_id
            AND review.decision_json ->> 'evidence_content_hash'
                = candidate.candidate_json -> 'evidence_packet'
                    -> 'lineage_ref' ->> 'content_hash'
            AND review.decision_json ->> 'source_revision_vector_digest'
                = candidate.candidate_json -> 'evidence_packet'
                    ->> 'source_revision_vector_digest'
            AND review.decision_json ->> 'source_cut_posture'
                = candidate.candidate_json -> 'evidence_packet'
                    ->> 'source_cut_posture'
      )
)
INSERT INTO idea_audit_event (
    audit_event_id,
    candidate_id,
    event_type,
    actor_subject,
    outcome,
    attributes_json,
    occurred_at_utc
)
SELECT
    'migration:032:superseded-approval:' || candidate_id,
    candidate_id,
    'idea.migration.superseded_approval_reopened.v1',
    'lotus-idea-migration-032',
    'reopened_for_fresh_review',
    jsonb_build_object(
        'migration_version', '032',
        'previous_lifecycle_status', lifecycle_status,
        'previous_review_posture', review_posture,
        'material_version', material_version,
        'evidence_version', evidence_version,
        'evidence_packet_id', evidence_packet_id,
        'evidence_hash', evidence_hash,
        'evidence_content_hash', candidate_json -> 'evidence_packet'
            -> 'lineage_ref' ->> 'content_hash',
        'source_revision_vector_digest', candidate_json -> 'evidence_packet'
            ->> 'source_revision_vector_digest',
        'source_cut_posture', candidate_json -> 'evidence_packet'
            ->> 'source_cut_posture'
    ),
    CURRENT_TIMESTAMP
FROM stale_approved;

INSERT INTO idea_lifecycle_history (
    lifecycle_history_id,
    candidate_id,
    source_status,
    target_status,
    actor_subject,
    changed_at_utc
)
SELECT
    'migration:032:superseded-approval:' || audit.candidate_id,
    audit.candidate_id,
    'approved',
    'ready_for_review',
    'lotus-idea-migration-032',
    audit.occurred_at_utc
FROM idea_audit_event AS audit
JOIN idea_candidate_record AS candidate
  ON candidate.candidate_id = audit.candidate_id
WHERE audit.event_type = 'idea.migration.superseded_approval_reopened.v1'
  AND candidate.lifecycle_status = 'approved'
  AND candidate.review_posture = 'approved_for_conversion'
  AND audit.attributes_json ->> 'material_version' = candidate.material_version::TEXT
  AND audit.attributes_json ->> 'evidence_version' = candidate.evidence_version::TEXT
  AND audit.attributes_json ->> 'evidence_packet_id' = candidate.evidence_packet_id
  AND audit.attributes_json ->> 'evidence_hash' = candidate.evidence_hash;

UPDATE idea_candidate_record AS candidate
SET lifecycle_status = 'ready_for_review',
    review_posture = 'advisor_review_required',
    candidate_json = jsonb_set(
        jsonb_set(
            jsonb_set(
                candidate.candidate_json,
                '{lifecycle_status}',
                to_jsonb('ready_for_review'::TEXT)
            ),
            '{review_posture}',
            to_jsonb('advisor_review_required'::TEXT)
        ),
        '{suppression_reason}',
        'null'::JSONB
    )
FROM idea_audit_event AS audit
WHERE audit.candidate_id = candidate.candidate_id
  AND audit.event_type = 'idea.migration.superseded_approval_reopened.v1'
  AND candidate.lifecycle_status = 'approved'
  AND candidate.review_posture = 'approved_for_conversion'
  AND audit.attributes_json ->> 'material_version' = candidate.material_version::TEXT
  AND audit.attributes_json ->> 'evidence_version' = candidate.evidence_version::TEXT
  AND audit.attributes_json ->> 'evidence_packet_id' = candidate.evidence_packet_id
  AND audit.attributes_json ->> 'evidence_hash' = candidate.evidence_hash;
