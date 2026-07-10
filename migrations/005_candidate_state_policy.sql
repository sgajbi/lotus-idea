-- Quarantine legacy lifecycle/review-posture contradictions and prevent new ones.
-- Policy: idea-candidate-state-v1.

CREATE TABLE IF NOT EXISTS idea_candidate_state_quarantine (
    candidate_id TEXT PRIMARY KEY,
    lifecycle_status TEXT NOT NULL,
    review_posture TEXT NOT NULL,
    candidate_json JSONB NOT NULL,
    policy_version TEXT NOT NULL,
    diagnostic_code TEXT NOT NULL,
    quarantined_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO idea_candidate_state_quarantine (
    candidate_id,
    lifecycle_status,
    review_posture,
    candidate_json,
    policy_version,
    diagnostic_code,
    quarantined_at_utc
)
SELECT
    candidate_id,
    lifecycle_status,
    review_posture,
    candidate_json,
    'idea-candidate-state-v1',
    'candidate_state_conflict',
    CURRENT_TIMESTAMP
FROM idea_candidate_record
WHERE NOT (
    (candidate_json->>'lifecycle_status') = lifecycle_status
    AND (candidate_json->>'review_posture') = review_posture
    AND (
        (
            lifecycle_status IN (
                'detected', 'generated', 'enriched', 'scored', 'governance_checked'
            )
            AND review_posture IN (
                'not_reviewed', 'advisor_review_required', 'pm_review_required',
                'compliance_review_required', 'suppressed'
            )
        )
        OR (
            lifecycle_status = 'ready_for_review'
            AND review_posture IN (
                'advisor_review_required', 'pm_review_required',
                'compliance_review_required', 'suppressed'
            )
        )
        OR (
            lifecycle_status = 'reviewed_by_advisor'
            AND review_posture IN (
                'advisor_reviewed', 'pm_review_required',
                'compliance_review_required', 'suppressed'
            )
        )
        OR (
            lifecycle_status IN (
                'approved', 'converted_to_proposal', 'converted_to_manage_review',
                'converted_to_report', 'accepted', 'executed'
            )
            AND review_posture = 'approved_for_conversion'
        )
        OR (lifecycle_status = 'rejected' AND review_posture = 'rejected')
        OR (lifecycle_status IN ('expired', 'closed') AND review_posture = 'no_action')
    )
)
ON CONFLICT (candidate_id) DO NOTHING;

ALTER TABLE idea_candidate_record
    ADD CONSTRAINT ck_idea_candidate_record_state_policy_v1 CHECK (
        (candidate_json->>'lifecycle_status') = lifecycle_status
        AND (candidate_json->>'review_posture') = review_posture
        AND (
            (
                lifecycle_status IN (
                    'detected', 'generated', 'enriched', 'scored', 'governance_checked'
                )
                AND review_posture IN (
                    'not_reviewed', 'advisor_review_required', 'pm_review_required',
                    'compliance_review_required', 'suppressed'
                )
            )
            OR (
                lifecycle_status = 'ready_for_review'
                AND review_posture IN (
                    'advisor_review_required', 'pm_review_required',
                    'compliance_review_required', 'suppressed'
                )
            )
            OR (
                lifecycle_status = 'reviewed_by_advisor'
                AND review_posture IN (
                    'advisor_reviewed', 'pm_review_required',
                    'compliance_review_required', 'suppressed'
                )
            )
            OR (
                lifecycle_status IN (
                    'approved', 'converted_to_proposal', 'converted_to_manage_review',
                    'converted_to_report', 'accepted', 'executed'
                )
                AND review_posture = 'approved_for_conversion'
            )
            OR (lifecycle_status = 'rejected' AND review_posture = 'rejected')
            OR (lifecycle_status IN ('expired', 'closed') AND review_posture = 'no_action')
        )
    ) NOT VALID;
