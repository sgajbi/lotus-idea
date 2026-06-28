from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_implementation_proof_readiness as proof_report
from app.application.core_portfolio_state_live_proof import (
    build_core_portfolio_state_live_proof_payload,
)


def test_generate_implementation_proof_readiness_uses_explicit_core_portfolio_state_live_proof(
    tmp_path: Path,
) -> None:
    core_proof = tmp_path / "core-portfolio-state-live-proof.json"
    core_proof.write_text(
        json.dumps(
            build_core_portfolio_state_live_proof_payload(
                generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
                live_core_source_attempted=True,
                evidence_summary={
                    "runStatus": "completed",
                    "sourceAuthority": "lotus-core",
                    "sourceProductId": "lotus-core:PortfolioStateSnapshot:v1",
                    "portfolioStateRefPresent": True,
                    "sourceEvidenceCurrent": True,
                    "sourceEvidenceAvailable": True,
                    "sourceDiagnosticCodes": ["core_portfolio_state_ready"],
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
            "--core-portfolio-state-live-proof",
            str(core_proof),
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
        "opportunity_archetype_core_portfolio_state_source_ref_missing"
        not in archetypes["blockers"]
    )
    assert (
        "opportunity_archetype_portfolio_scoped_manage_source_proof_missing"
        in archetypes["blockers"]
    )
    assert (
        "opportunity_archetype_mandate_performance_health_source_ref_missing"
        in archetypes["blockers"]
    )
    assert "opportunity_archetype_mandate_risk_health_source_ref_missing" in archetypes["blockers"]
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes["blockers"]
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes["blockers"])
    assert "Core portfolio-state live proof artifact" in archetypes["evidenceRefs"]
    assert payload["readinessStatus"] == "blocked"
    assert payload["supportedFeaturePromoted"] is False
