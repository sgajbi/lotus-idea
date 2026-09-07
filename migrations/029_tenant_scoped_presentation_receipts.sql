-- Bind the client-generated presentation receipt key to the trusted candidate tenant.
-- Old writers must be drained because they target the former raw-key primary key.

ALTER TABLE idea_candidate_presentation_receipt
    DROP CONSTRAINT idea_candidate_presentation_receipt_pkey;

ALTER TABLE idea_candidate_presentation_receipt
    ADD CONSTRAINT idea_candidate_presentation_receipt_pkey
    PRIMARY KEY (tenant_id, receipt_id);
