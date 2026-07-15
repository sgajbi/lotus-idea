from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.low_income_cashflow_runtime_evidence import (
    valid_low_income_cashflow_runtime_evidence,
)
from tests.support.proof_provenance import bound_aggregate_proof

LOW_INCOME_PROOF_REF = "output/opportunity-archetypes/low-income-core-cashflow-live-proof.json"


def test_readiness_uses_low_income_cashflow_runtime_evidence_without_promotion() -> None:
    evaluated_at = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=evaluated_at,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        low_income_core_cashflow_live_proof=bound_aggregate_proof(
            valid_low_income_cashflow_runtime_evidence(evaluated_at_utc=evaluated_at),
            LOW_INCOME_PROOF_REF,
        ),
        low_income_core_cashflow_live_proof_ref=LOW_INCOME_PROOF_REF,
    )

    assert "opportunity_archetype_live_core_cashflow_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    for blocker in (
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
        "no_supported_features_promoted",
    ):
        assert blocker in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    archetypes = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "opportunity-archetype-scenarios"
    )
    assert "opportunity_archetype_live_core_cashflow_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes.blockers
    assert LOW_INCOME_PROOF_REF in archetypes.evidence_refs
