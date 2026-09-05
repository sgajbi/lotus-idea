DROP VIEW IF EXISTS idea_review_authority_migration_audit;

UPDATE idea_conversion_intent
SET intent_json = intent_json - 'review_authority_grant'
WHERE intent_json -> 'review_authority_grant' = 'null'::jsonb;

UPDATE idea_review_decision
SET decision_json = decision_json - 'review_channel' - 'review_policy_version'
    - 'review_authority_policy_version'
WHERE decision_json ->> 'review_channel' = 'legacy_unverified'
  AND decision_json ->> 'review_policy_version' = 'legacy-unverified'
  AND decision_json ->> 'review_authority_policy_version' = 'legacy-unverified';
