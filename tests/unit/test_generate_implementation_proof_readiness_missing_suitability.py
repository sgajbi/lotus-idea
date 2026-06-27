from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_implementation_proof_readiness as proof_report
from app.application.missing_suitability_live_proof import (
    build_missing_suitability_live_proof_payload,
)


def test_generate_implementation_proof_readiness_uses_explicit_missing_suitability_live_proof(
    tmp_path: Path,
) -> None:
    advise_proof = tmp_path / "missing-suitability-live-proof.json"
    advise_proof.write_text(
        json.dumps(
            build_missing_suitability_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_advise_source_attempted=True,
                evaluation_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-advise",
                    "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
                    "evaluationOutcome": "candidate_created",
                    "sourceEvidenceCurrent": True,
                    "clientReadyPublicationBlocked": True,
                    "advisePolicyWorkflowReady": True,
                    "sourceDiagnosticCodes": ["advise_policy_requirements_open"],
                    "reasonCodes": ["suitability_context_missing", "review_required"],
                    "unsupportedReasons": [],
                },
            )
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "proof" / "readiness.json"

    result = proof_report.main(
        [
            "--evaluated-at-utc",
            "2026-06-27T00:00:00Z",
            "--missing-suitability-live-proof",
            str(advise_proof),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    archetypes = next(
        capability
        for capability in payload["capabilities"]
        if capability["capabilityId"] == "opportunity-archetype-scenarios"
    )
    assert (
        "opportunity_archetype_advise_policy_live_source_proof_missing"
        not in (archetypes["blockers"])
    )
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes["blockers"]
    assert "opportunity_archetype_client_publication_not_ready" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "Missing suitability live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
