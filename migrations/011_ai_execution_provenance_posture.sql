-- Preserve honest execution-provenance posture for AI explanation lineage.

ALTER TABLE idea_ai_explanation_lineage
    ADD COLUMN execution_provenance_posture TEXT;

UPDATE idea_ai_explanation_lineage
SET execution_provenance_posture = 'pre_attestation_unverifiable',
    lineage_json = lineage_json || jsonb_build_object(
        'execution_provenance_posture',
        'pre_attestation_unverifiable'
    );

ALTER TABLE idea_ai_explanation_lineage
    ALTER COLUMN execution_provenance_posture SET NOT NULL;
