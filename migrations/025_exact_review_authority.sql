-- Classify pre-exact-authority history without fabricating presentation or evidence proof.
-- The application decoder grants no authority to legacy_unverified decisions or null grants.

UPDATE idea_review_decision
SET decision_json = (
    decision_json
    - 'presentation_receipt_id'
    - 'queue_snapshot_digest'
) || jsonb_build_object(
    'review_channel', 'legacy_unverified',
    'review_policy_version', 'legacy-unverified',
    'review_authority_policy_version', 'legacy-unverified'
)
WHERE NOT decision_json ?& ARRAY[
    'candidate_material_version',
    'candidate_evidence_version',
    'evidence_packet_id',
    'evidence_content_hash',
    'review_channel',
    'review_policy_version',
    'review_authority_policy_version'
];

UPDATE idea_conversion_intent
SET intent_json = jsonb_set(
    intent_json,
    '{review_authority_grant}',
    'null'::jsonb,
    true
)
WHERE NOT intent_json ? 'review_authority_grant'
   OR intent_json -> 'review_authority_grant' = 'null'::jsonb
   OR NOT (intent_json -> 'review_authority_grant' ? 'authority_policy_version');

CREATE VIEW idea_review_authority_migration_audit AS
SELECT
    review.candidate_id,
    'review_decision'::text AS resource_type,
    review.review_decision_id AS resource_id,
    'legacy_review_authority_unverified'::text AS finding
FROM idea_review_decision AS review
WHERE review.decision_json ->> 'review_channel' = 'legacy_unverified'
UNION ALL
SELECT
    intent.candidate_id,
    'conversion_intent'::text AS resource_type,
    intent.conversion_intent_id AS resource_id,
    'conversion_intent_without_exact_review_authority'::text AS finding
FROM idea_conversion_intent AS intent
WHERE intent.intent_json -> 'review_authority_grant' IS NULL
   OR intent.intent_json -> 'review_authority_grant' = 'null'::jsonb
UNION ALL
SELECT
    candidate.candidate_id,
    'candidate'::text AS resource_type,
    candidate.candidate_id AS resource_id,
    'approved_candidate_without_exact_review_authority'::text AS finding
FROM idea_candidate_record AS candidate
WHERE candidate.review_posture = 'approved_for_conversion'
  AND NOT EXISTS (
      SELECT 1
      FROM idea_review_decision AS review
      WHERE review.candidate_id = candidate.candidate_id
        AND review.action = 'approve_for_conversion'
        AND review.decision_json ->> 'review_channel' IN ('workbench', 'operator')
        AND review.decision_json ?& ARRAY[
            'candidate_material_version',
            'candidate_evidence_version',
            'evidence_packet_id',
            'evidence_content_hash',
            'review_policy_version',
            'review_authority_policy_version'
        ]
  );
