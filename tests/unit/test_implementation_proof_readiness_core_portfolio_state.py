from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.core_portfolio_state_runtime_evidence import (
    valid_core_portfolio_state_runtime_evidence,
)
from tests.support.proof_provenance import bound_aggregate_proof

PROOF_REF = "output/opportunity/core-portfolio-state-runtime-execution.json"


def test_implementation_proof_readiness_uses_receipt_bound_core_portfolio_state_evidence() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        core_portfolio_state_live_proof=_valid_runtime_evidence(),
        core_portfolio_state_live_proof_ref=PROOF_REF,
    )

    assert "opportunity_archetype_core_portfolio_state_source_ref_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_portfolio_scoped_manage_source_proof_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_mandate_performance_health_source_ref_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_mandate_risk_health_source_ref_missing" in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    assert "workbench_panel_missing" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_core_portfolio_state_source_ref_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_portfolio_scoped_manage_source_proof_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_mandate_performance_health_source_ref_missing" in (
        archetypes.blockers
    )
    assert "opportunity_archetype_mandate_risk_health_source_ref_missing" in (archetypes.blockers)
    assert "opportunity_archetype_data_mesh_not_certified" in archetypes.blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (archetypes.blockers)
    assert PROOF_REF in archetypes.evidence_refs
    assert archetypes.supported_feature_promoted is False
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False


def test_implementation_proof_readiness_rejects_retired_summary_only_evidence() -> None:
    retired_summary = bound_aggregate_proof(
        {
            "schemaVersion": "lotus-idea.core-portfolio-state-live-proof.v1",
            "evidenceClass": "live_proof",
            "generatedAtUtc": "2026-06-27T00:00:00Z",
            "execution": {"status": "completed"},
            "evidenceSummary": {
                "sourceAuthority": "lotus-core",
                "portfolioStateRefPresent": True,
                "sourceEvidenceCurrent": True,
                "sourceEvidenceAvailable": True,
            },
        },
        PROOF_REF,
    )

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        core_portfolio_state_live_proof=retired_summary,
        core_portfolio_state_live_proof_ref=PROOF_REF,
    )

    assert "opportunity_archetype_core_portfolio_state_source_ref_missing" in (
        snapshot.overall_blockers
    )


def _valid_runtime_evidence() -> dict[str, object]:
    return bound_aggregate_proof(
        valid_core_portfolio_state_runtime_evidence(
            evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        ),
        PROOF_REF,
    )
