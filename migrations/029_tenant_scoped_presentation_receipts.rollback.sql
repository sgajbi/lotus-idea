-- Refuse a downgrade that would collapse independent tenant receipt identities.
DO $$
DECLARE
    duplicate_raw_keys BOOLEAN := FALSE;
BEGIN
    IF to_regclass('idea_candidate_presentation_receipt') IS NOT NULL THEN
        EXECUTE
            'SELECT EXISTS (
                SELECT receipt_id
                FROM idea_candidate_presentation_receipt
                GROUP BY receipt_id
                HAVING COUNT(*) > 1
            )'
        INTO duplicate_raw_keys;
    END IF;
    IF duplicate_raw_keys THEN
        RAISE EXCEPTION
            'cannot roll back tenant-scoped presentation receipts while duplicate raw keys exist';
    END IF;
END
$$;

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    DROP CONSTRAINT IF EXISTS idea_candidate_presentation_receipt_pkey;

ALTER TABLE IF EXISTS idea_candidate_presentation_receipt
    ADD CONSTRAINT idea_candidate_presentation_receipt_pkey
    PRIMARY KEY (receipt_id);
