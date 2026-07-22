from __future__ import annotations

from datetime import UTC, datetime

from app.application.implementation_proof_readiness import (
    build_implementation_proof_readiness_snapshot,
)
from app.domain import InMemoryIdeaRepository
from tests.support.proof_provenance import bound_aggregate_proof as _bound_aggregate_proof
from tests.unit.downstream_realization.fixtures import valid_manage_intake_runtime_execution


def test_manage_intake_runtime_execution_clears_downstream_live_blocker_only() -> None:
    proof_ref = "output/downstream/manage-intake-runtime-execution-proof.json"
    snapshot = build_implementation_proof_readiness_snapshot(
        evaluated_at_utc=datetime(2026, 7, 22, 0, 0, tzinfo=UTC),
        repository=InMemoryIdeaRepository(),
        durable_storage_backed=False,
        manage_intake_runtime_execution_proof=_bound_aggregate_proof(
            valid_manage_intake_runtime_execution(),
            proof_ref,
        ),
        manage_intake_runtime_execution_proof_ref=proof_ref,
    )

    assert "manage_live_contract_proof_missing" not in snapshot.overall_blockers
    assert "rebalance_execution_authority_remains_lotus_manage" in snapshot.overall_blockers
    assert "advise_live_contract_proof_missing" in snapshot.overall_blockers
    assert "client_publication_authority_blocked" in snapshot.overall_blockers
    assert "no_supported_features_promoted" in snapshot.overall_blockers
    assert snapshot.readiness_status == "blocked"
    assert snapshot.supportability_status == "not_certified"
    assert snapshot.supported_features_promoted is False
    downstream = next(
        capability
        for capability in snapshot.capabilities
        if capability.capability_id == "downstream-realization"
    )
    assert "manage_live_contract_proof_missing" not in downstream.blockers
    assert "rebalance_execution_authority_remains_lotus_manage" in downstream.blockers
    assert proof_ref in downstream.evidence_refs
