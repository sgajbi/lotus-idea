from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.bond_maturity_runtime_evidence import (
    valid_bond_maturity_runtime_evidence,
)
from tests.support.proof_provenance import bound_aggregate_proof

BOND_MATURITY_PROOF_REF = "output/opportunity-archetypes/bond-maturity-live-proof.json"
EVALUATED_AT = datetime(2026, 6, 27, 0, 0, tzinfo=UTC)


def test_readiness_uses_receipt_bound_runtime_evidence_without_promotion() -> None:
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        bond_maturity_live_proof=bound_aggregate_proof(
            valid_bond_maturity_runtime_evidence(evaluated_at_utc=EVALUATED_AT),
            BOND_MATURITY_PROOF_REF,
        ),
        bond_maturity_live_proof_ref=BOND_MATURITY_PROOF_REF,
    )

    assert "opportunity_archetype_maturity_live_core_source_proof_missing" not in (
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
    assert "opportunity_archetype_maturity_live_core_source_proof_missing" not in (
        archetypes.blockers
    )
    assert "opportunity_archetype_workbench_product_proof_missing" in archetypes.blockers
    assert BOND_MATURITY_PROOF_REF in archetypes.evidence_refs


def test_readiness_rejects_unknown_reconciliation_even_with_current_provenance() -> None:
    proof = valid_bond_maturity_runtime_evidence(evaluated_at_utc=EVALUATED_AT)
    proof["execution"]["sourceReceipt"]["reconciliationStatus"] = "UNKNOWN"

    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=EVALUATED_AT,
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        bond_maturity_live_proof=bound_aggregate_proof(proof, BOND_MATURITY_PROOF_REF),
        bond_maturity_live_proof_ref=BOND_MATURITY_PROOF_REF,
    )

    assert "opportunity_archetype_maturity_live_core_source_proof_missing" in (
        snapshot.overall_blockers
    )
