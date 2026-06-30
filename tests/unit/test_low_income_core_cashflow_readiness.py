from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.application.low_income_core_cashflow_live_proof import (
    build_low_income_core_cashflow_live_proof_payload,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof


LOW_INCOME_PROOF_REF = "output/opportunity-archetypes/low-income-core-cashflow-live-proof.json"


def test_readiness_uses_low_income_core_cashflow_proof_without_promotion() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        low_income_core_cashflow_live_proof=_valid_low_income_core_cashflow_live_proof(),
        low_income_core_cashflow_live_proof_ref=LOW_INCOME_PROOF_REF,
    )

    assert "opportunity_archetype_live_core_cashflow_source_proof_missing" not in (
        snapshot.overall_blockers
    )
    assert "opportunity_archetype_workbench_product_proof_missing" in snapshot.overall_blockers
    assert "opportunity_archetype_data_mesh_not_certified" in snapshot.overall_blockers
    assert "opportunity_archetype_client_publication_not_ready" in snapshot.overall_blockers
    assert "opportunity_archetype_supported_feature_promotion_missing" in (
        snapshot.overall_blockers
    )
    assert "no_supported_features_promoted" in snapshot.overall_blockers
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


def _valid_low_income_core_cashflow_live_proof() -> dict[str, object]:
    return bound_aggregate_proof(
        build_low_income_core_cashflow_live_proof_payload(
            generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
            live_core_source_attempted=True,
            evidence_summary={
                "runStatus": "completed",
                "sourceAuthority": "lotus-core",
                "cashMovementRefPresent": True,
                "cashflowProjectionRefPresent": True,
                "cashMovementCountPresent": True,
                "projectedCumulativeCashflowPresent": True,
                "sourceEvidenceCurrent": True,
                "cashflowDiagnostic": "core_cashflow_liquidity_evidence_ready",
                "sourceDiagnosticCodes": ["core_cashflow_liquidity_evidence_ready"],
            },
        ),
        LOW_INCOME_PROOF_REF,
    )
