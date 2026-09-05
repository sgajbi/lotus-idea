DROP VIEW IF EXISTS idea_review_authority_migration_audit;

DO $$
BEGIN
    IF to_regclass('public.idea_conversion_intent') IS NOT NULL THEN
        UPDATE idea_conversion_intent
        SET intent_json = intent_json - 'review_authority_grant'
        WHERE intent_json -> 'review_authority_grant' = 'null'::jsonb;
    END IF;
END
$$;

DO $$
BEGIN
    IF to_regclass('public.idea_review_decision') IS NOT NULL THEN
        UPDATE idea_review_decision
        SET decision_json = decision_json - 'review_channel' - 'review_policy_version'
            - 'review_authority_policy_version'
        WHERE decision_json ->> 'review_channel' = 'legacy_unverified'
          AND decision_json ->> 'review_policy_version' = 'legacy-unverified'
          AND decision_json ->> 'review_authority_policy_version' = 'legacy-unverified';
    END IF;
END
$$;
