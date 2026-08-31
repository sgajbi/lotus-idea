-- Restore the pre-021 persistence shape only for rows explicitly marked as historical fixed
-- scores. Evidence-derived v2 breakdowns are retained because discarding them would lose truth.

ALTER TABLE IF EXISTS idea_candidate_record
    DROP CONSTRAINT IF EXISTS ck_idea_candidate_record_score_breakdown;

DO $$
BEGIN
    IF to_regclass('public.idea_candidate_record') IS NOT NULL THEN
        UPDATE idea_candidate_record
        SET candidate_json = (candidate_json #- '{score,contributions}')
            #- '{score,conflict_penalty_applied}'
        WHERE jsonb_array_length(candidate_json->'score'->'contributions') = 1
          AND candidate_json->'score'->'contributions'->0->>'component' =
              'legacy_fixed_policy';
    END IF;
END
$$;
