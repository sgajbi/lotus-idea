from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.risk_concentration_live_proof import (
    build_risk_concentration_live_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof

PROOF_REF = "output/opportunity/risk-concentration-live-proof.json"


def test_implementation_proof_readiness_uses_risk_concentration_live_proof_without_promotion() -> (
    None
):
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        risk_concentration_live_proof=_valid_risk_concentration_live_proof(),
        risk_concentration_live_proof_ref=PROOF_REF,
    )

    assert "opportunity_archetype_live_risk_source_proof_missing" not in (snapshot.overall_blockers)
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in snapshot.overall_blockers
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_live_risk_source_proof_missing" not in archetypes.blockers
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert "output/opportunity/risk-concentration-live-proof.json" in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_risk_concentration_live_proof() -> dict[str, object]:
    return bound_aggregate_proof(
        build_risk_concentration_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            live_risk_source_attempted=True,
            evaluation_summary={
                "runStatus": "completed",
                "sourceAuthority": "lotus-risk",
                "sourceProductId": "lotus-risk:ConcentrationRiskReport:v1",
                "evaluationOutcome": "candidate_created",
                "sourceEvidenceCurrent": True,
                "sourceDiagnosticCodes": ["risk_issuer_coverage_complete"],
                "reasonCodes": ["concentration_attention"],
                "unsupportedReasons": [],
            },
        ),
        PROOF_REF,
    )
