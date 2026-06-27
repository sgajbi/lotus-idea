from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.manage_mandate_live_proof import build_manage_mandate_live_proof_payload
from app.domain import InMemoryIdeaRepository


def test_implementation_proof_readiness_retains_manage_mandate_blocker_without_proof() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
    )

    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_portfolio_scoped_manage_source_proof_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_portfolio_scoped_manage_source_proof_missing" in (
        snapshot.overall_blockers
    )


def test_implementation_proof_readiness_uses_manage_mandate_live_proof_without_promotion() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        manage_mandate_live_proof=_valid_manage_mandate_live_proof(),
        manage_mandate_live_proof_ref="output/opportunity/manage-mandate-live-proof.json",
    )

    assert "opportunity_archetype_portfolio_scoped_manage_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_mandate_performance_health_source_ref_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_mandate_risk_health_source_ref_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_core_portfolio_state_source_ref_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_workbench_product_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_client_publication_not_ready" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_portfolio_scoped_manage_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_mandate_performance_health_source_ref_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_mandate_risk_health_source_ref_missing" in archetypes.blockers
    assert "opportunity_archetype_core_portfolio_state_source_ref_missing" in archetypes.blockers
    assert "opportunity_archetype_client_publication_not_ready" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in archetypes.blockers
    assert "output/opportunity/manage-mandate-live-proof.json" in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def _valid_manage_mandate_live_proof() -> dict[str, object]:
    return build_manage_mandate_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        live_manage_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-manage",
            "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "portfolioScopeConfirmed": True,
            "manageActionRegisterReady": True,
            "workflowDecisionCount": 2,
            "lineageEdgeCount": 1,
            "sourceDiagnosticCodes": ["manage_action_register_ready_portfolio_scope"],
            "reasonCodes": ["review_required"],
            "unsupportedReasons": [],
        },
    )
