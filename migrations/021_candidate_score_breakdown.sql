-- Make persisted candidate scores self-explanatory and reconstructable.
-- Historical v1 policies stored a scalar without source-derived components. Preserve those
-- records explicitly as historical fixed-policy scores; all v2 writes already carry their
-- evidence-derived breakdown. Unknown or malformed score payloads fail constraint validation.

UPDATE idea_candidate_record
SET candidate_json = jsonb_set(
    jsonb_set(
        candidate_json,
        '{score,contributions}',
        jsonb_build_array(
            jsonb_build_object(
                'component', 'legacy_fixed_policy',
                'input_score', candidate_json->'score'->>'score',
                'weight', '1',
                'contribution', candidate_json->'score'->>'score'
            )
        ),
        true
    ),
    '{score,conflict_penalty_applied}',
    to_jsonb('0'::text),
    true
)
WHERE candidate_json->'score' IS NOT NULL
  AND candidate_json->'score' <> 'null'::jsonb
  AND jsonb_typeof(candidate_json->'score') = 'object'
  AND NOT (candidate_json->'score' ? 'contributions')
  AND candidate_json->'score'->>'policy_version' IN (
      'allocation-drift-mandate-review-v1',
      'bond-maturity-review-v1',
      'cashflow-liquidity-review-v1',
      'concentration-attention-v1',
      'drawdown-review-attention-v1',
      'high-volatility-attention-v1',
      'idle-liquidity-v1',
      'mandate-restriction-review-v1',
      'missing-benchmark-review-v1',
      'missing-risk-profile-review-v1',
      'missing-suitability-context-review-v1',
      'underperformance-review-v1'
  );

ALTER TABLE idea_candidate_record
    ADD CONSTRAINT ck_idea_candidate_record_score_breakdown CHECK (
        candidate_json->'score' IS NULL
        OR candidate_json->'score' = 'null'::jsonb
        OR (
            jsonb_typeof(candidate_json->'score') = 'object'
            AND jsonb_typeof(candidate_json->'score'->'contributions') = 'array'
            AND jsonb_array_length(candidate_json->'score'->'contributions') > 0
            AND candidate_json->'score' ? 'conflict_penalty_applied'
        )
    ) NOT VALID;

ALTER TABLE idea_candidate_record
    VALIDATE CONSTRAINT ck_idea_candidate_record_score_breakdown;
