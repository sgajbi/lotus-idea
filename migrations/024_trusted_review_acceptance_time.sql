-- Preserve producer-observed action time while making Idea server admission time explicit.
-- Historical rows cannot prove a distinct server instant, so their posture is marked as assumed.

ALTER TABLE idea_review_decision
    ADD COLUMN accepted_at_utc TIMESTAMPTZ,
    ADD COLUMN acceptance_time_source TEXT;

UPDATE idea_review_decision
SET accepted_at_utc = decided_at_utc,
    acceptance_time_source = 'legacy_observed_time_assumed',
    decision_json = jsonb_set(
        jsonb_set(
            decision_json,
            '{accepted_at_utc}',
            to_jsonb(decided_at_utc)
        ),
        '{acceptance_time_source}',
        to_jsonb('legacy_observed_time_assumed'::text)
    );

ALTER TABLE idea_review_decision
    ALTER COLUMN accepted_at_utc SET NOT NULL,
    ALTER COLUMN acceptance_time_source SET NOT NULL,
    ADD CONSTRAINT ck_idea_review_decision_acceptance_time_source
        CHECK (acceptance_time_source IN ('server_accepted', 'legacy_observed_time_assumed'));

ALTER TABLE idea_feedback_event
    ADD COLUMN accepted_at_utc TIMESTAMPTZ,
    ADD COLUMN acceptance_time_source TEXT;

UPDATE idea_feedback_event
SET accepted_at_utc = recorded_at_utc,
    acceptance_time_source = 'legacy_observed_time_assumed',
    feedback_json = jsonb_set(
        jsonb_set(
            feedback_json,
            '{accepted_at_utc}',
            to_jsonb(recorded_at_utc)
        ),
        '{acceptance_time_source}',
        to_jsonb('legacy_observed_time_assumed'::text)
    );

ALTER TABLE idea_feedback_event
    ALTER COLUMN accepted_at_utc SET NOT NULL,
    ALTER COLUMN acceptance_time_source SET NOT NULL,
    ADD CONSTRAINT ck_idea_feedback_event_acceptance_time_source
        CHECK (acceptance_time_source IN ('server_accepted', 'legacy_observed_time_assumed'));

CREATE INDEX idx_idea_review_decision_candidate_accepted_time
    ON idea_review_decision (candidate_id, accepted_at_utc, review_decision_id);

CREATE INDEX idx_idea_feedback_event_candidate_accepted_time
    ON idea_feedback_event (candidate_id, accepted_at_utc, feedback_event_id);

ALTER TABLE idea_conversion_intent
    ADD COLUMN accepted_at_utc TIMESTAMPTZ,
    ADD COLUMN acceptance_time_source TEXT;

UPDATE idea_conversion_intent
SET accepted_at_utc = requested_at_utc,
    acceptance_time_source = 'legacy_observed_time_assumed',
    intent_json = jsonb_set(
        jsonb_set(
            intent_json,
            '{accepted_at_utc}',
            to_jsonb(requested_at_utc)
        ),
        '{acceptance_time_source}',
        to_jsonb('legacy_observed_time_assumed'::text)
    );

ALTER TABLE idea_conversion_intent
    ALTER COLUMN accepted_at_utc SET NOT NULL,
    ALTER COLUMN acceptance_time_source SET NOT NULL,
    ADD CONSTRAINT ck_idea_conversion_intent_acceptance_time_source
        CHECK (acceptance_time_source IN ('server_accepted', 'legacy_observed_time_assumed'));

ALTER TABLE idea_conversion_outcome
    ADD COLUMN accepted_at_utc TIMESTAMPTZ,
    ADD COLUMN acceptance_time_source TEXT;

UPDATE idea_conversion_outcome
SET accepted_at_utc = recorded_at_utc,
    acceptance_time_source = 'legacy_observed_time_assumed',
    outcome_json = jsonb_set(
        jsonb_set(
            outcome_json,
            '{accepted_at_utc}',
            to_jsonb(recorded_at_utc)
        ),
        '{acceptance_time_source}',
        to_jsonb('legacy_observed_time_assumed'::text)
    );

ALTER TABLE idea_conversion_outcome
    ALTER COLUMN accepted_at_utc SET NOT NULL,
    ALTER COLUMN acceptance_time_source SET NOT NULL,
    ADD CONSTRAINT ck_idea_conversion_outcome_acceptance_time_source
        CHECK (acceptance_time_source IN ('server_accepted', 'legacy_observed_time_assumed'));

CREATE INDEX idx_idea_conversion_intent_candidate_accepted_time
    ON idea_conversion_intent (candidate_id, accepted_at_utc, conversion_intent_id);

CREATE INDEX idx_idea_conversion_outcome_intent_accepted_time
    ON idea_conversion_outcome (conversion_intent_id, accepted_at_utc, conversion_outcome_id);

ALTER TABLE idea_candidate_presentation_receipt
    ADD COLUMN accepted_at_utc TIMESTAMPTZ,
    ADD COLUMN acceptance_time_source TEXT;

UPDATE idea_candidate_presentation_receipt
SET accepted_at_utc = recorded_at_utc,
    acceptance_time_source = 'legacy_observed_time_assumed';

ALTER TABLE idea_candidate_presentation_receipt
    ALTER COLUMN accepted_at_utc SET NOT NULL,
    ALTER COLUMN acceptance_time_source SET NOT NULL,
    ADD CONSTRAINT ck_idea_presentation_receipt_acceptance_time_source
        CHECK (acceptance_time_source IN ('server_accepted', 'legacy_observed_time_assumed'));

CREATE INDEX idx_idea_presentation_receipt_candidate_accepted_time
    ON idea_candidate_presentation_receipt (candidate_id, accepted_at_utc, receipt_id);
